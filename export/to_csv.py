"""export/to_csv.py — Serialise LCIDataset flows to CSV."""
from __future__ import annotations
import csv, os
from pipeline.models import LCIDataset
import config


def export_csv(lci: LCIDataset, path: str | None = None) -> str:
    if path is None:
        os.makedirs(config.DATA_OUTPUT, exist_ok=True)
        safe = lci.process_name.replace(" ", "_").replace(",", "")[:60]
        path = os.path.join(config.DATA_OUTPUT, f"{safe}.csv")
    fields = ["direction", "name", "amount", "unit", "category",
              "source", "confidence", "provenance"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for flow in lci.all_flows:
            w.writerow({
                "direction":  flow.direction,
                "name":       flow.name,
                "amount":     flow.amount,
                "unit":       flow.unit,
                "category":   flow.category,
                "source":     flow.source,
                "confidence": flow.confidence,
                "provenance": flow.provenance,
            })
    print(f"  [CSV]  → {path}")
    return path
