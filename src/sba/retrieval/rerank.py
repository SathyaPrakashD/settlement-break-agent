"""Cross-encoder reranker.

After hybrid retrieval gives us the top-20 candidates, the reranker reads each
candidate jointly with the query and produces a relevance score. Cross-encoders
are slow (must encode each query-doc pair separately) but far more accurate
than bi-encoder retrievers — the classic retrieve-then-rerank pattern.

──────────────────────────────────────────────────────────────────────────────
TODO(sathya): implement the rerank() method.

Why I left this as a stub: implementing it yourself is the highest-leverage
30-minute exercise in this whole project. You will:
  1. Load a CrossEncoder (use settings.reranker_model = bge-reranker-base)
  2. Build [(query, doc_text)] pairs for each candidate
  3. Call cross_encoder.predict(pairs) → returns scores
  4. Re-sort candidates by new scores, keep top-K
  5. Return as list[RetrievedCase] with the new scores

Reference implementation hint:
    from sentence_transformers import CrossEncoder
    self.encoder = CrossEncoder(settings.reranker_model)
    scores = self.encoder.predict([(query, doc) for doc in candidate_texts])

What "doc_text" should be: same shape as the embedding text — see
indexer._embedding_text(). Consistency matters.

When you're done:
  - Run `uv run sba investigate --trade-id TRD-XXXX` and compare top-5
    before vs after rerank. The improvement is usually visible.
  - Add a unit test in tests/test_rerank.py
──────────────────────────────────────────────────────────────────────────────
"""
from sba.config import settings
from sba.retrieval.dense import RetrievedCase


class Reranker:
    """Cross-encoder reranker over hybrid retrieval candidates."""

    def __init__(self) -> None:
        # TODO(sathya): load the CrossEncoder model here
        # from sentence_transformers import CrossEncoder
        # self.encoder = CrossEncoder(settings.reranker_model)
        self.encoder = None  # placeholder

    def rerank(
        self,
        query: str,
        candidates: list[RetrievedCase],
        top_k: int | None = None,
    ) -> list[RetrievedCase]:
        """Rerank candidates and return top-K by cross-encoder score.

        Args:
            query: The original query text.
            candidates: Output from HybridRetriever.search().
            top_k: How many to return after reranking. Defaults to
                   settings.rerank_top_k.

        Returns:
            Top-K candidates sorted by cross-encoder relevance score desc.
        """
        top_k = top_k or settings.rerank_top_k

        # TODO(sathya): replace this passthrough with the real implementation
        if self.encoder is None:
            # Stub behaviour: return top-K of candidates unchanged.
            # This lets the pipeline run end-to-end before you implement
            # rerank, so you can see the whole flow first.
            return candidates[:top_k]

        # ─────── Your implementation goes here ───────
        # 1. Build pairs
        # 2. Get scores
        # 3. Sort
        # 4. Return top-K
        raise NotImplementedError("Implement Reranker.rerank — see module docstring")
