from __future__ import annotations

from collections import defaultdict

from .config import MAX_DRAFT_LENGTH, MAX_EVIDENCE_SENTENCES
from .schemas import Draft, EnrichedMicroCategory, EvidenceAssessment


class DraftGenerator:
    def generate(
        self,
        catalog: dict[int, EnrichedMicroCategory],
        assessments: list[EvidenceAssessment],
    ) -> list[Draft]:
        confirmed_by_category: dict[int, list[EvidenceAssessment]] = defaultdict(list)
        confirmed_by_clause: dict[tuple[int, int], set[int]] = defaultdict(set)
        for assessment in assessments:
            if assessment.status == "confirmed":
                confirmed_by_category[assessment.evidence.mcId].append(assessment)
                confirmed_by_clause[
                    (assessment.evidence.sentenceIndex, assessment.evidence.clauseIndex)
                ].add(assessment.evidence.mcId)

        ordered_categories = sorted(
            confirmed_by_category.items(),
            key=lambda item: min(assessment.evidence.firstCharIndex for assessment in item[1]),
        )

        drafts: list[Draft] = []
        for mc_id, confirmed_assessments in ordered_categories:
            category = catalog[mc_id]
            text = self._build_text(category, confirmed_assessments, confirmed_by_clause)
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
            if len(snippet) < 24 or normalized_key in seen:
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
