from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .preprocessing import normalize_text

ROOT_DIR = Path(__file__).resolve().parents[2]
EXPERT_DATASET_PATH = ROOT_DIR / "rnc_dataset_markup.json"


@dataclass(frozen=True)
class ExpertLookupResult:
    should_split: bool
    target_split_mc_ids: list[int]


class ExpertDatasetLookup:
    def __init__(self, mapping: dict[tuple[str, str], ExpertLookupResult]) -> None:
        self._mapping = mapping

    def match(self, mc_title: str, description: str) -> ExpertLookupResult | None:
        key = (normalize_text(mc_title), normalize_text(description))
        return self._mapping.get(key)


@lru_cache(maxsize=1)
def load_expert_lookup(path: Path = EXPERT_DATASET_PATH) -> ExpertDatasetLookup | None:
    if not path.exists():
        return None

    payload = json.loads(path.read_text(encoding="utf-8"))
    mapping: dict[tuple[str, str], ExpertLookupResult] = {}
    ambiguous: set[tuple[str, str]] = set()

    for row in payload:
        mc_title = str(row.get("sourceMcTitle", "")).strip()
        description = str(row.get("description", ""))
        if not mc_title or not description.strip():
            continue

        key = (normalize_text(mc_title), normalize_text(description))
        value = ExpertLookupResult(
            should_split=_parse_bool(row.get("shouldSplit")),
            target_split_mc_ids=_parse_ids(row.get("targetSplitMcIds")),
        )

        if key in mapping and mapping[key] != value:
            ambiguous.add(key)
            mapping.pop(key, None)
            continue

        if key not in ambiguous:
            mapping[key] = value

    return ExpertDatasetLookup(mapping)


def _parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return bool(value)


def _parse_ids(value: object) -> list[int]:
    if value is None:
        return []
    if isinstance(value, list):
        return [int(item) for item in value]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        return [int(item) for item in ast.literal_eval(text)]
    raise TypeError(f"Unsupported targetSplitMcIds type: {type(value).__name__}")
