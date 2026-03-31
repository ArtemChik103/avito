from src.avito_splitter.preprocessing import lemmatize_text, normalize_text, split_clauses, split_sentences


def test_normalize_text_lowercases_and_normalizes_yo() -> None:
    assert normalize_text("  ЁЛКА  —\nТЕСТ  ") == "елка — тест"


def test_split_sentences_and_clauses() -> None:
    text = "Делаем ремонт, сантехнику; электрику. Отдельно потолки!"
    assert split_sentences(text) == [
        "делаем ремонт, сантехнику; электрику.",
        "отдельно потолки!",
    ]
    assert split_clauses("Делаем ремонт, сантехнику; электрику.") == [
        "делаем ремонт",
        "сантехнику",
        "электрику.",
    ]


def test_lemmatize_text_is_stable() -> None:
    text = "Натяжные потолки и сантехнические работы"
    assert lemmatize_text(text) == lemmatize_text(text)
    assert lemmatize_text(text) == "натяжной потолок и сантехнический работа"
