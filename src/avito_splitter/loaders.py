from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, TypeAdapter

from .schemas import EnrichedMicroCategory, GoldExample, MicroCategory

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
RAW_CATALOG_PATH = DATA_DIR / "microcategories.raw.json"
ENRICHED_CATALOG_PATH = DATA_DIR / "microcategories.enriched.json"
GOLD_EXAMPLES_PATH = DATA_DIR / "gold_examples.json"

ModelT = TypeVar("ModelT", bound=BaseModel)


def _load_json(path: Path) -> object:
    if not path.exists():
        raise FileNotFoundError(f"Required data file is missing: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_list(path: Path, model_type: type[ModelT]) -> list[ModelT]:
    raw_payload = _load_json(path)
    adapter = TypeAdapter(list[model_type])
    return adapter.validate_python(raw_payload)


def load_raw_catalog(path: Path = RAW_CATALOG_PATH) -> list[MicroCategory]:
    return _load_list(path, MicroCategory)


def load_enriched_catalog(path: Path = ENRICHED_CATALOG_PATH) -> list[EnrichedMicroCategory]:
    catalog = _load_list(path, EnrichedMicroCategory)
    for entry in catalog:
        if not entry.matchPhrases:
            raise ValueError(f"Enriched microcategory {entry.mcId} must define matchPhrases")
        if not entry.draftLead.strip():
            raise ValueError(f"Enriched microcategory {entry.mcId} must define draftLead")
    return catalog


def load_gold_examples(path: Path = GOLD_EXAMPLES_PATH) -> list[GoldExample]:
    return _load_list(path, GoldExample)
