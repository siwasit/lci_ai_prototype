"""
pipeline/corpus.py
──────────────────
Document corpus management and chunking for the RAG index.

In production: replace DEMO_CORPUS with PDF/text loaders that read
files from data/input/. The chunk() and index_corpus() functions
work identically regardless of source.
"""
from __future__ import annotations
import config

# ── Built-in demo corpus (Thai rice LCI literature snippets) ─────

DEMO_CORPUS: list[dict] = [
    {
        "id": "samson_2020",
        "title": "Life Cycle Assessment of Thai Hom Mali Rice (Samson et al. 2020, Sustainability 12:6003)",
        "text": """
        Conventional jasmine rice cultivation in Thailand, cradle-to-farm-gate.
        Functional unit: 1 kg paddy rice. Average yield: 3,000 kg paddy/ha.
        Rice straw co-product: 3,600 kg/ha (ratio 1.2 kg straw per kg paddy).
        Inputs per hectare: seed 25 kg/ha; nitrogen fertiliser as urea 196 kg urea/ha
        (90 kg N/ha); P2O5 45 kg/ha; K2O 45 kg/ha; herbicide 1.44 kg a.i./ha;
        insecticide 0.36 kg a.i./ha; diesel 65 L/ha; electricity irrigation 55.5 kWh/ha.
        Field CH4: IPCC Tier 1, EF=1.3 g/m2/day × 130 days = 84 kg CH4/ha
        (28 kg CH4 per tonne paddy). N2O direct: 1% of N applied = 2.46 kg N2O/ha
        (0.82 kg N2O/tonne paddy). GWP100: 1.06 kg CO2-eq per kg paddy.
        Field emissions account for ~83% of total GHG impacts.
        """,
    },
    {
        "id": "phungrassami_2015",
        "title": "Life Cycle Assessment of Milled Rice Production (Phungrassami et al. 2015)",
        "text": """
        Cradle-to-mill-gate LCA of milled rice in Thailand. Functional unit: 1 tonne milled rice.
        Paddy cultivation inputs per tonne paddy: TSP fertiliser (46% P2O5) 32.6 kg/t;
        potassium chloride (60% K2O) 32.6 kg/t; fungicide 0.08 kg a.i./t; irrigation
        water 2,970 m3/t. Emissions per tonne paddy: PO4 runoff 0.22 kg/t;
        NH3 volatilisation from urea 4.5 kg/t (5% of N applied); pesticide residual
        to soil 0.42 kg/t (62% of a.i. applied).
        Rice milling per tonne milled rice: electricity 85 kWh; water 0.8 m3.
        Milling recovery: 65% (680 kg milled rice + 80 kg bran + 200 kg husk + 40 kg broken).
        """,
    },
    {
        "id": "oae_2022",
        "title": "Agricultural Statistics of Thailand 2022 (Office of Agricultural Economics)",
        "text": """
        National average paddy yield: 3,000 kg/ha (wet season, conventional irrigated).
        Seed rate: 25 kg/ha transplanting = 8.3 kg seed per tonne paddy.
        Straw-to-paddy ratio: 1.2 kg straw per kg paddy.
        Total paddy area: 10.2 million ha; total production: 30.5 million t/year.
        Diesel: tractor tillage 35-45 L/ha + combine 20-25 L/ha = ~65 L/ha total.
        Electricity irrigation pumping: 55-62 kWh/ha/season.
        N fertiliser recommendation: 70-120 kg N/ha; actual farmer use ~90 kg N/ha.
        Land occupied: 0.33 ha per tonne paddy (inverse of yield).
        """,
    },
    {
        "id": "ipcc_ar6",
        "title": "IPCC AR6 Chapter 7 — Agriculture, Forestry and Other Land Use (2022)",
        "text": """
        Paddy CH4 emission factor: EF_c = 1.3 g CH4/m2/day (continuous flooding).
        Growing period Thai wet-season rice: ~130 days.
        N2O direct: EF1 = 0.01 kg N2O-N per kg N applied (1% default).
        N2O indirect (leaching): EF5 = 0.0075 kg N2O-N per kg NO3-N leached;
        FracLEACH = 0.24 kg NO3-N per kg N applied.
        GWP100 (AR6, 100-year): CH4 biogenic = 27.9; N2O = 273; CO2 = 1.0.
        NOx from diesel combustion: 0.0074 kg NOx per litre diesel.
        CO2 from diesel combustion: 2.65 kg CO2 per litre diesel (petroleum diesel).
        """,
    },
]


# ── Chunking ──────────────────────────────────────────────────────

def chunk_document(doc: dict) -> list[dict]:
    """Split a document into overlapping word-based chunks."""
    words = doc["text"].split()
    size, overlap = config.CHUNK_SIZE, config.CHUNK_OVERLAP
    chunks, i = [], 0
    while i < len(words):
        text = " ".join(words[i: i + size])
        chunks.append({
            "doc_id":    doc["id"],
            "doc_title": doc["title"],
            "text":      text,
            "chunk_idx": len(chunks),
        })
        i += size - overlap
    return chunks


def index_corpus(corpus: list[dict] | None = None) -> list[dict]:
    """
    Index all documents into chunks.
    Pass None to use the built-in DEMO_CORPUS.
    In production, load PDFs from data/input/ and pass them here.
    """
    corpus = corpus or DEMO_CORPUS
    chunks = []
    for doc in corpus:
        chunks.extend(chunk_document(doc))
    print(f"[Corpus] {len(corpus)} docs → {len(chunks)} chunks indexed.")
    return chunks


def load_pdf_corpus(pdf_dir: str) -> list[dict]:
    """
    Load all PDFs from a directory as additional corpus documents.
    Requires pdfplumber: pip install pdfplumber
    """
    import os
    try:
        import pdfplumber
    except ImportError:
        print("[Warning] pdfplumber not installed — skipping PDF corpus. "
              "Run: pip install pdfplumber")
        return []

    docs = []
    for fname in os.listdir(pdf_dir):
        if not fname.lower().endswith(".pdf"):
            continue
        path = os.path.join(pdf_dir, fname)
        try:
            with pdfplumber.open(path) as pdf:
                text = "\n".join(p.extract_text() or "" for p in pdf.pages)
            docs.append({"id": fname, "title": fname, "text": text})
            print(f"[Corpus] Loaded: {fname} ({len(text)} chars)")
        except Exception as e:
            print(f"[Corpus] Failed to load {fname}: {e}")
    return docs
