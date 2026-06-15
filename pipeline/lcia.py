"""
pipeline/lcia.py
────────────────
LCIA characterisation — Global Warming Potential (GWP100, IPCC AR6).
Extend _CF_GWP100 to add more impact categories (eutrophication, etc.)
"""
from __future__ import annotations
from pipeline.models import LCIDataset

# IPCC AR6 GWP100 characterisation factors
_CF_GWP100: dict[str, float] = {
    "ch4":              27.9,   # biogenic
    "methane":          27.9,
    "n2o":              273.0,
    "nitrous oxide":    273.0,
    "co2":              1.0,
    "carbon dioxide":   1.0,
}


def _match_cf(name: str) -> float | None:
    n = name.lower()
    for key, cf in _CF_GWP100.items():
        if key in n:
            return cf
    return None


def calculate_gwp100(lci: LCIDataset) -> dict:
    """
    Return GWP100 breakdown and total for all emission flows.
    Result keys: flow name → {amount_kg, cf, co2eq}; TOTAL → float
    """
    results: dict[str, object] = {}
    total = 0.0
    for flow in lci.outputs:
        if "emission" not in flow.category.lower():
            continue
        cf = _match_cf(flow.name)
        if cf is None:
            continue
        try:
            amt = float(str(flow.amount).replace(",", ""))
        except (ValueError, TypeError):
            continue
        contribution = amt * cf
        results[flow.name] = {
            "amount_kg": amt,
            "cf":        cf,
            "co2eq":     round(contribution, 2),
        }
        total += contribution

    results["TOTAL"] = round(total, 2)
    results["unit"]  = "kg CO2-eq per functional unit"
    return results


def print_gwp100(results: dict) -> None:
    print(f"\n  {'Emission Flow':<45} {'kg':>8} {'CF':>7} {'CO2-eq':>10}")
    print("  " + "-" * 73)
    for name, data in results.items():
        if name in ("TOTAL", "unit"):
            continue
        print(f"  {name:<45} {data['amount_kg']:>8.2f} "
              f"{data['cf']:>7.1f} {data['co2eq']:>10.2f}")
    print("  " + "-" * 73)
    total = results["TOTAL"]
    print(f"  {'TOTAL GWP100':<45} {'':>8} {'':>7} {total:>10.2f} kg CO2-eq")
    print(f"  = {total/1000:.4f} kg CO2-eq / kg paddy "
          f"(lit. range: 0.83–1.34 kg CO2-eq/kg)")
