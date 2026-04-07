from __future__ import annotations

import re
from functools import lru_cache

from pymorphy3 import MorphAnalyzer

from .config import CLAUSE_SPLIT_PATTERN, SENTENCE_SPLIT_PATTERN
from .schemas import ClauseContext

_MORPH = MorphAnalyzer()
_WHITESPACE_RE = re.compile(r"\s+")
_TOKEN_RE = re.compile(r"[0-9a-zа-я]+", re.IGNORECASE)
_PUNCT_SPACING_RE = re.compile(r"\s*([,;:.!?])\s*")
_DASH_RE = re.compile(r"\s*[–—−]+\s*")
_SENTENCE_SPLIT_RE = re.compile(SENTENCE_SPLIT_PATTERN)
_CLAUSE_SPLIT_RE = re.compile(CLAUSE_SPLIT_PATTERN)
_LATIN_TO_CYRILLIC = str.maketrans(
    {
        "a": "а",
        "b": "в",
        "c": "с",
        "e": "е",
        "h": "н",
        "k": "к",
        "m": "м",
        "o": "о",
        "p": "р",
        "t": "т",
        "x": "х",
        "y": "у",
    }
)


@lru_cache(maxsize=8192)
def _lemmatize_token(token: str) -> str:
    if token.isdigit():
        return token
    return _MORPH.parse(token)[0].normal_form


@lru_cache(maxsize=2048)
def expand_phrase_variants(text: str) -> tuple[str, ...]:
    normalized = normalize_text(text)
    tokens = _TOKEN_RE.findall(normalized)
    if len(tokens) != 1:
        return (normalized,)

    token = tokens[0]
    variants = {normalized}
    for parse in _MORPH.parse(token)[:2]:
        variants.update(normalize_text(form.word) for form in parse.lexeme)
    return tuple(sorted(variants))


def normalize_text(text: str) -> str:
    normalized = text.lower().replace("ё", "е")
    normalized = normalized.translate(_LATIN_TO_CYRILLIC)
    normalized = _DASH_RE.sub(" — ", normalized)
    normalized = normalized.replace("\r", " ").replace("\n", " ")
    normalized = _PUNCT_SPACING_RE.sub(r"\1 ", normalized)
    normalized = _WHITESPACE_RE.sub(" ", normalized)
    return normalized.strip()


def split_sentences(text: str) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []
    sentences = [sentence.strip() for sentence in _SENTENCE_SPLIT_RE.split(normalized) if sentence.strip()]
    return sentences or [normalized]


def split_clauses(sentence: str) -> list[str]:
    normalized = normalize_text(sentence)
    if not normalized:
        return []
    clauses = [clause.strip(" ,;:—-") for clause in _CLAUSE_SPLIT_RE.split(normalized) if clause.strip(" ,;:—-")]
    return clauses or [normalized]


def lemmatize_text(text: str) -> str:
    normalized = normalize_text(text)
    tokens = _TOKEN_RE.findall(normalized)
    return " ".join(_lemmatize_token(token) for token in tokens)


def build_clause_contexts(text: str) -> list[ClauseContext]:
    normalized_text = normalize_text(text)
    if not normalized_text:
        return []

    contexts: list[ClauseContext] = []
    search_from = 0

    for sentence_index, sentence in enumerate(split_sentences(normalized_text)):
        sentence_start = normalized_text.find(sentence, search_from)
        if sentence_start == -1:
            sentence_start = search_from
        clause_search_from = 0

        for clause_index, clause in enumerate(split_clauses(sentence)):
            clause_start_in_sentence = sentence.find(clause, clause_search_from)
            if clause_start_in_sentence == -1:
                clause_start_in_sentence = clause_search_from
            clause_search_from = clause_start_in_sentence + len(clause)

            contexts.append(
                ClauseContext(
                    sentenceIndex=sentence_index,
                    clauseIndex=clause_index,
                    startCharIndex=sentence_start + clause_start_in_sentence,
                    sentenceText=sentence,
                    clauseText=clause,
                    clauseTextNormalized=clause,
                    clauseTextLemmatized=lemmatize_text(clause),
                )
            )

        search_from = sentence_start + len(sentence)

    return contexts
