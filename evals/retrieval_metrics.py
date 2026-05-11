"""Layer 2: retrieval metrics.

Standard IR metrics computed against the golden set.

Golden set format (JSONL, one per line):
  {
    "query_break_id": "CASE-000123",
    "expected_match_id": "CASE-000456",
    "notes": "Why this is the right match (for review)"
  }

The query_break_id is one we synthesised; the expected_match_id is the case
in the corpus that an analyst would consider 'the closest precedent'. For v0.1
we author this manually — labelling ~30 is one evening of work.
"""
import json
from pathlib import Path

from sba.config import settings
from sba.retrieval.dense import RetrievedCase


def precision_at_k(retrieved: list[RetrievedCase], expected_id: str, k: int) -> float:
    """1.0 if expected_id is in top-K, else 0.0. (Single expected match → binary.)"""
    top_k_ids = {r.case_id for r in retrieved[:k]}
    return 1.0 if expected_id in top_k_ids else 0.0


def mrr(retrieved: list[RetrievedCase], expected_id: str) -> float:
    """Mean Reciprocal Rank — 1/rank of the first correct hit, 0 if not found."""
    for rank, case in enumerate(retrieved, start=1):
        if case.case_id == expected_id:
            return 1.0 / rank
    return 0.0


def hit_rate_at_1(retrieved: list[RetrievedCase], expected_id: str) -> float:
    """1.0 if top result is the expected match."""
    return 1.0 if retrieved and retrieved[0].case_id == expected_id else 0.0


def load_golden_set(path: Path | None = None) -> list[dict]:
    """Load the golden eval set from JSONL."""
    path = path or settings.golden_set_path
    if not path.exists():
        raise FileNotFoundError(
            f"Golden set not found at {path}. See data/golden_set.jsonl.example."
        )

    items = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                items.append(json.loads(line))
    return items


def run_retrieval_eval() -> dict[str, float]:
    """Run retrieval metrics over the golden set.

    Returns a dict of metric → score (averaged across the golden set).
    """
    from sba.retrieval.hybrid import HybridRetriever
    from sba.retrieval.indexer import load_corpus
    from sba.retrieval.rerank import Reranker

    golden = load_golden_set()
    corpus = {b.case_id: b for b in load_corpus(settings.corpus_path)}

    retriever = HybridRetriever()
    reranker = Reranker()

    metrics: dict[str, list[float]] = {
        "precision@5": [],
        "precision@10": [],
        "mrr": [],
        "hit_rate@1": [],
    }

    for item in golden:
        query_id = item["query_break_id"]
        expected_id = item["expected_match_id"]
        query_break = corpus.get(query_id)
        if query_break is None:
            print(f"⚠ query break {query_id} missing from corpus — skipping")
            continue

        candidates = retriever.search(query_break.analyst_narrative, top_k=20)
        top_cases = reranker.rerank(query_break.analyst_narrative, candidates, top_k=10)

        metrics["precision@5"].append(precision_at_k(top_cases, expected_id, k=5))
        metrics["precision@10"].append(precision_at_k(top_cases, expected_id, k=10))
        metrics["mrr"].append(mrr(top_cases, expected_id))
        metrics["hit_rate@1"].append(hit_rate_at_1(top_cases, expected_id))

    return {name: (sum(scores) / len(scores) if scores else 0.0) for name, scores in metrics.items()}
