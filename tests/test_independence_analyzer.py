from src.avito_splitter.category_extractor import CategoryExtractor
from src.avito_splitter.independence_analyzer import IndependenceAnalyzer
from src.avito_splitter.loaders import load_enriched_catalog
from src.avito_splitter.preprocessing import build_clause_contexts
from src.avito_splitter.schemas import AdInput


def analyze(
    description: str,
    source_mc_id: int = 101,
    source_mc_title: str = "Ремонт квартир и домов под ключ",
) -> list[tuple[int, str]]:
    item = AdInput(itemId=1, mcId=source_mc_id, mcTitle=source_mc_title, description=description)
    contexts = build_clause_contexts(description)
    extractor = CategoryExtractor(load_enriched_catalog())
    evidences = extractor.extract(item, contexts)
    assessments = IndependenceAnalyzer().analyze(evidences, contexts)
    return [(assessment.evidence.mcId, assessment.status) for assessment in assessments]


def test_blocks_services_in_including_clause() -> None:
    assert analyze("Делаем ремонт под ключ, включая электрику и сантехнику.") == [
        (103, "blocked"),
        (102, "blocked"),
    ]


def test_confirms_service_with_otdelno_marker() -> None:
    assert analyze("Отдельно выполняем сантехнические работы.") == [(102, "confirmed")]


def test_confirms_service_with_neighbor_clause_marker() -> None:
    assert analyze("Сантехника, а также отдельно выполняем электромонтажные работы.") == [
        (102, "confirmed"),
        (103, "confirmed"),
    ]


def test_keeps_confirmed_evidence_when_blocked_exists_elsewhere() -> None:
    assert analyze(
        "Ремонт под ключ, включая электрику. Отдельно выполняем электромонтажные работы."
    ) == [
        (103, "blocked"),
        (103, "confirmed"),
    ]


def test_rejects_neutral_only_mentions() -> None:
    assert analyze("Выполняем ремонт под ключ с электрикой и сантехникой.") == [
        (103, "neutral"),
        (102, "neutral"),
    ]
