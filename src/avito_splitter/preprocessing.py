from __future__ import annotations


def normalize_text(text: str) -> str:
    raise NotImplementedError


def split_sentences(text: str) -> list[str]:
    raise NotImplementedError


def split_clauses(sentence: str) -> list[str]:
    raise NotImplementedError


def lemmatize_text(text: str) -> str:
    raise NotImplementedError
