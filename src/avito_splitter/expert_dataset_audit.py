from __future__ import annotations

import ast
import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .expert_dataset_lookup import EXPERT_DATASET_PATH, ROOT_DIR
from .pipeline import ServicesSplitter
from .schemas import AdInput

EXPERT_DATASET_CSV_PATH = ROOT_DIR / "rnc_dataset_markup.csv"


@dataclass(frozen=True)
class ExpertDatasetAudit:
    json_rows: int
    csv_rows: int
    json_non_numeric_item_ids: list[int]
    json_non_numeric_source_mc_ids: list[int]
    json_conflicting_duplicates: int
    csv_conflicting_duplicates: int
    only_in_json: int
    only_in_csv: int
    json_csv_value_mismatches: int
    case_type_counts: dict[str, int]


@dataclass(frozen=True)
class ExpertDatasetRegression:
    examples: int
    matched: int
    accuracy: float


def audit_expert_dataset(
    json_path: Path = EXPERT_DATASET_PATH,
    csv_path: Path = EXPERT_DATASET_CSV_PATH,
) -> ExpertDatasetAudit:
    json_rows = _load_json_rows(json_path)
    csv_rows = _load_csv_rows(csv_path)

    json_non_numeric_item_ids = [index for index, row in enumerate(json_rows) if not str(row.get("itemId", "")).isdigit()]
    json_non_numeric_source_mc_ids = [
        index for index, row in enumerate(json_rows) if not str(row.get("sourceMcId", "")).isdigit()
    ]

    json_map, json_conflicts = _build_normalized_map(json_rows)
    csv_map, csv_conflicts = _build_normalized_map(csv_rows)

    only_in_json = len([key for key in json_map if key not in csv_map])
    only_in_csv = len([key for key in csv_map if key not in json_map])
    value_mismatches = len([key for key in json_map if key in csv_map and json_map[key] != csv_map[key]])

    case_type_counts = dict(Counter(str(row.get("caseType", "")) for row in json_rows))
    return ExpertDatasetAudit(
        json_rows=len(json_rows),
        csv_rows=len(csv_rows),
        json_non_numeric_item_ids=json_non_numeric_item_ids,
        json_non_numeric_source_mc_ids=json_non_numeric_source_mc_ids,
        json_conflicting_duplicates=len(json_conflicts),
        csv_conflicting_duplicates=len(csv_conflicts),
        only_in_json=only_in_json,
        only_in_csv=only_in_csv,
        json_csv_value_mismatches=value_mismatches,
        case_type_counts=case_type_counts,
    )


def evaluate_expert_dataset(
    splitter: ServicesSplitter | None = None,
    json_path: Path = EXPERT_DATASET_PATH,
) -> ExpertDatasetRegression:
    splitter = splitter or ServicesSplitter()
    rows = _load_json_rows(json_path)

    matched = 0
    for row in rows:
        item = AdInput(
            itemId=int(row["itemId"]) if str(row.get("itemId", "")).isdigit() else 0,
            mcId=int(row["sourceMcId"]),
            mcTitle=str(row["sourceMcTitle"]),
            description=str(row["description"]),
        )
        response = splitter.process(item)
        expected_should_split = _parse_bool(row.get("shouldSplit"))
        expected_ids = _parse_ids(row.get("targetSplitMcIds"))
        if response.shouldSplit == expected_should_split and [draft.mcId for draft in response.drafts] == expected_ids:
            matched += 1

    total = len(rows)
    return ExpertDatasetRegression(examples=total, matched=matched, accuracy=(matched / total if total else 0.0))


def format_expert_dataset_report(
    audit: ExpertDatasetAudit,
    regression: ExpertDatasetRegression | None = None,
) -> str:
    lines = [
        "Expert Dataset Audit",
        f"JSON rows: {audit.json_rows}",
        f"CSV rows: {audit.csv_rows}",
        f"JSON non-numeric itemId rows: {audit.json_non_numeric_item_ids}",
        f"JSON non-numeric sourceMcId rows: {audit.json_non_numeric_source_mc_ids}",
        f"JSON conflicting duplicates: {audit.json_conflicting_duplicates}",
        f"CSV conflicting duplicates: {audit.csv_conflicting_duplicates}",
        f"Only in JSON: {audit.only_in_json}",
        f"Only in CSV: {audit.only_in_csv}",
        f"JSON/CSV value mismatches: {audit.json_csv_value_mismatches}",
        f"Case types: {audit.case_type_counts}",
    ]
    if regression is not None:
        lines.extend(
            [
                "",
                "Expert Dataset Regression",
                f"Matched: {regression.matched}/{regression.examples}",
                f"Accuracy: {regression.accuracy:.4f}",
            ]
        )
    return "\n".join(lines)


def _load_json_rows(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_csv_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def _build_normalized_map(rows: list[dict]) -> tuple[dict[tuple[str, str], tuple[str, tuple[int, ...]]], list[tuple[str, str]]]:
    mapping: dict[tuple[str, str], tuple[str, tuple[int, ...]]] = {}
    conflicts: list[tuple[str, str]] = []

    for row in rows:
        key = (str(row.get("sourceMcTitle", "")).strip(), str(row.get("description", "")).strip())
        value = (str(row.get("shouldSplit", "")).strip().lower(), tuple(_parse_ids(row.get("targetSplitMcIds"))))
        previous = mapping.get(key)
        if previous is not None and previous != value:
            conflicts.append(key)
            continue
        mapping[key] = value

    return mapping, conflicts


def _parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def _parse_ids(value: object) -> list[int]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [int(item) for item in value]
    return [int(item) for item in ast.literal_eval(str(value))]


if __name__ == "__main__":
    audit = audit_expert_dataset()
    regression = evaluate_expert_dataset()
    print(format_expert_dataset_report(audit, regression))
