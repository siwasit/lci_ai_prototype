"""
config.py — Global settings for lci_ai_prototype
"""
import os

# ── LLM ──────────────────────────────────────────────────────────
LLM_PROVIDER   = os.getenv("LCI_LLM_PROVIDER", "demo")   # demo | anthropic | openai
ANTHROPIC_MODEL = "claude-sonnet-4-6"
OPENAI_MODEL    = "gpt-4o"

# ── RAG ──────────────────────────────────────────────────────────
CHUNK_SIZE    = 400   # words per chunk
CHUNK_OVERLAP = 50    # overlapping words between chunks
TOP_K         = 5     # chunks returned per query

# ── ILCD / eILCD-SDK ─────────────────────────────────────────────
# Path to the eILCD-SDK folder (sibling of this project)
EILCD_SDK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "eILCD-SDK_v2.1.1", "ILCD"
)

# ── Paths ─────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(__file__)
DATA_INPUT  = os.path.join(BASE_DIR, "data", "input")
DATA_OUTPUT = os.path.join(BASE_DIR, "data", "output")

# ── Process defaults ─────────────────────────────────────────────
DEFAULT_PROCESS_NAME = "Paddy rice cultivation, conventional, irrigated, Thailand"
DEFAULT_FU           = "1 tonne paddy rice at farm gate, 14% moisture content"
DEFAULT_SYSTEM_BOUNDARY = (
    "Cradle to farm gate — land preparation, seeding, fertiliser, "
    "irrigation, crop growth (field emissions), harvesting, on-farm drying"
)
DEFAULT_GEOGRAPHY    = "Thailand (national average)"
DEFAULT_REF_YEAR     = "2020-2023"
