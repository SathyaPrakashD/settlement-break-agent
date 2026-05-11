# ADR-002: Embedding model and embedded text

**Status:** Accepted
**Date:** 2026-05-11
**Decision-makers:** Sathya Prakash D

## Context

Two decisions, both consequential:
1. **Which embedding model** to use for dense retrieval over historical breaks
2. **What text to actually embed** — narrative only, resolution only, or both

## Embedding model

### Options

| Option | MTEB rank | Local? | Cost (1M embeddings) | Notes |
|---|---|---|---|---|
| OpenAI `text-embedding-3-large` | Strong | No | ~$130 | Closed model. Data leaves network. |
| OpenAI `text-embedding-3-small` | Good | No | ~$20 | Cheap but quality drop noticeable. |
| Voyage `voyage-3` | Top-tier | No | ~$120 | Excellent quality, niche provider. |
| **BAAI `bge-large-en-v1.5`** | Top-tier on retrieval | Yes | $0 (compute only) | 1024-dim, open weights, MIT license. |
| BAAI `bge-base-en-v1.5` | Solid | Yes | $0 | 768-dim, faster but less accurate. |
| Sentence-Transformers `all-MiniLM-L6-v2` | Mediocre | Yes | $0 | 384-dim, fast, lower ceiling. |

### Decision: `bge-large-en-v1.5`

### Rationale

- **Open weights:** zero per-call cost during the 50+ iterations of re-indexing that v0.1 will see. Closed-API embeddings during development add up fast.
- **MTEB retrieval-leaderboard quality:** competitive with the closed models on the relevant benchmarks.
- **Local control:** I can fine-tune later if I need domain-specific improvements. Closed models close that door.
- **Data privacy story:** for BFSI deployment, "embeddings computed locally, never leave the network" is a material risk reduction.

## What to embed

### Options

| Option | Pros | Cons |
|---|---|---|
| Narrative only | Most literal — "find narratives like this narrative" | Loses the resolution signal entirely |
| Resolution only | Surfaces "fix patterns" | A new break has no resolution yet — asymmetric |
| **Narrative + Resolution** | Captures both how the break presented AND how it was fixed | Risk of resolution text dominating |
| Narrative + structured fields as text | Filterable via embedding | Structured filters belong in payload, not embedding |

### Decision: **Narrative + Resolution concatenated**, with category prefix

```
"Category: ssi_mismatch. Narrative: {analyst_narrative} Resolution: {resolution}"
```

### Rationale

A new break has only a narrative. But the **retrieval target** is a case where the *resolution* was useful. By embedding both, we let dense similarity find historical cases whose narrative AND resolution-pattern jointly resemble the new query. This is asymmetric retrieval (query has only narrative; document has narrative + resolution) and is the right shape for this domain.

The category prefix gives weak category-clustering in the embedding space — a small bias toward same-category retrieval — without forcing it.

## Consequences

- **Positive:** Free indexing during development. Resolution signal is preserved in retrieval. Open path to fine-tuning later.
- **Negative:** First-time model download is ~1.3GB (one-off). Inference needs ~2GB RAM (acceptable on laptops).
- **Re-evaluate:** if precision@5 in the eval suite is below 0.7 after 30 hand-labelled golden cases, revisit the embedding-text strategy before swapping models. Often it's the text choice, not the model.
