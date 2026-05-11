"""Hybrid retrieval via Reciprocal Rank Fusion (RRF).

RRF fuses results from multiple retrievers using rank position, not score —
which is robust to heterogeneous score distributions (cosine sim vs BM25).

Formula:
    rrf_score(doc) = sum over retrievers of  1 / (k + rank_in_retriever(doc))

The k constant (default 60, original paper) controls how aggressively to
penalise documents ranked low in any single retriever.

Reference: Cormack, Clarke, Buettcher. "Reciprocal Rank Fusion outperforms
Condorcet and individual rank learning methods." SIGIR 2009.
"""
from collections import defaultdict

from sba.config import settings
from sba.retrieval.dense import DenseRetriever, RetrievedCase
from sba.retrieval.sparse import SparseRetriever


class HybridRetriever:
    """Combine dense + sparse retrieval via RRF."""

    def __init__(self) -> None:
        self.dense = DenseRetriever()
        self.sparse = SparseRetriever()

    def search(self, query: str, top_k: int | None = None) -> list[RetrievedCase]:
        top_k = top_k or settings.retrieval_top_k
        dense_results = self.dense.search(query, top_k=top_k)
        sparse_results = self.sparse.search(query, top_k=top_k)

        return self._rrf_fuse(dense_results, sparse_results, k=settings.rrf_k)[:top_k]

    @staticmethod
    def _rrf_fuse(
        dense_results: list[RetrievedCase],
        sparse_results: list[RetrievedCase],
        k: int,
    ) -> list[RetrievedCase]:
        """Apply RRF fusion. Returns merged list sorted by RRF score desc."""
        rrf_scores: dict[str, float] = defaultdict(float)
        payloads: dict[str, dict] = {}

        for rank, hit in enumerate(dense_results, start=1):
            rrf_scores[hit.case_id] += 1.0 / (k + rank)
            payloads[hit.case_id] = hit.payload

        for rank, hit in enumerate(sparse_results, start=1):
            rrf_scores[hit.case_id] += 1.0 / (k + rank)
            # Don't overwrite; dense payload is fine
            if hit.case_id not in payloads:
                payloads[hit.case_id] = hit.payload

        sorted_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)

        return [
            RetrievedCase(case_id=cid, score=rrf_scores[cid], payload=payloads[cid])
            for cid in sorted_ids
        ]
