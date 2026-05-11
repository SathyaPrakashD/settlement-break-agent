"""Indexing pipeline.

Embeds every historical break with bge-large-en-v1.5 and stores in Qdrant.
Builds an in-memory BM25 index over structured fields for sparse retrieval.

Design note: we embed *narrative + resolution* concatenated, not just narrative.
The resolution carries the most useful signal for "what worked before" — losing
it during retrieval would defeat the purpose. This is a deliberate, defensible
choice; see ADR-002.
"""

import pickle
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from sba.config import settings
from sba.synthetic.schemas import HistoricalBreak


def _embedding_text(brk: HistoricalBreak) -> str:
    """Build the text we actually embed.

    Concatenates narrative + resolution because the resolution is half the
    retrieval signal. Prefixed with category for slight category-clustering.
    """
    return (
        f"Category: {brk.category.value}. "
        f"Narrative: {brk.analyst_narrative} "
        f"Resolution: {brk.resolution}"
    )


def _bm25_tokens(brk: HistoricalBreak) -> list[str]:
    """Build the token set for BM25.

    BM25 is the right tool for *structured field matching*, so we deliberately
    tokenise the codes/codes/IDs alongside the words rather than just running
    raw text tokenisation over everything.
    """
    structured = [
        brk.category.value,
        brk.severity.value,
        brk.product_type.value,
        brk.currency,
        brk.counterparty_id,
        brk.exception_code,
    ]
    narrative_tokens = brk.analyst_narrative.lower().split()
    resolution_tokens = brk.resolution.lower().split()
    return structured + narrative_tokens + resolution_tokens


def load_corpus(corpus_path: Path) -> list[HistoricalBreak]:
    """Load the JSONL corpus into memory."""
    breaks = []
    with corpus_path.open("r", encoding="utf-8") as f:
        for line in f:
            breaks.append(HistoricalBreak.model_validate_json(line))
    return breaks


def index_corpus(corpus_path: Path | None = None) -> None:
    """End-to-end indexing: embed → Qdrant + build BM25 → pickle.

    Idempotent: drops and recreates the collection on each run. Acceptable for
    a 500-doc corpus; for larger corpora we'd switch to incremental upserts.
    """
    corpus_path = corpus_path or settings.corpus_path
    if not corpus_path.exists():
        raise FileNotFoundError(
            f"Corpus not found at {corpus_path}. Run `sba generate-corpus` first."
        )

    print(f"Loading corpus from {corpus_path}")
    breaks = load_corpus(corpus_path)
    print(f"Loaded {len(breaks)} breaks.")

    # ─────── Dense indexing ───────
    print(f"\nLoading embedding model: {settings.embedding_model}")
    model = SentenceTransformer(settings.embedding_model)

    print("Embedding corpus...")
    texts = [_embedding_text(b) for b in breaks]
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)

    print(f"\nConnecting to Qdrant at {settings.qdrant_host}:{settings.qdrant_port}")
    client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

    if client.collection_exists(settings.qdrant_collection):
        client.delete_collection(settings.qdrant_collection)
    client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config=VectorParams(size=settings.embedding_dim, distance=Distance.COSINE),
    )

    print(f"Uploading {len(breaks)} points to Qdrant...")
    points = [
        PointStruct(
            id=i,
            vector=embeddings[i].tolist(),
            payload=breaks[i].model_dump(mode="json"),
        )
        for i in range(len(breaks))
    ]
    client.upsert(collection_name=settings.qdrant_collection, points=points)

    # ─────── Sparse indexing ───────
    print("\nBuilding BM25 index...")
    bm25_tokens = [_bm25_tokens(b) for b in breaks]
    bm25 = BM25Okapi(bm25_tokens)

    bm25_path = settings.data_dir / "bm25_index.pkl"
    with bm25_path.open("wb") as f:
        pickle.dump({"bm25": bm25, "case_ids": [b.case_id for b in breaks]}, f)

    print(f"BM25 index written to {bm25_path}")
    print(f"\n✓ Indexed {len(breaks)} breaks. Dense → Qdrant. Sparse → {bm25_path.name}.")
