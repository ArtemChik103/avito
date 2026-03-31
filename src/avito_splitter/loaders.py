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


def _ensure_unique_mcids(catalog: list[MicroCategory | EnrichedMicroCategory], source_name: str) -> None:
    seen_ids: set[int] = set()
    for entry in catalog:
        if entry.mcId in seen_ids:
            raise ValueError(f"{source_name} contains duplicate mcId={entry.mcId}")
        seen_ids.add(entry.mcId)


def load_raw_catalog(path: Path = RAW_CATALOG_PATH) -> list[MicroCategory]:
    catalog = _load_list(path, MicroCategory)
    _ensure_unique_mcids(catalog, "raw catalog")
    return catalog


def load_enriched_catalog(path: Path = ENRICHED_CATALOG_PATH) -> list[EnrichedMicroCategory]:
    catalog = _load_list(path, EnrichedMicroCategory)
    _ensure_unique_mcids(catalog, "enriched catalog")
    return catalog


def load_gold_examples(path: Path = GOLD_EXAMPLES_PATH) -> list[GoldExample]:
    examples = _load_list(path, GoldExample)
    seen_names: set[str] = set()
    for entry in examples:
        if entry.name in seen_names:
            raise ValueError(f"gold examples contain duplicate name={entry.name}")
        seen_names.add(entry.name)
    return examples


def load_catalog_bundle(
    raw_path: Path = RAW_CATALOG_PATH,
    enriched_path: Path = ENRICHED_CATALOG_PATH,
) -> tuple[list[MicroCategory], list[EnrichedMicroCategory]]:
    raw_catalog = load_raw_catalog(raw_path)
    enriched_catalog = load_enriched_catalog(enriched_path)

    raw_by_id = {entry.mcId: entry for entry in raw_catalog}
    enriched_by_id = {entry.mcId: entry for entry in enriched_catalog}

    if raw_by_id.keys() != enriched_by_id.keys():
        raise ValueError("raw and enriched catalogs must contain the same mcIds")

    for mc_id, raw_entry in raw_by_id.items():
        enriched_entry = enriched_by_id[mc_id]
        if raw_entry.mcTitle != enriched_entry.mcTitle:
            raise ValueError(f"mcTitle mismatch for mcId={mc_id}")
        missing_phrases = set(raw_entry.keyPhrases) - set(enriched_entry.keyPhrases)
        if missing_phrases:
            raise ValueError(f"enriched catalog missing key phrases for mcId={mc_id}: {sorted(missing_phrases)}")

    return raw_catalog, enriched_catalog
