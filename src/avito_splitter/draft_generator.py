from __future__ import annotations

from collections import defaultdict
import re

from .config import MAX_DRAFT_LENGTH, MAX_EVIDENCE_SENTENCES
from .preprocessing import lemmatize_text
from .schemas import Draft, EnrichedMicroCategory, EvidenceAssessment

_TOKEN_RE = re.compile(r"[0-9a-zа-я]+", re.IGNORECASE)
_GENERIC_SNIPPET_TOKENS = {
    "а",
    "и",
    "или",
    "также",
    "отдельно",
    "выполнять",
    "делать",
    "можно",
    "заказать",
    "как",
    "отдельный",
    "услуга",
    "работа",
}


class DraftGenerator:
    def generate(
        self,
        catalog: dict[int, EnrichedMicroCategory],
        assessments: list[EvidenceAssessment],
    ) -> list[Draft]:
        ordered_ids: list[int] = []
        seen_ids: set[int] = set()
        for assessment in sorted(assessments, key=lambda item: item.evidence.firstCharIndex):
            if assessment.status != "confirmed" or assessment.evidence.mcId in seen_ids:
                continue
            seen_ids.add(assessment.evidence.mcId)
            ordered_ids.append(assessment.evidence.mcId)

        return self.generate_for_category_ids(catalog, assessments, ordered_ids)

    def generate_for_category_ids(
        self,
        catalog: dict[int, EnrichedMicroCategory],
        assessments: list[EvidenceAssessment],
        category_ids: list[int],
    ) -> list[Draft]:
        confirmed_by_category: dict[int, list[EvidenceAssessment]] = defaultdict(list)
        confirmed_by_clause: dict[tuple[int, int], set[int]] = defaultdict(set)
        for assessment in assessments:
            if assessment.status == "confirmed":
                confirmed_by_category[assessment.evidence.mcId].append(assessment)
                confirmed_by_clause[
                    (assessment.evidence.sentenceIndex, assessment.evidence.clauseIndex)
                ].add(assessment.evidence.mcId)

        drafts: list[Draft] = []
        seen_ids: set[int] = set()
        for mc_id in category_ids:
            if mc_id in seen_ids:
                continue
            seen_ids.add(mc_id)
            category = catalog[mc_id]
            confirmed_assessments = confirmed_by_category.get(mc_id, [])
            if confirmed_assessments:
                text = self._build_text(category, confirmed_assessments, confirmed_by_clause)
            else:
                text = self._build_fallback_text(category)
            drafts.append(Draft(mcId=category.mcId, mcTitle=category.mcTitle, text=text))

        return drafts

    def _build_text(
        self,
        category: EnrichedMicroCategory,
        confirmed_assessments: list[EvidenceAssessment],
        confirmed_by_clause: dict[tuple[int, int], set[int]],
    ) -> str:
        snippets = self._collect_context_snippets(confirmed_assessments, confirmed_by_clause)
        if snippets:
            text = f"{self._ensure_period(category.draftLead)} {' '.join(snippets)}"
        else:
            text = self._build_fallback_text(category)

        if len(text) > MAX_DRAFT_LENGTH:
            text = text[: MAX_DRAFT_LENGTH - 1].rstrip(" ,;:.") + "."
        return text

    @staticmethod
    def _ensure_period(text: str) -> str:
        return text.rstrip(" .!?") + "."

    def _collect_context_snippets(
        self,
        assessments: list[EvidenceAssessment],
        confirmed_by_clause: dict[tuple[int, int], set[int]],
    ) -> list[str]:
        snippets: list[str] = []
        seen: set[str] = set()

        for assessment in sorted(assessments, key=lambda item: item.evidence.firstCharIndex):
            clause_key = (assessment.evidence.sentenceIndex, assessment.evidence.clauseIndex)
            if len(confirmed_by_clause[clause_key]) > 1:
                continue
            snippet = assessment.evidence.clauseText.strip(" ,;:.")
            normalized_key = snippet.lower()
            if len(snippet) < 24 or normalized_key in seen or self._is_low_signal_snippet(assessment):
                continue
            seen.add(normalized_key)
            snippets.append(self._ensure_period(snippet[:1].upper() + snippet[1:]))
            if len(snippets) >= MAX_EVIDENCE_SENTENCES:
                break

        return snippets

    def _build_fallback_text(self, category: EnrichedMicroCategory) -> str:
        phrases = ", ".join(category.keyPhrases[:2])
        if phrases:
            return f"{self._ensure_period(category.draftLead)} Основные работы: {phrases}."
        return self._ensure_period(category.draftLead)

    def _is_low_signal_snippet(self, assessment: EvidenceAssessment) -> bool:
        snippet_tokens = self._content_tokens(assessment.evidence.clauseText)
        if not snippet_tokens:
            return True

        matched_phrase_tokens = self._content_tokens(assessment.evidence.matchedPhrase)
        if matched_phrase_tokens and snippet_tokens.issubset(matched_phrase_tokens):
            return True

        return False

    def _content_tokens(self, text: str) -> set[str]:
        lemma_tokens = _TOKEN_RE.findall(lemmatize_text(text))
        return {token for token in lemma_tokens if token not in _GENERIC_SNIPPET_TOKENS}
