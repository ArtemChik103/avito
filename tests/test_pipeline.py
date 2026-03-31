from src.avito_splitter.loaders import load_gold_examples
from src.avito_splitter.pipeline import ServicesSplitter
from src.avito_splitter.schemas import AdInput, SplitResponse


def test_pipeline_matches_gold_examples() -> None:
    splitter = ServicesSplitter()

    for example in load_gold_examples():
        response = splitter.process(example.item)
        assert response.shouldSplit == example.expected.shouldSplit
        assert [draft.mcId for draft in response.drafts] == example.expected.draftMcIds
        assert SplitResponse.model_validate(response.model_dump()) == response


def test_pipeline_allows_neighbor_clause_confirmation() -> None:
    splitter = ServicesSplitter()
    item = AdInput(
        itemId=6001,
        mcId=201,
        mcTitle="Ремонт квартир и домов под ключ",
        description="Сантехника, а также отдельно выполняем электромонтажные работы.",
    )

    response = splitter.process(item)

    assert response.shouldSplit is True
    assert [draft.mcId for draft in response.drafts] == [101, 102]


def test_pipeline_returns_single_draft_for_repeated_category_mentions() -> None:
    splitter = ServicesSplitter()
    item = AdInput(
        itemId=6002,
        mcId=201,
        mcTitle="Ремонт квартир и домов под ключ",
        description="Отдельно выполняем сантехнику. Сантехника отдельно и еще раз сантехника отдельно.",
    )

    response = splitter.process(item)

    assert response.shouldSplit is True
    assert [draft.mcId for draft in response.drafts] == [101]
