from __future__ import annotations

import json
from pathlib import Path

from app.models import Catalog

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "catalog.json"


def load_catalog() -> Catalog | None:
    if not DATA_FILE.exists():
        return None
    return Catalog.model_validate_json(DATA_FILE.read_text(encoding="utf-8"))


def save_catalog(catalog: Catalog) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(catalog.model_dump_json(indent=2), encoding="utf-8")
