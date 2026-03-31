from __future__ import annotations

from dataclasses import dataclass

from .preprocessing import expand_phrase_variants, lemmatize_text, normalize_text
from .schemas import AdInput, ClauseContext, EnrichedMicroCategory, Evidence


@dataclass(frozen=True)
class _PhraseEntry:
    mc_id: int
    mc_title: str
    phrase: str
    normalized_phrase: str
    lemma_phrase: str


class CategoryExtractor:
    def __init__(self, catalog: list[EnrichedMicroCategory]) -> None:
        self._catalog = {entry.mcId: entry for entry in catalog}
        self._phrase_entries = self._build_phrase_entries(catalog)

    @staticmethod
    def _build_phrase_entries(catalog: list[EnrichedMicroCategory]) -> list[_PhraseEntry]:
        entries: list[_PhraseEntry] = []
        seen_keys: set[tuple[int, str]] = set()

        for category in catalog:
            phrase_pool = [*category.keyPhrases, *category.matchPhrases]
            for phrase in phrase_pool:
                for variant in expand_phrase_variants(phrase):
                    normalized_phrase = normalize_text(variant)
                    key = (category.mcId, normalized_phrase)
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    entries.append(
                        _PhraseEntry(
                            mc_id=category.mcId,
                            mc_title=category.mcTitle,
                            phrase=phrase.strip(),
                            normalized_phrase=normalized_phrase,
                            lemma_phrase=lemmatize_text(variant),
                        )
                    )

        return sorted(entries, key=lambda entry: len(entry.normalized_phrase), reverse=True)

    def extract(self, item: AdInput, clause_contexts: list[ClauseContext]) -> list[Evidence]:
        evidences: list[Evidence] = []

        for context in clause_contexts:
            best_by_category: dict[int, Evidence] = {}

            for phrase_entry in self._phrase_entries:
                if phrase_entry.mc_id == item.mcId:
                    continue

                normalized_pos = context.clauseTextNormalized.find(phrase_entry.normalized_phrase)
                lemma_pos = context.clauseTextLemmatized.find(phrase_entry.lemma_phrase)
                if normalized_pos == -1 and lemma_pos == -1:
                    continue

                local_pos = normalized_pos if normalized_pos != -1 else max(lemma_pos, 0)
                candidate = Evidence(
                    mcId=phrase_entry.mc_id,
                    mcTitle=phrase_entry.mc_title,
                    matchedPhrase=phrase_entry.phrase,
                    sentenceIndex=context.sentenceIndex,
                    clauseIndex=context.clauseIndex,
                    clauseText=context.clauseText,
                    clauseTextNormalized=context.clauseTextNormalized,
                    clauseTextLemmatized=context.clauseTextLemmatized,
                    firstCharIndex=context.startCharIndex + local_pos,
                )

                previous = best_by_category.get(candidate.mcId)
                if previous is None or candidate.firstCharIndex < previous.firstCharIndex:
                    best_by_category[candidate.mcId] = candidate

            evidences.extend(best_by_category.values())

        return sorted(
            evidences,
            key=lambda evidence: (evidence.firstCharIndex, evidence.sentenceIndex, evidence.clauseIndex, evidence.mcId),
        )
