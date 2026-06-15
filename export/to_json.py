"""export/to_json.py — Serialise LCIDataset to JSON."""
from __future__ import annotations
import json, os
from pipeline.models import LCIDataset
import config


def export_json(lci: LCIDataset, path: str | None = None) -> str:
    if path is None:
        os.makedirs(config.DATA_OUTPUT, exist_ok=True)
        safe = lci.process_name.replace(" ", "_").replace(",", "")[:60]
        path = os.path.join(config.DATA_OUTPUT, f"{safe}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(lci.to_dict(), f, indent=2, ensure_ascii=False)
    print(f"  [JSON] → {path}")
    return path
