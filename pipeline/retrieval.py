"""
pipeline/retrieval.py
─────────────────────
Retrieve the most relevant document chunks for a query.

Current implementation: keyword overlap (TF-style).
Production upgrade: swap retrieve() for a FAISS / ChromaDB vector
search using sentence-transformer embeddings — the rest of the
pipeline is unchanged.
"""
from __future__ import annotations
import config


def retrieve(query: str, chunks: list[dict]) -> list[dict]:
    """
    Return the top-K chunks most relevant to *query*.

    Keyword-overlap scoring simulates cosine similarity over a bag-of-words
    representation. Replace this function body with an embedding-based search
    (faiss.IndexFlatIP, chromadb.Collection.query, etc.) for production use.
    """
    q_words = set(query.lower().split())
    scored = sorted(
        chunks,
        key=lambda c: len(q_words & set(c["text"].lower().split())),
        reverse=True,
    )
    top = scored[: config.TOP_K]
    doc_ids = {c["doc_id"] for c in top}
    print(f"[Retrieval] Query matched {len(top)} chunks "
          f"from {len(doc_ids)} document(s).")
    return top


def build_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a single context block for the LLM prompt."""
    parts = []
    for c in chunks:
        parts.append(f"SOURCE: {c['doc_title']}\n{c['text'].strip()}")
    return "\n\n---\n\n".join(parts)
