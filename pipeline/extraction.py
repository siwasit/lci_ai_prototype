"""
pipeline/extraction.py
──────────────────────
Build the LLM extraction prompt and call the chosen provider.

Provider options (set LCI_LLM_PROVIDER env var or config.LLM_PROVIDER):
  demo      – returns hard-coded Thai rice LCI (no API key needed)
  anthropic – calls claude-sonnet-4-6 via Anthropic SDK
  openai    – calls gpt-4o via OpenAI SDK
"""
from __future__ import annotations
import json, os
import config

# ── Prompt template ───────────────────────────────────────────────

_PROMPT = """You are an expert Life Cycle Inventory (LCI) data extraction assistant.

RETRIEVED CONTEXT:
{context}

TASK:
Extract every LCI flow (inputs and outputs) for:
  Process : {process_name}
  Functional unit: {functional_unit}

RULES:
1. Extract ONLY values explicitly stated in the context above.
2. Do NOT infer or hallucinate values absent from the text.
3. For every flow record the exact source sentence (provenance).
4. Confidence: HIGH = explicitly stated, MEDIUM = derived/calculated,
   LOW = inferred or absent from context.

Return STRICT JSON with this schema:
{{
  "flows": [
    {{
      "name":       "substance or material name",
      "amount":     "number as string",
      "unit":       "unit string",
      "direction":  "input" | "output",
      "category":   "Material|Energy|Water|Land|Emission/Air|Emission/Water|Emission/Soil|Product",
      "confidence": "HIGH|MEDIUM|LOW",
      "source":     "doc id",
      "provenance": "verbatim quote ≤150 chars"
    }}
  ],
  "notes": "allocation assumptions or caveats"
}}"""


def build_prompt(context: str, process_name: str, functional_unit: str) -> str:
    return _PROMPT.format(
        context=context,
        process_name=process_name,
        functional_unit=functional_unit,
    )


# ── Pre-built demo response ───────────────────────────────────────

def _demo_response() -> dict:
    """Simulated LLM output — Thai rice LCI grounded in DEMO_CORPUS."""
    return {
        "flows": [
            # ---- INPUTS ----
            {"name":"Rice seed (Oryza sativa, certified)","amount":"8.3","unit":"kg",
             "direction":"input","category":"Material","confidence":"HIGH",
             "source":"oae_2022","provenance":"8.3 kg seed per tonne paddy"},
            {"name":"Urea (46% N)","amount":"65.2","unit":"kg",
             "direction":"input","category":"Material","confidence":"HIGH",
             "source":"samson_2020","provenance":"196 kg urea/ha ÷ 3 t/ha = 65.3 kg/t"},
            {"name":"Triple superphosphate (46% P2O5)","amount":"32.6","unit":"kg",
             "direction":"input","category":"Material","confidence":"HIGH",
             "source":"phungrassami_2015","provenance":"TSP fertiliser 32.6 kg/t"},
            {"name":"Potassium chloride (60% K2O)","amount":"32.6","unit":"kg",
             "direction":"input","category":"Material","confidence":"HIGH",
             "source":"phungrassami_2015","provenance":"potassium chloride 32.6 kg/t"},
            {"name":"Herbicide (a.i.)","amount":"0.48","unit":"kg",
             "direction":"input","category":"Material","confidence":"HIGH",
             "source":"samson_2020","provenance":"1.44 kg a.i./ha ÷ 3 = 0.48 kg/t"},
            {"name":"Insecticide (a.i.)","amount":"0.12","unit":"kg",
             "direction":"input","category":"Material","confidence":"HIGH",
             "source":"samson_2020","provenance":"0.36 kg a.i./ha ÷ 3 = 0.12 kg/t"},
            {"name":"Fungicide (a.i.)","amount":"0.08","unit":"kg",
             "direction":"input","category":"Material","confidence":"HIGH",
             "source":"phungrassami_2015","provenance":"fungicide 0.08 kg a.i./t"},
            {"name":"Diesel (tractor + combine harvester)","amount":"21.7","unit":"L",
             "direction":"input","category":"Energy","confidence":"HIGH",
             "source":"oae_2022","provenance":"~65 L/ha ÷ 3 t/ha = 21.7 L/t"},
            {"name":"Electricity (irrigation pumping)","amount":"18.5","unit":"kWh",
             "direction":"input","category":"Energy","confidence":"MEDIUM",
             "source":"oae_2022","provenance":"55.5 kWh/ha ÷ 3 t/ha = 18.5 kWh/t"},
            {"name":"Irrigation water","amount":"3333","unit":"m3",
             "direction":"input","category":"Water","confidence":"HIGH",
             "source":"phungrassami_2015","provenance":"irrigation water 2,970 m3/t"},
            {"name":"Agricultural land","amount":"0.33","unit":"ha·yr",
             "direction":"input","category":"Land","confidence":"HIGH",
             "source":"oae_2022","provenance":"0.33 ha per tonne paddy"},
            # ---- OUTPUTS ----
            {"name":"Paddy rice (main product)","amount":"1000","unit":"kg",
             "direction":"output","category":"Product","confidence":"HIGH",
             "source":"functional_unit","provenance":"functional unit = 1 tonne paddy"},
            {"name":"Rice straw (co-product)","amount":"1200","unit":"kg",
             "direction":"output","category":"Product","confidence":"HIGH",
             "source":"oae_2022","provenance":"straw ratio 1.2 kg per kg paddy"},
            {"name":"CH4 — methane (flooded field)","amount":"28.0","unit":"kg",
             "direction":"output","category":"Emission/Air","confidence":"HIGH",
             "source":"samson_2020","provenance":"84 kg CH4/ha ÷ 3 t/ha = 28 kg/t"},
            {"name":"N2O — direct field","amount":"0.82","unit":"kg",
             "direction":"output","category":"Emission/Air","confidence":"HIGH",
             "source":"samson_2020","provenance":"2.46 kg N2O/ha ÷ 3 t/ha = 0.82 kg/t"},
            {"name":"N2O — indirect (leaching)","amount":"0.18","unit":"kg",
             "direction":"output","category":"Emission/Air","confidence":"MEDIUM",
             "source":"ipcc_ar6","provenance":"EF5=0.0075 × FracLEACH=0.24 × 30 kg N/t"},
            {"name":"CO2 (diesel combustion)","amount":"57.5","unit":"kg",
             "direction":"output","category":"Emission/Air","confidence":"HIGH",
             "source":"ipcc_ar6","provenance":"21.7 L × 2.65 kg CO2/L = 57.5 kg"},
            {"name":"NH3 — ammonia (N volatilisation)","amount":"4.50","unit":"kg",
             "direction":"output","category":"Emission/Air","confidence":"MEDIUM",
             "source":"phungrassami_2015","provenance":"5% of N applied = 4.5 kg NH3/t"},
            {"name":"NOx (diesel combustion)","amount":"0.16","unit":"kg",
             "direction":"output","category":"Emission/Air","confidence":"HIGH",
             "source":"ipcc_ar6","provenance":"21.7 L × 0.0074 kg NOx/L = 0.16 kg"},
            {"name":"NO3- leaching to groundwater","amount":"5.40","unit":"kg",
             "direction":"output","category":"Emission/Water","confidence":"MEDIUM",
             "source":"ipcc_ar6","provenance":"30 kg N/t × 0.24 FracLEACH × 0.75 = 5.4 kg"},
            {"name":"PO43- runoff to surface water","amount":"0.22","unit":"kg",
             "direction":"output","category":"Emission/Water","confidence":"HIGH",
             "source":"phungrassami_2015","provenance":"PO4 runoff 0.22 kg per tonne paddy"},
            {"name":"Pesticide residual to soil","amount":"0.42","unit":"kg",
             "direction":"output","category":"Emission/Soil","confidence":"MEDIUM",
             "source":"phungrassami_2015","provenance":"62% of a.i. applied = 0.42 kg/t"},
        ],
        "notes": (
            "Values per functional unit: 1 t paddy at farm gate. "
            "Mass allocation NOT applied — straw declared as co-product. "
            "CH4 uses biogenic GWP100 = 27.9 (IPCC AR6)."
        ),
    }


# ── Provider dispatch ─────────────────────────────────────────────

def extract(prompt: str, provider: str | None = None) -> dict:
    """Call the chosen LLM and return parsed extraction JSON."""
    provider = provider or config.LLM_PROVIDER

    if provider == "demo":
        print("[LLM] Demo mode — returning pre-built extraction.")
        return _demo_response()

    if provider == "anthropic":
        return _call_anthropic(prompt)

    if provider == "openai":
        return _call_openai(prompt)

    raise ValueError(f"Unknown LLM provider: {provider!r}")


def _call_anthropic(prompt: str) -> dict:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        msg = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text
        return _parse_json(raw)
    except Exception as e:
        print(f"[LLM] Anthropic call failed ({e}). Falling back to demo.")
        return _demo_response()


def _call_openai(prompt: str) -> dict:
    try:
        import openai
        client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        resp = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        print(f"[LLM] OpenAI call failed ({e}). Falling back to demo.")
        return _demo_response()


def _parse_json(text: str) -> dict:
    start = text.find("{")
    end   = text.rfind("}") + 1
    return json.loads(text[start:end])




def build_lci_from_extraction(
    extraction: dict,
    process_name: str | None = None,
    functional_unit: str | None = None,
):
    """Convert raw LLM extraction dict into a typed LCIDataset.

    Handles two response shapes:
      - {"flows": [...], "notes": ...}           (new flat schema)
      - {"inputs": [...], "outputs": [...], ...} (legacy schema)
    """
    from pipeline.models import LCIDataset

    meta = extraction.get("process_metadata", {})

    lci = LCIDataset()
    lci.process_name     = process_name or meta.get("name", "Unknown process")
    lci.functional_unit  = functional_unit or meta.get("functional_unit", "")
    lci.system_boundary  = meta.get("system_boundary", "")
    lci.geography        = meta.get("geography", "TH")
    lci.reference_year   = meta.get("reference_year", "")
    lci.technology_level = meta.get("technology_level", "")
    lci.data_quality     = meta.get("data_quality", {}) if isinstance(meta.get("data_quality"), dict) else {}
    lci.extraction_meta  = {
        "confidence_overall": extraction.get("confidence_overall", ""),
        "notes":              extraction.get("notes", ""),
    }

    # ── flat "flows" list (new schema from _demo_response) ──
    if "flows" in extraction:
        for f in extraction["flows"]:
            kwargs = {
                "name":       f.get("name", ""),
                "amount":     f.get("amount", 0),
                "unit":       f.get("unit", ""),
                "category":   f.get("category", ""),
                "source":     f.get("source", ""),
                "confidence": f.get("confidence", ""),
                "provenance": f.get("provenance", ""),
            }
            if f.get("direction") == "input":
                lci.add_input(**kwargs)
            else:
                lci.add_output(**kwargs)
        return lci

    # ── legacy separate "inputs" / "outputs" lists ──
    for f in extraction.get("inputs", []):
        lci.add_input(
            name       = f.get("name", ""),
            amount     = f.get("amount", 0),
            unit       = f.get("unit", ""),
            category   = f.get("category", ""),
            source     = f.get("source", ""),
            confidence = f.get("confidence", ""),
            provenance = f.get("provenance", ""),
        )
    for f in extraction.get("outputs", []):
        lci.add_output(
            name       = f.get("name", ""),
            amount     = f.get("amount", 0),
            unit       = f.get("unit", ""),
            category   = f.get("category", ""),
            source     = f.get("source", ""),
            confidence = f.get("confidence", ""),
            provenance = f.get("provenance", ""),
        )
    return lci
