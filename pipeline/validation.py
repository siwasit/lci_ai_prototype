"""
pipeline/validation.py
──────────────────────
Sanity-check extracted LCI values against literature-derived ranges.
Flags outliers for mandatory expert review before DB insertion.
"""
from __future__ import annotations
from pipeline.models import LCIFlow, LCIDataset

# Acceptable literature ranges keyed by substring match on flow name
_RANGES: dict[str, dict] = {
    "urea":             {"min": 40,    "max": 150,   "unit": "kg"},
    "ch4":              {"min": 15.0,  "max": 50.0,  "unit": "kg"},
    "n2o":              {"min": 0.3,   "max": 2.5,   "unit": "kg"},
    "co2":              {"min": 30.0,  "max": 100.0, "unit": "kg"},
    "diesel":           {"min": 15.0,  "max": 35.0,  "unit": "L"},
    "irrigation water": {"min": 1000,  "max": 5000,  "unit": "m3"},
    "no3":              {"min": 2.0,   "max": 12.0,  "unit": "kg"},
    "nh3":              {"min": 1.0,   "max": 10.0,  "unit": "kg"},
}


def validate_flow(flow: LCIFlow) -> dict:
    name_l = flow.name.lower()
    for key, rng in _RANGES.items():
        if key in name_l:
            try:
                val = float(str(flow.amount).replace(",", ""))
                ok  = rng["min"] <= val <= rng["max"]
                return {
                    "flow":   flow.name,
                    "value":  val,
                    "unit":   flow.unit,
                    "range":  f"{rng['min']}–{rng['max']} {rng['unit']}",
                    "status": "PASS" if ok else "FLAG",
                }
            except (ValueError, TypeError):
                pass
    return {"flow": flow.name, "status": "NO_RANGE"}


def validate_dataset(lci: LCIDataset) -> list[dict]:
    results = [validate_flow(f) for f in lci.all_flows]
    flags   = [r for r in results if r["status"] == "FLAG"]
    passed  = [r for r in results if r["status"] == "PASS"]

    print(f"[Validation] PASS: {len(passed)}  FLAG: {len(flags)}  "
          f"NO_RANGE: {len(results)-len(passed)-len(flags)}")
    if flags:
        print("  ⚠ Flagged for expert review:")
        for f in flags:
            print(f"    • {f['flow']}: {f['value']} {f['unit']} "
                  f"(expected {f['range']})")
    else:
        print("  ✓ All range-checked flows within literature bounds.")
    return results
