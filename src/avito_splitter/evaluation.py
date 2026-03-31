from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .loaders import load_examples
from .pipeline import ServicesSplitter
from .schemas import GoldExample


@dataclass(frozen=True)
class EvaluationMetrics:
    examples: int
    should_split_accuracy: float
    exact_draft_list_accuracy: float
    micro_precision: float
    micro_recall: float
    micro_f1: float
    true_positives: int
    false_positives: int
    false_negatives: int


def evaluate_examples(examples: list[GoldExample], splitter: ServicesSplitter | None = None) -> EvaluationMetrics:
    splitter = splitter or ServicesSplitter()

    should_split_correct = 0
    exact_draft_correct = 0
    true_positives = 0
    false_positives = 0
    false_negatives = 0

    for example in examples:
        response = splitter.process(example.item)
        predicted_ids = [draft.mcId for draft in response.drafts]
        expected_ids = example.expected.draftMcIds

        if response.shouldSplit == example.expected.shouldSplit:
            should_split_correct += 1
        if predicted_ids == expected_ids:
            exact_draft_correct += 1

        predicted_set = set(predicted_ids)
        expected_set = set(expected_ids)
        true_positives += len(predicted_set & expected_set)
        false_positives += len(predicted_set - expected_set)
        false_negatives += len(expected_set - predicted_set)

    precision = _safe_div(true_positives, true_positives + false_positives)
    recall = _safe_div(true_positives, true_positives + false_negatives)
    f1 = _safe_div(2 * precision * recall, precision + recall) if precision or recall else 0.0

    return EvaluationMetrics(
        examples=len(examples),
        should_split_accuracy=_safe_div(should_split_correct, len(examples)),
        exact_draft_list_accuracy=_safe_div(exact_draft_correct, len(examples)),
        micro_precision=precision,
        micro_recall=recall,
        micro_f1=f1,
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
    )


def evaluate_file(path: Path) -> EvaluationMetrics:
    return evaluate_examples(load_examples(path))


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0
