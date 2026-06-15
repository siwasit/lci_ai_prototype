# LCI-AI Prototype

**Automated Life Cycle Inventory extraction using RAG + LLM — with Expert Review Web UI**

A modular Python prototype that demonstrates how AI can extract Life Cycle Inventory (LCI) data from scientific literature, present it to an expert for review and correction, and export it in JSON, CSV, and ILCD-compliant XML — the standard exchange format for the Thai National LCI Database.

---

## Project Goal

Thai National LCI data currently sits locked inside PDF reports and peer-reviewed papers. This prototype shows a viable pipeline to unlock it:

1. Ingest PDFs → chunk text → build a retrieval index
2. Retrieve the most relevant passages for a given process
3. Feed context to an LLM with a structured extraction prompt
4. Parse, validate, and characterise the resulting flows
5. **Present flagged flows to an expert for Keep / Correct / Remove review**
6. Export expert-approved data in JSON / CSV / ILCD XML

The demo runs end-to-end with hard-coded Thai paddy rice data (no API key needed).

---

## Directory Structure

```
lci_ai_prototype/
├── app.py                     # Flask web UI entry point
├── main.py                    # CLI entry point
├── config.py                  # Central settings (paths, model names, chunking params)
├── requirements.txt
│
├── pipeline/
│   ├── models.py              # LCIFlow dataclass + LCIDataset (with from_dict, corrections)
│   ├── corpus.py              # Document loader, demo corpus, chunker, PDF loader
│   ├── retrieval.py           # Keyword-based retrieval (upgradeable to FAISS)
│   ├── extraction.py          # Prompt builder + LLM dispatch (demo/Anthropic/OpenAI)
│   ├── validation.py          # Range-based flow validation (PASS / FLAG / NO_RANGE)
│   └── lcia.py                # GWP100 characterisation (IPCC AR6)
│
├── export/
│   ├── to_json.py             # JSON export
│   ├── to_csv.py              # CSV export
│   └── to_ilcd.py             # ILCD-compliant XML export
│
├── templates/
│   ├── base.html              # Shared layout (Bootstrap 5, navbar)
│   ├── index.html             # Step 1 — configure process + upload PDF
│   ├── review.html            # Step 2 — expert flow review (Keep/Correct/Remove)
│   └── results.html           # Step 3 — GWP summary + download buttons
│
└── data/
    ├── input/                 # Drop your PDFs here
    └── output/                # Generated JSON, CSV, ILCD XML appear here
```

---

## Quick Start

### Option A — Web UI (recommended)

```bash
cd lci_ai_prototype
pip install flask pdfplumber python-dotenv
python app.py
# open http://localhost:5000
```

### Option B — CLI

```bash
pip install pdfplumber python-dotenv
python main.py --mode demo          # demo data, no API key needed
python main.py --mode extract --pdf data/input/ --api anthropic
python main.py --mode validate      # validate demo LCI only
```

Set your API key before using a real LLM:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."   # or OPENAI_API_KEY
```

---

## Expert Workflow (Web UI)

```
Step 1 — Configure    http://localhost:5000/
  ┌─────────────────────────────────────────────┐
  │  Process name        [Paddy rice, Thailand] │
  │  Functional unit     [1 tonne at farm gate] │
  │  System boundary     [Cradle to farm gate]  │
  │  Allocation method   [No allocation ▼]      │
  │  LLM provider        [Demo ▼]               │
  │  Upload PDF          [Choose file...]        │
  │              [ Run Extraction Pipeline → ]   │
  └─────────────────────────────────────────────┘
        ↓ pipeline runs (index → retrieve → LLM → validate → GWP100)
Step 2 — Review       /review
  ┌─────────────────────────────────────────────┐
  │  GWP100: 1,112 kg CO₂-eq   11 in  11 out  │
  │                                             │
  │  ⚠ 2 flows flagged for expert review:       │
  │  N2O indirect  0.18 kg  expected 0.3–2.5   │
  │    Action [Keep ▼]  Corrected value [    ] │
  │  NOx diesel    0.16 kg  expected 15–35 L   │
  │    Action [Correct ▼]  Corrected value [18]│
  │                                             │
  │  All flows table (read-only, colour coded) │
  │  GWP100 breakdown table                    │
  │         [ ✓ Approve & Export Dataset ]      │
  └─────────────────────────────────────────────┘
        ↓ corrections applied, re-validated, exported
Step 3 — Export       /results
  ┌─────────────────────────────────────────────┐
  │  Final GWP100: 1,112 kg CO₂-eq             │
  │  [ 📄 Download JSON  ]                      │
  │  [ 📊 Download CSV   ]                      │
  │  [ 🗂  Download ILCD XML ]                  │
  └─────────────────────────────────────────────┘
```

---

## Pipeline Walkthrough

```
PDFs / demo corpus
       │
       ▼
  [1] corpus.py        chunk_document() → 400-token chunks, 50-token overlap
       │
       ▼
  [2] retrieval.py     retrieve() → top-5 chunks by keyword overlap
                       (upgrade path: FAISS + sentence-transformers)
       │
       ▼
  [3] extraction.py    build_prompt() → chain-of-thought prompt with context
                       extract()      → LLM returns structured JSON
       │
       ▼
  [4] models.py        build_lci_from_extraction() → LCIDataset object
                       (handles flat "flows" list or legacy inputs/outputs)
       │
       ▼
  [5] validation.py    validate_dataset() → PASS / FLAG / NO_RANGE per flow
       │
       ▼  ← Expert reviews here (web UI) ←
       │
       ▼
  [6] lcia.py          calculate_gwp100() → kg CO₂-eq / functional unit
       │
       ▼
  [7] export/          to_json.py  → <process>.json
                       to_csv.py   → <process>.csv
                       to_ilcd.py  → <process>_ILCD.xml
```

---

## Demo Output (Thai Paddy Rice)

**Process:** Paddy rice cultivation, conventional, irrigated, Thailand
**Functional unit:** 1 tonne paddy rice at farm gate, 14% moisture content
**System boundary:** Cradle to farm gate (excludes milling)

### Key inputs (11 total)

| Flow | Amount | Unit | Category |
|------|--------|------|----------|
| Urea (46% N) | 65.2 | kg | Material |
| Triple superphosphate | 32.6 | kg | Material |
| Potassium chloride | 32.6 | kg | Material |
| Diesel (tractor + harvester) | 21.7 | L | Energy |
| Electricity (irrigation) | 18.5 | kWh | Energy |
| Irrigation water | 3,333 | m³ | Water |
| Agricultural land | 0.33 | ha·yr | Land |

### Key outputs / emissions (11 total)

| Flow | Amount | Unit | Category |
|------|--------|------|----------|
| Paddy rice (main product) | 1,000 | kg | Product |
| Rice straw (co-product) | 1,200 | kg | Product |
| CH₄ — methane (flooded field) | 28.0 | kg | Emission/Air |
| N₂O — direct field | 0.82 | kg | Emission/Air |
| CO₂ (diesel combustion) | 57.5 | kg | Emission/Air |

### GWP100 result

| Emission | kg | CF (AR6) | kg CO₂-eq |
|----------|----|----------|-----------|
| CH₄ biogenic | 28.0 | 27.9 | 781.2 |
| N₂O direct | 0.82 | 273.0 | 223.9 |
| N₂O indirect | 0.18 | 273.0 | 49.1 |
| CO₂ diesel | 57.5 | 1.0 | 57.5 |
| **TOTAL** | | | **1,111.7 kg CO₂-eq/t** |

Literature range: 830–1,340 kg CO₂-eq/tonne paddy. ✓

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Retrieval | Keyword overlap | Zero-dependency; swap to FAISS for production |
| LLM prompt | Chain-of-thought + strict JSON schema | Reduces hallucination; easy to parse |
| Expert gate | Review after validation, before export | ISO 14044 §4.3.3 requires human data review |
| Export formats | JSON + CSV + ILCD XML | ILCD required for Thai National LCI DB ingestion |
| Validation | Range-based against literature | Catches 10× errors before they propagate |
| LCIA | GWP100 IPCC AR6 only | Highest priority; extend to ReCiPe 2016 next |

---

## File Relationship to TOR Deliverables

| TOR Deliverable | Implemented in |
|-----------------|---------------|
| D1 — Industry selection (agriculture/rice) | `pipeline/corpus.py` (DEMO_CORPUS), `config.py` defaults |
| D2 — LCI status + AI tech review | `pipeline/extraction.py` (RAG + LLM), `pipeline/retrieval.py` |
| D3 — Sample LCI database | `data/output/*.json / *.csv / *_ILCD.xml` |
| D4 — Feasibility analysis | `pipeline/validation.py` + `pipeline/lcia.py` + expert review in `app.py` |

---

## Extending the Prototype

### Upgrade to FAISS vector retrieval
```python
# pipeline/retrieval.py
import faiss
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("all-MiniLM-L6-v2")
# index = faiss.IndexFlatL2(384)
```

### Add more LCIA categories
```python
# pipeline/lcia.py
_CF_EUTROPHICATION = {"no3": 0.1, "nh3": 0.35, "p": 3.06}
```

### Connect to Thai National LCI Database API
```python
# export/to_tiis.py — POST to the TIIS REST API endpoint
```

### Add user authentication (multi-expert)
```python
# app.py — add Flask-Login for named expert sessions
# Each correction logged with expert name + timestamp
```

---

## References

- Samson et al. (2020) — Thai paddy rice LCA, *J. Cleaner Production*
- Phungrassami et al. (2015) — Thai jasmine rice carbon footprint, *Int. J. LCA*
- OAE (2022) — Thai rice statistics, Office of Agricultural Economics
- IPCC AR6 (2021) — GWP100 characterisation factors
- JRC (2010) — ILCD Handbook, European Commission
- ISO 14040:2006 / ISO 14044:2006 — LCA framework and requirements
- ISO TS-14048:2002 — LCI data documentation format
