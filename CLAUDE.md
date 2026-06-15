# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
# Web UI (recommended — starts Flask on port 5000)
python app.py

# CLI — demo mode (no API key, uses hard-coded Thai rice data)
python main.py --mode demo

# CLI — real LLM extraction
python main.py --mode extract --pdf data/input/paper.pdf --api anthropic
python main.py --mode extract --pdf data/input/paper.pdf --api openai

# CLI — validate demo data only (skips LLM call)
python main.py --mode validate
```

Set API keys before using a live provider:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
```

All settings (model names, chunk size, top-k, paths, default process) live in `config.py`. The `LCI_LLM_PROVIDER` env var overrides `config.LLM_PROVIDER`.

## Architecture

The system has two entry points that share the same pipeline logic:

- **`main.py`** — CLI, calls `run_pipeline()` which prints/exports directly
- **`app.py`** — Flask web UI, calls `run_pipeline_api()` (same logic but returns a dict; suppresses print output so the UI renders its own view). Session state is stored in the module-level `_store` dict keyed by UUID, with the UUID kept in the Flask session cookie.

### Pipeline stages (sequential)

```
corpus.py      → index_corpus()        chunk documents (400-word chunks, 50-word overlap)
retrieval.py   → retrieve()            keyword overlap scoring, returns top-K chunks
extraction.py  → build_prompt()        fills chain-of-thought prompt template
               → extract()             dispatches to demo/_call_anthropic/_call_openai
               → build_lci_from_extraction()  parses flat "flows" list or legacy inputs/outputs
models.py      → LCIDataset / LCIFlow  typed containers for the inventory data
validation.py  → validate_dataset()    range-checks flows against _RANGES dict; returns PASS/FLAG/NO_RANGE
lcia.py        → calculate_gwp100()    multiplies emission flows by _CF_GWP100 factors (IPCC AR6)
export/        → to_json / to_csv / to_ilcd   write files to data/output/
```

### Core data model

`LCIFlow` (dataclass) — one exchange: name, amount, unit, category, source, confidence, provenance, direction.

`LCIDataset` — holds `inputs: list[LCIFlow]` and `outputs: list[LCIFlow]` plus ISO 14048 metadata fields. Serialises to/from plain dict via `to_dict()` / `from_dict()` (used for Flask session storage). `remove_flow()` and `correct_flow_amount()` are the mutation methods called by the `/approve` route.

### Expert review flow (web UI only)

`/run` (POST) → runs pipeline → stores result in `_store` → redirects to `/review`.
`/review` (GET) → renders flagged flows for Keep / Correct / Remove decisions.
`/approve` (POST) → applies corrections (removes first in reverse-index order to avoid index shift, then corrects surviving flows), re-runs validation + GWP, exports all three formats, stores filenames in `_store`.
`/results` (GET) → shows final GWP and download links served by `/download/<filename>`.

### LLM extraction contract

`extract()` must return a dict with either:
- `{"flows": [...], "notes": "..."}` — current flat schema
- `{"inputs": [...], "outputs": [...], ...}` — legacy schema

`build_lci_from_extraction()` handles both shapes. The demo provider returns the flat schema via `_demo_response()`.

### Adding new LCIA categories

Add characterisation factors to the `_CF_*` dict in `pipeline/lcia.py` and a new `calculate_*` function following the `calculate_gwp100` pattern.

### Upgrading to vector retrieval

`pipeline/retrieval.py` currently uses keyword overlap. The upgrade path (FAISS + sentence-transformers) is noted in comments there — swap `retrieve()` without touching other modules.
