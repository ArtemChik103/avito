import json
from pathlib import Path

from pydantic import TypeAdapter

from src.avito_splitter.category_extractor import CategoryExtractor
from src.avito_splitter.preprocessing import build_clause_contexts
from src.avito_splitter.schemas import AdInput, EnrichedMicroCategory


def load_sample_catalog() -> list[EnrichedMicroCategory]:
    fixture_path = Path(__file__).parent / "fixtures" / "sample_microcategories.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    return TypeAdapter(list[EnrichedMicroCategory]).validate_python(payload)


def test_extracts_raw_phrase_match() -> None:
    extractor = CategoryExtractor(load_sample_catalog())
    item = AdInput(itemId=1, mcId=201, mcTitle="Ремонт", description="Отдельно делаем замена проводки.")

    evidences = extractor.extract(item, build_clause_contexts(item.description))

    assert [evidence.mcId for evidence in evidences] == [102]


def test_extracts_inflected_single_word_match() -> None:
    extractor = CategoryExtractor(load_sample_catalog())
    item = AdInput(itemId=2, mcId=201, mcTitle="Ремонт", description="Включая сантехнику в ремонт.")

    evidences = extractor.extract(item, build_clause_contexts(item.description))

    assert [evidence.mcId for evidence in evidences] == [101]


def test_excludes_source_category() -> None:
    extractor = CategoryExtractor(load_sample_catalog())
    item = AdInput(itemId=3, mcId=101, mcTitle="Сантехника", description="Сантехника и электрика отдельно.")

    evidences = extractor.extract(item, build_clause_contexts(item.description))

    assert [evidence.mcId for evidence in evidences] == [102]


def test_deduplicates_repeated_matches_per_clause() -> None:
    extractor = CategoryExtractor(load_sample_catalog())
    item = AdInput(
        itemId=4,
        mcId=201,
        mcTitle="Ремонт",
        description="Отдельно выполняем сантехнику и сантехнику.",
    )

    evidences = extractor.extract(item, build_clause_contexts(item.description))

    assert [evidence.mcId for evidence in evidences] == [101]
