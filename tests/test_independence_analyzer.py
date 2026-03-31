from src.avito_splitter.category_extractor import CategoryExtractor
from src.avito_splitter.independence_analyzer import IndependenceAnalyzer
from src.avito_splitter.loaders import load_enriched_catalog
from src.avito_splitter.preprocessing import build_clause_contexts
from src.avito_splitter.schemas import AdInput


def analyze(description: str, source_mc_id: int = 201) -> list[tuple[int, str]]:
    item = AdInput(itemId=1, mcId=source_mc_id, mcTitle="Ремонт", description=description)
    contexts = build_clause_contexts(description)
    extractor = CategoryExtractor(load_enriched_catalog())
    evidences = extractor.extract(item, contexts)
    assessments = IndependenceAnalyzer().analyze(evidences, contexts)
    return [(assessment.evidence.mcId, assessment.status) for assessment in assessments]


def test_blocks_services_in_including_clause() -> None:
    assert analyze("Делаем ремонт под ключ, включая электрику и сантехнику.") == [
        (102, "blocked"),
        (101, "blocked"),
    ]


def test_confirms_service_with_otdelno_marker() -> None:
    assert analyze("Отдельно выполняем сантехнические работы.") == [(101, "confirmed")]


def test_confirms_service_with_neighbor_clause_marker() -> None:
    assert analyze("Сантехника, а также отдельно выполняем электромонтажные работы.") == [
        (101, "confirmed"),
        (102, "confirmed"),
    ]


def test_keeps_confirmed_evidence_when_blocked_exists_elsewhere() -> None:
    assert analyze(
        "Ремонт под ключ, включая электрику. Отдельно выполняем электромонтажные работы."
    ) == [
        (102, "blocked"),
        (102, "confirmed"),
    ]


def test_rejects_neutral_only_mentions() -> None:
    assert analyze("Выполняем ремонт под ключ с электрикой и сантехникой.") == [
        (102, "neutral"),
        (101, "neutral"),
    ]
