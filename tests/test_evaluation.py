from pathlib import Path

from src.avito_splitter.evaluation import evaluate_file


def test_synthetic_eval_dataset_matches_expected_outputs() -> None:
    metrics = evaluate_file(Path("data/synthetic_eval_examples.json"))

    assert metrics.examples == 25
    assert metrics.should_split_accuracy == 1.0
    assert metrics.exact_draft_list_accuracy == 1.0
    assert metrics.micro_precision == 1.0
    assert metrics.micro_recall == 1.0
    assert metrics.micro_f1 == 1.0
