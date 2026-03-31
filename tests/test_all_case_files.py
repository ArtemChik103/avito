import json
from pathlib import Path

from pydantic import TypeAdapter

from src.avito_splitter.pipeline import ServicesSplitter
from src.avito_splitter.schemas import GoldExample


def test_all_gold_like_case_files_match_pipeline_outputs() -> None:
    splitter = ServicesSplitter()
    adapter = TypeAdapter(list[GoldExample])

    for relative_path in (
        "data/gold_examples.json",
        "data/synthetic_eval_examples.json",
        "tests/fixtures/sample_cases.json",
    ):
        path = Path(relative_path)
        examples = adapter.validate_python(json.loads(path.read_text(encoding="utf-8")))

        for example in examples:
            response = splitter.process(example.item)
            assert response.shouldSplit == example.expected.shouldSplit, (relative_path, example.name)
            assert [draft.mcId for draft in response.drafts] == example.expected.draftMcIds, (
                relative_path,
                example.name,
            )
            assert all(draft.text.strip() for draft in response.drafts), (relative_path, example.name)
            assert all(len(draft.text) <= 320 for draft in response.drafts), (relative_path, example.name)


def test_demo_case_file_matches_pipeline_outputs() -> None:
    splitter = ServicesSplitter()
    payload = json.loads(Path("demo/demo_cases.json").read_text(encoding="utf-8"))

    for case in payload:
        response = splitter.process(case["item"])
        assert response.shouldSplit == case["expectedShouldSplit"], case["label"]
        assert [draft.mcId for draft in response.drafts] == case["expectedDraftMcIds"], case["label"]
        assert all(draft.text.strip() for draft in response.drafts), case["label"]
        assert all(len(draft.text) <= 320 for draft in response.drafts), case["label"]
