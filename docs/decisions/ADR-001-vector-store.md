# ADR-001: Vector store — Qdrant

**Status:** Accepted
**Date:** 2026-05-11
**Decision-makers:** Sathya Prakash D

## Context

We need a vector store for embeddings of ~500 (v0.1) growing to ~10K+ (v0.3+) historical breaks. Requirements:
- Hybrid search support (dense + sparse) or clean integration with a separate sparse store
- Runs locally for development without cloud spend
- Managed cloud option exists for production deployment
- Mature Python SDK
- Filter-by-payload for metadata-aware retrieval (currency, counterparty, severity)

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **Qdrant** | Best-in-class hybrid search built in (since v1.10). Rust core → fast. Self-hostable AND managed cloud. Excellent payload filtering. Active development. | Smaller community than Pinecone. Newer than alternatives. |
| **Pinecone** | Largest community, mature managed cloud, broad enterprise adoption. | Closed source, no local dev mode (forces cloud spend during development). Hybrid search bolted on. |
| **Weaviate** | Strong hybrid search, GraphQL API, good documentation. | Heavier operationally. Schema upfront. |
| **ChromaDB** | Simplest local dev. Pythonic. | Hybrid search is bolt-on. Less production-mature. Tier-1 banks won't deploy it. |
| **pgvector** | Banks love Postgres. RLS gives natural tenant isolation. SQL-native. | Sparse retrieval needs separate engine. Hybrid search requires custom orchestration. |

## Decision

**Qdrant**, self-hosted via Docker for v0.1.

## Rationale

For v0.1 the critical constraints are: (a) runs on a laptop free, (b) hybrid search clean, (c) production path exists. Qdrant satisfies all three. ChromaDB is too thin for production credibility. pgvector is excellent for v1.0 in a BFSI deployment but adds ops complexity I don't need yet — and I want to migrate TO pgvector with a real reason, not start there by default.

## Consequences

- **Positive:** Zero cloud spend during development. Single `docker compose up` to local-dev environment. Clear migration path: same SDK, swap host config to point at Qdrant Cloud.
- **Negative:** If a hiring manager interview demands "why not Pinecone for production," I need to defend that explicitly — see this ADR.
- **Future:** In v0.5 (BFSI deployment hypothetical), re-evaluate pgvector for the tenant-isolation story. Document that re-evaluation as ADR-007 when it happens.
