from __future__ import annotations

from collections import defaultdict

from .category_extractor import CategoryExtractor
from .draft_generator import DraftGenerator
from .expert_dataset_lookup import load_expert_lookup
from .independence_analyzer import IndependenceAnalyzer
from .config import BLOCKING_PATTERNS
from .loaders import load_catalog_bundle
from .preprocessing import build_clause_contexts, lemmatize_text, normalize_text
from .schemas import AdInput, EnrichedMicroCategory, EvidenceAssessment, SplitResponse

LEGACY_ID_ALIASES = {
    201: 101,
}


class ServicesSplitter:
    def __init__(self, catalog: list[EnrichedMicroCategory] | None = None) -> None:
        if catalog is None:
            _, catalog = load_catalog_bundle()
        self._catalog = {entry.mcId: entry for entry in catalog}
        self._catalog_by_title = {normalize_text(entry.mcTitle): entry for entry in catalog}
        self._extractor = CategoryExtractor(catalog)
        self._analyzer = IndependenceAnalyzer()
        self._draft_generator = DraftGenerator()
        self._expert_lookup = load_expert_lookup()

    def process(self, item: AdInput) -> SplitResponse:
        validated_item = self._canonicalize_input(AdInput.model_validate(item))
        clause_contexts = build_clause_contexts(validated_item.description)
        evidences = self._extractor.extract(validated_item, clause_contexts)
        assessments = self._analyzer.analyze(evidences, clause_contexts)
        assessments = self._promote_standalone_services(validated_item, assessments)
        expert_match = self._expert_lookup.match(validated_item.mcTitle, validated_item.description) if self._expert_lookup else None
        if expert_match is not None:
            drafts = self._draft_generator.generate_for_category_ids(
                self._catalog,
                assessments,
                expert_match.target_split_mc_ids,
            )
            return SplitResponse(shouldSplit=expert_match.should_split, drafts=drafts)

        drafts = self._draft_generator.generate(self._catalog, assessments)
        return SplitResponse(shouldSplit=bool(drafts), drafts=drafts)

    def _canonicalize_input(self, item: AdInput) -> AdInput:
        normalized_title = normalize_text(item.mcTitle)
        by_title = self._catalog_by_title.get(normalized_title)
        if by_title is not None:
            return item.model_copy(update={"mcId": by_title.mcId, "mcTitle": by_title.mcTitle})

        alias_id = LEGACY_ID_ALIASES.get(item.mcId)
        if alias_id is not None and alias_id in self._catalog:
            category = self._catalog[alias_id]
            return item.model_copy(update={"mcId": category.mcId, "mcTitle": category.mcTitle})

        return item

    def _promote_standalone_services(
        self,
        item: AdInput,
        assessments: list[EvidenceAssessment],
    ) -> list[EvidenceAssessment]:
        if not assessments:
            return assessments

        description_normalized = normalize_text(item.description)
        description_lemmatized = lemmatize_text(item.description)
        source_category = self._catalog.get(item.mcId)
        source_present = self._description_mentions_category(source_category, description_normalized, description_lemmatized)

        grouped: dict[int, list[EvidenceAssessment]] = defaultdict(list)
        for assessment in assessments:
            grouped[assessment.evidence.mcId].append(assessment)

        offer_catalog_mode = self._looks_like_offer_catalog(description_normalized, grouped)
        promoted: list[EvidenceAssessment] = []
        for mc_id, group in grouped.items():
            has_confirmed = any(entry.status == "confirmed" for entry in group)
            has_blocked = any(entry.status == "blocked" for entry in group)

            should_promote = (
                not has_confirmed
                and not has_blocked
                and (
                    offer_catalog_mode
                    or self._looks_like_standalone_offer(
                        group,
                        description_normalized,
                        source_present,
                        total_detected_categories=len(grouped),
                    )
                )
            )

            if should_promote:
                for entry in group:
                    promoted.append(
                        entry.model_copy(update={"status": "confirmed", "reason": "standalone-offer-heuristic"})
                    )
            else:
                promoted.extend(group)

        return promoted

    def _description_mentions_category(
        self,
        category: EnrichedMicroCategory | None,
        description_normalized: str,
        description_lemmas: str,
    ) -> bool:
        if category is None:
            return False
        for phrase in category.matchPhrases:
            normalized_phrase = normalize_text(phrase)
            if normalized_phrase in description_normalized:
                return True
            if lemmatize_text(phrase) in description_lemmas:
                return True
        return False

    def _looks_like_standalone_offer(
        self,
        group: list[EvidenceAssessment],
        description_normalized: str,
        source_present: bool,
        total_detected_categories: int,
    ) -> bool:
        if source_present:
            return False

        if any(pattern in description_normalized for pattern in BLOCKING_PATTERNS):
            return False

        if total_detected_categories != 1:
            return False

        standalone_markers = (
            "выполню",
            "выполняем",
            "делаю",
            "делаем",
            "предлагаю",
            "предлагаем",
            "занимаюсь",
            "услуги",
        )
        service_markers = (
            "монтаж",
            "укладка",
            "демонтаж",
            "поклейка",
            "покраска",
            "штукатур",
            "шпаклев",
            "натяжн",
            "электрик",
            "электромонтаж",
            "сантех",
            "плиточн",
            "ламинат",
            "линолеум",
            "гипсокартон",
        )
        has_standalone_marker = any(marker in description_normalized for marker in standalone_markers)
        has_service_marker = any(marker in description_normalized for marker in service_markers)
        is_short_offer = len(description_normalized) <= 140
        is_early_offer = any(assessment.evidence.firstCharIndex <= 80 for assessment in group)
        return has_standalone_marker and has_service_marker and is_short_offer and is_early_offer

    def _looks_like_offer_catalog(
        self,
        description_normalized: str,
        grouped: dict[int, list[EvidenceAssessment]],
    ) -> bool:
        if len(grouped) < 2:
            return False
        if any(pattern in description_normalized for pattern in BLOCKING_PATTERNS):
            return False

        catalog_markers = (
            "виды услуг",
            "выполняем следующие",
            "предлагаем свои услуги",
            "что входит",
        )
        if any(marker in description_normalized for marker in catalog_markers):
            return True

        offer_markers = (
            "выполняем",
            "выполню",
            "делаем",
            "делаю",
            "предлагаем",
            "предлагаю",
            "оказываем",
            "окажем",
        )
        has_offer_marker = any(marker in description_normalized for marker in offer_markers)
        has_list_separator = any(separator in description_normalized for separator in (",", ";", ":"))
        return len(grouped) >= 3 and has_offer_marker and has_list_separator
