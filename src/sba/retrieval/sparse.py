"""Sparse retrieval via BM25.

BM25 excels at structured-field matching — exact matches on currency codes,
counterparty IDs, exception codes that dense retrieval can fuzz away. Hybrid
retrieval picks up where each lone retriever fails.
"""
import pickle

from rank_bm25 import BM25Okapi

from sba.config import settings
from sba.retrieval.dense import RetrievedCase
from sba.retrieval.indexer import load_corpus


class SparseRetriever:
    """BM25 over the historical break corpus."""

    def __init__(self) -> None:
        bm25_path = settings.data_dir / "bm25_index.pkl"
        if not bm25_path.exists():
            raise FileNotFoundError(
                f"BM25 index not found at {bm25_path}. Run `sba index` first."
            )

        with bm25_path.open("rb") as f:
            data = pickle.load(f)

        self.bm25: BM25Okapi = data["bm25"]
        self.case_ids: list[str] = data["case_ids"]

        # Load the payloads so we can return them with results.
        # For 500 docs this is fine; for larger corpora we'd lazy-load.
        breaks = load_corpus(settings.corpus_path)
        self.payloads = {b.case_id: b.model_dump(mode="json") for b in breaks}

    def search(self, query: str, top_k: int | None = None) -> list[RetrievedCase]:
        top_k = top_k or settings.retrieval_top_k
        tokens = query.lower().split()
        scores = self.bm25.get_scores(tokens)

        # argsort descending
        top_indices = scores.argsort()[::-1][:top_k]

        return [
            RetrievedCase(
                case_id=self.case_ids[i],
                score=float(scores[i]),
                payload=self.payloads[self.case_ids[i]],
            )
            for i in top_indices
            if scores[i] > 0  # filter zero-score matches
        ]
