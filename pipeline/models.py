"""
pipeline/models.py
──────────────────
Core data structures (ISO 14048-compatible).

LCIFlow   — one input or output flow with provenance metadata
LCIDataset — a complete unit-process dataset ready for export
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LCIFlow:
    """One exchange in an LCI unit process (ISO 14048 / ILCD exchange)."""
    name:           str
    amount:         float
    unit:           str
    category:       str          # Material | Energy | Water | Land |
                                 # Emission/Air | Emission/Water | Emission/Soil | Product
    source:         str          # bibliographic reference id
    confidence:     str  = "LOW" # HIGH | MEDIUM | LOW
    provenance:     str  = ""    # verbatim text passage from source
    direction:      str  = "input"  # input | output

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    def __str__(self) -> str:
        tag = f"[{self.confidence}]" if self.confidence else ""
        return (f"  {tag:8s} {str(self.amount):>12} {self.unit:<8}  "
                f"{self.name}  ({self.source})")


class LCIDataset:
    """
    A complete unit-process LCI dataset.
    All mandatory ISO TS-14048:2002 fields are present.
    """

    def __init__(self):
        self.process_name:     str  = ""
        self.functional_unit:  str  = ""
        self.system_boundary:  str  = ""
        self.geography:        str  = ""
        self.reference_year:   str  = ""
        self.technology_level: str  = ""
        self.data_quality:     dict = {}
        self.extraction_meta:  dict = {}
        self.inputs:  list[LCIFlow] = []
        self.outputs: list[LCIFlow] = []

    def add_input(self, **kw):
        kw.setdefault("direction", "input")
        self.inputs.append(LCIFlow(**kw))

    def add_output(self, **kw):
        kw.setdefault("direction", "output")
        self.outputs.append(LCIFlow(**kw))

    @property
    def all_flows(self) -> list[LCIFlow]:
        return self.inputs + self.outputs

    def to_dict(self) -> dict:
        return {
            "process_name":     self.process_name,
            "functional_unit":  self.functional_unit,
            "system_boundary":  self.system_boundary,
            "geography":        self.geography,
            "reference_year":   self.reference_year,
            "technology_level": self.technology_level,
            "data_quality":     self.data_quality,
            "extraction_meta":  self.extraction_meta,
            "inputs":  [f.to_dict() for f in self.inputs],
            "outputs": [f.to_dict() for f in self.outputs],
        }

    def summary(self) -> str:
        w = 70
        lines = [
            "=" * w,
            f"  {self.process_name}",
            "=" * w,
            f"  FU      : {self.functional_unit}",
            f"  Boundary: {self.system_boundary}",
            f"  Geo     : {self.geography}  |  Year: {self.reference_year}",
            "",
            f"  INPUTS  ({len(self.inputs)} flows)",
            "  " + "-" * (w - 2),
        ]
        for f in self.inputs:
            lines.append(str(f))
        lines += ["", f"  OUTPUTS ({len(self.outputs)} flows)", "  " + "-" * (w - 2)]
        for f in self.outputs:
            lines.append(str(f))
        lines += ["", "  DATA QUALITY (ISO 14044)"]
        for k, v in self.data_quality.items():
            lines.append(f"    {k:<35}: {v}")
        lines.append("=" * w)
        return "\n".join(lines)

    @classmethod
    def from_dict(cls, d: dict) -> "LCIDataset":
        lci = cls()
        lci.process_name     = d.get("process_name", "")
        lci.functional_unit  = d.get("functional_unit", "")
        lci.system_boundary  = d.get("system_boundary", "")
        lci.geography        = d.get("geography", "")
        lci.reference_year   = d.get("reference_year", "")
        lci.technology_level = d.get("technology_level", "")
        lci.data_quality     = d.get("data_quality", {})
        lci.extraction_meta  = d.get("extraction_meta", {})
        lci.inputs  = [LCIFlow(**f) for f in d.get("inputs",  [])]
        lci.outputs = [LCIFlow(**f) for f in d.get("outputs", [])]
        return lci

    def remove_flow(self, direction: str, idx: int) -> None:
        """Remove a flow by index within its direction list."""
        if direction == "input":
            self.inputs.pop(idx)
        else:
            self.outputs.pop(idx)

    def correct_flow_amount(self, direction: str, idx: int, new_amount: float) -> None:
        """Correct the amount of a specific flow."""
        if direction == "input":
            self.inputs[idx].amount = new_amount
        else:
            self.outputs[idx].amount = new_amount
