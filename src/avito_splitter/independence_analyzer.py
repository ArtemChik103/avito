from __future__ import annotations

from collections import defaultdict

from .config import BLOCKING_PATTERNS, CONFIRMING_PATTERNS, ENUMERATION_CONFIRMING_HINTS, LIST_SEPARATORS
from .schemas import ClauseContext, Evidence, EvidenceAssessment


class IndependenceAnalyzer:
    def analyze(
        self,
        evidences: list[Evidence],
        clause_contexts: list[ClauseContext],
    ) -> list[EvidenceAssessment]:
        clause_map = {(context.sentenceIndex, context.clauseIndex): context for context in clause_contexts}
        evidences_by_sentence: dict[int, list[Evidence]] = defaultdict(list)
        for evidence in evidences:
            evidences_by_sentence[evidence.sentenceIndex].append(evidence)

        assessments: list[EvidenceAssessment] = []
        for evidence in evidences:
            clause = clause_map[(evidence.sentenceIndex, evidence.clauseIndex)]
            same_sentence_clauses = [
                context for context in clause_contexts if context.sentenceIndex == evidence.sentenceIndex
            ]

            has_blocking = self._contains_any(clause.clauseTextNormalized, BLOCKING_PATTERNS)
            has_confirming = any(
                self._contains_any(context.clauseTextNormalized, CONFIRMING_PATTERNS)
                for context in same_sentence_clauses
                if abs(context.clauseIndex - evidence.clauseIndex) <= 1
            )
            has_enumeration_confirmation = self._is_confirming_enumeration(
                clause.sentenceText,
                evidences_by_sentence[evidence.sentenceIndex],
            )

            if has_confirming or has_enumeration_confirmation:
                status = "confirmed"
                reason = "confirming-pattern" if has_confirming else "enumeration-heuristic"
            elif has_blocking:
                status = "blocked"
                reason = "blocking-pattern"
            else:
                status = "neutral"
                reason = "mention-without-independence-marker"

            assessments.append(EvidenceAssessment(evidence=evidence, status=status, reason=reason))

        return assessments

    @staticmethod
    def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
        return any(pattern in text for pattern in patterns)

    def _is_confirming_enumeration(self, sentence_text: str, sentence_evidences: list[Evidence]) -> bool:
        distinct_categories = {evidence.mcId for evidence in sentence_evidences}
        if len(distinct_categories) < 2:
            return False
        if self._contains_any(sentence_text, BLOCKING_PATTERNS):
            return False
        has_separator = any(separator in sentence_text for separator in LIST_SEPARATORS)
        has_service_hint = self._contains_any(sentence_text, ENUMERATION_CONFIRMING_HINTS)
        return has_separator and has_service_hint
