# ADR-003: Hybrid fusion — Reciprocal Rank Fusion (RRF)

**Status:** Accepted
**Date:** 2026-05-11
**Decision-makers:** Sathya Prakash D

## Context

We retrieve from two heterogeneous sources:
- **Dense:** cosine similarity, scores in [0, 1]
- **Sparse (BM25):** unbounded positive scores, no upper bound

We need to combine these into a single ranked list. The scoring distributions are fundamentally incompatible, so we cannot just add or average raw scores.

## Options

### Score-based fusion (rejected)
- **Linear combination:** `alpha * dense_score + (1-alpha) * sparse_score`. Requires score normalisation, which is fragile across corpora.
- **Convex combination after rescaling:** more robust than raw scores but still requires hyperparameter tuning per dataset.

### Rank-based fusion (chosen)
- **Reciprocal Rank Fusion:** position-only, single hyperparameter `k` (default 60), well-studied.
- **Borda count:** simpler than RRF but rewards mediocre rankings more aggressively.

### Learned fusion (rejected for v0.1)
- **Learning-to-rank (LambdaMART, etc.):** state of art but requires labelled training pairs we don't yet have.

## Decision

**RRF with k=60** (the original paper's recommendation).

```
rrf_score(doc) = sum over retrievers of  1 / (k + rank_in_retriever(doc))
```

## Rationale

- **Score-distribution agnostic.** Works regardless of whether dense scores are cosine, dot product, L2, etc. Robust to retriever swaps.
- **Single hyperparameter.** `k` has well-understood behaviour — larger k means more aggressive top-rank weighting.
- **Empirically strong.** The original RRF paper (Cormack et al., SIGIR 2009) showed it outperformed both Condorcet methods and individual rank-learning.
- **Cheap to compute.** Pure rank arithmetic.

## Consequences

- **Positive:** Adding a third retriever later (e.g. Splade in v0.4+) is trivial — just another rank list into the same formula.
- **Negative:** We don't capture absolute score confidence. A doc with cosine 0.99 in dense and rank-1 in sparse is treated identically to a doc with cosine 0.51 and rank-1.
- **Mitigation:** the reranker (cross-encoder) downstream gives us the absolute relevance signal RRF dropped.

## Reference

Cormack, Clarke, Buettcher. *Reciprocal Rank Fusion outperforms Condorcet and individual rank learning methods.* SIGIR 2009.
