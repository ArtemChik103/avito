from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import TypeAdapter

from .pipeline import ServicesSplitter
from .schemas import GoldExample


@dataclass(frozen=True)
class CaseOutcome:
    case_name: str
    expected_should_split: bool
    actual_should_split: bool
    expected_ids: list[int]
    actual_ids: list[int]
    ok: bool


@dataclass(frozen=True)
class CaseSection:
    source: str
    total: int
    matched: int
    outcomes: list[CaseOutcome]


def build_case_report(splitter: ServicesSplitter | None = None) -> list[CaseSection]:
    splitter = splitter or ServicesSplitter()
    sections = [
        _build_gold_like_section(splitter, Path("data/gold_examples.json")),
        _build_gold_like_section(splitter, Path("data/synthetic_eval_examples.json")),
        _build_gold_like_section(splitter, Path("tests/fixtures/sample_cases.json")),
        _build_demo_section(splitter, Path("demo/demo_cases.json")),
    ]
    return sections


def format_case_report(sections: list[CaseSection]) -> str:
    total_cases = sum(section.total for section in sections)
    total_matched = sum(section.matched for section in sections)
    lines = [
        "Avito Services Splitter Case Report",
        f"Total matched: {total_matched}/{total_cases}",
        "",
    ]

    for section in sections:
        lines.append(f"[{section.source}] matched {section.matched}/{section.total}")
        for outcome in section.outcomes:
            status = "OK" if outcome.ok else "FAIL"
            lines.append(
                f"  {status:<4} {outcome.case_name} | "
                f"shouldSplit {outcome.actual_should_split} (expected {outcome.expected_should_split}) | "
                f"drafts {outcome.actual_ids} (expected {outcome.expected_ids})"
            )
        lines.append("")

    return "\n".join(lines).rstrip()


def _build_gold_like_section(splitter: ServicesSplitter, path: Path) -> CaseSection:
    adapter = TypeAdapter(list[GoldExample])
    payload = json.loads(path.read_text(encoding="utf-8"))
    examples = adapter.validate_python(payload)
    outcomes = [
        _evaluate_case(
            splitter,
            case_name=example.name,
            item=example.item.model_dump(),
            expected_should_split=example.expected.shouldSplit,
            expected_ids=example.expected.draftMcIds,
        )
        for example in examples
    ]
    return CaseSection(
        source=path.as_posix(),
        total=len(outcomes),
        matched=sum(outcome.ok for outcome in outcomes),
        outcomes=outcomes,
    )


def _build_demo_section(splitter: ServicesSplitter, path: Path) -> CaseSection:
    payload = json.loads(path.read_text(encoding="utf-8"))
    outcomes = [
        _evaluate_case(
            splitter,
            case_name=case["label"],
            item=case["item"],
            expected_should_split=case["expectedShouldSplit"],
            expected_ids=case["expectedDraftMcIds"],
        )
        for case in payload
    ]
    return CaseSection(
        source=path.as_posix(),
        total=len(outcomes),
        matched=sum(outcome.ok for outcome in outcomes),
        outcomes=outcomes,
    )


def _evaluate_case(
    splitter: ServicesSplitter,
    case_name: str,
    item: dict,
    expected_should_split: bool,
    expected_ids: list[int],
) -> CaseOutcome:
    response = splitter.process(item)
    actual_ids = [draft.mcId for draft in response.drafts]
    ok = response.shouldSplit == expected_should_split and actual_ids == expected_ids
    return CaseOutcome(
        case_name=case_name,
        expected_should_split=expected_should_split,
        actual_should_split=response.shouldSplit,
        expected_ids=expected_ids,
        actual_ids=actual_ids,
        ok=ok,
    )
