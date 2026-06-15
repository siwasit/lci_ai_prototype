#!/usr/bin/env python3
"""
main.py — CLI entry point for the LCI-AI Prototype
────────────────────────────────────────────────────
Usage:
  python main.py                         # demo mode, all exports
  python main.py --mode demo
  python main.py --mode extract --pdf path/to/paper.pdf
  python main.py --mode extract --pdf path/to/paper.pdf --api anthropic
  python main.py --mode validate         # validate demo LCI only
"""
import argparse, sys, os

# Ensure the package root is on sys.path when run directly
sys.path.insert(0, os.path.dirname(__file__))

import config
from pipeline.corpus      import index_corpus, load_pdf_corpus, DEMO_CORPUS
from pipeline.retrieval   import retrieve, build_context
from pipeline.extraction  import build_prompt, extract, build_lci_from_extraction
from pipeline.validation  import validate_dataset
from pipeline.lcia        import calculate_gwp100, print_gwp100
from export.to_json       import export_json
from export.to_csv        import export_csv
from export.to_ilcd       import export_ilcd


def run_pipeline(
    mode: str = "demo",
    pdf_path: str | None = None,
    provider: str | None = None,
    process_name: str = config.DEFAULT_PROCESS_NAME,
    functional_unit: str = config.DEFAULT_FU,
) -> None:
    print("\n" + "═" * 65)
    print("  LCI-AI Prototype  |  mode:", mode)
    print("═" * 65)

    # ── 1. Build corpus & index ─────────────────────────────────────────
    print("\n[1/6] Indexing corpus …")
    if pdf_path:
        pdf_dir = os.path.dirname(os.path.abspath(pdf_path))
        corpus = load_pdf_corpus(pdf_dir)
        if not corpus:
            print("  WARNING: No PDFs found — falling back to demo corpus.")
            corpus = DEMO_CORPUS
    else:
        corpus = DEMO_CORPUS
    chunks = index_corpus(corpus)
    print(f"  {len(chunks)} chunks indexed from {len(corpus)} document(s)")

    # ── 2. Retrieve context ─────────────────────────────────────────────
    print("\n[2/6] Retrieving relevant chunks …")
    query = f"LCI flows inputs outputs {process_name} {functional_unit}"
    top_chunks = retrieve(query, chunks)
    context = build_context(top_chunks)
    print(f"  {len(top_chunks)} chunk(s) retrieved")

    # ── 3. Build prompt & extract ───────────────────────────────────────
    print("\n[3/6] Calling LLM for extraction …")
    if mode == "validate":
        # Skip LLM; use demo extraction directly
        from pipeline.extraction import _demo_response
        raw = _demo_response()
        extraction = raw
    else:
        prompt = build_prompt(context, process_name, functional_unit)
        extraction = extract(prompt, provider=provider)

    # ── 4. Build LCI dataset ────────────────────────────────────────────
    print("\n[4/6] Building LCI dataset …")
    lci = build_lci_from_extraction(extraction, process_name, functional_unit)
    lci.summary()

    # ── 5. Validate ─────────────────────────────────────────────────────
    print("\n[5/6] Validating flows …")
    validate_dataset(lci)

    # ── 6. LCIA (GWP100) ────────────────────────────────────────────────
    print("\n[6/6] Calculating GWP100 (IPCC AR6) …")
    gwp = calculate_gwp100(lci)
    print_gwp100(gwp)

    # ── Exports ──────────────────────────────────────────────────────────
    print("\n[Export] Writing outputs …")
    os.makedirs(config.DATA_OUTPUT, exist_ok=True)
    json_path  = export_json(lci)
    csv_path   = export_csv(lci)
    ilcd_path  = export_ilcd(lci)

    print("\n" + "─" * 65)
    print("  Done.")
    print(f"  JSON  : {json_path}")
    print(f"  CSV   : {csv_path}")
    print(f"  ILCD  : {ilcd_path}")
    print("─" * 65 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LCI-AI Prototype — extract LCI flows from literature"
    )
    parser.add_argument(
        "--mode", choices=["demo", "extract", "validate"],
        default="demo",
        help="demo: use hard-coded Thai rice data | "
             "extract: run RAG+LLM pipeline | "
             "validate: validate demo LCI only",
    )
    parser.add_argument(
        "--pdf", dest="pdf_path", default=None,
        help="Path to a PDF (or directory of PDFs) to use as corpus",
    )
    parser.add_argument(
        "--api", dest="provider", default=None,
        choices=["demo", "anthropic", "openai"],
        help="LLM provider override (default: from LCI_LLM_PROVIDER env var)",
    )
    parser.add_argument(
        "--process", dest="process_name",
        default=config.DEFAULT_PROCESS_NAME,
        help="Process name for the LCI dataset",
    )
    parser.add_argument(
        "--fu", dest="functional_unit",
        default=config.DEFAULT_FU,
        help="Functional unit string",
    )
    args = parser.parse_args()
    run_pipeline(
        mode=args.mode,
        pdf_path=args.pdf_path,
        provider=args.provider,
        process_name=args.process_name,
        functional_unit=args.functional_unit,
    )


if __name__ == "__main__":
    main()


def run_pipeline_api(
    mode: str = "demo",
    pdf_path: str | None = None,
    provider: str | None = None,
    process_name: str = config.DEFAULT_PROCESS_NAME,
    functional_unit: str = config.DEFAULT_FU,
) -> dict:
    """
    API-style version of run_pipeline: returns a dict instead of printing/exporting.
    Used by the Flask web UI.

    Returns:
        {
          "lci":        LCIDataset,
          "validation": list[dict],   # per-flow validation results
          "gwp":        dict,         # GWP100 breakdown + TOTAL
        }
    """
    import io, contextlib

    # Suppress all print output (UI will render its own view)
    with contextlib.redirect_stdout(io.StringIO()):
        if pdf_path:
            pdf_dir = os.path.dirname(os.path.abspath(pdf_path))
            corpus  = load_pdf_corpus(pdf_dir) or DEMO_CORPUS
        else:
            corpus = DEMO_CORPUS

        chunks     = index_corpus(corpus)
        query      = f"LCI flows inputs outputs {process_name} {functional_unit}"
        top_chunks = retrieve(query, chunks)
        context    = build_context(top_chunks)

        if mode == "validate":
            from pipeline.extraction import _demo_response
            extraction = _demo_response()
        else:
            prompt     = build_prompt(context, process_name, functional_unit)
            extraction = extract(prompt, provider=provider)

        lci        = build_lci_from_extraction(extraction, process_name, functional_unit)
        validation = validate_dataset(lci)
        gwp        = calculate_gwp100(lci)

    return {"lci": lci, "validation": validation, "gwp": gwp}
