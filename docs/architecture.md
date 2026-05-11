# Architecture

## v0.1 — RAG-first foundation

The system is a four-stage pipeline that takes a structured break notification and produces a structured remediation suggestion.

### High-level flow

```mermaid
flowchart LR
    A[Break Notification] --> B[Hybrid Retrieval]
    B --> C[Cross-Encoder Rerank]
    C --> D[LLM Synthesis]
    D --> E[Structured Remediation]

    subgraph Hybrid["Hybrid Retrieval"]
        F[Dense: Qdrant + BGE] --> G[RRF Fusion]
        H[Sparse: BM25] --> G
    end

    B -.-> Hybrid
```

### Component responsibilities

| Component | Module | Job |
|---|---|---|
| Synthetic generator | `sba.synthetic.generator` | Produce realistic historical breaks for indexing and eval |
| Indexer | `sba.retrieval.indexer` | Embed corpus, write to Qdrant, build BM25 index |
| Dense retriever | `sba.retrieval.dense` | Cosine-sim retrieval over BGE embeddings via Qdrant |
| Sparse retriever | `sba.retrieval.sparse` | BM25 retrieval over tokenised structured + free-text fields |
| Hybrid retriever | `sba.retrieval.hybrid` | Combine dense + sparse via Reciprocal Rank Fusion |
| Reranker | `sba.retrieval.rerank` | Cross-encoder rerank to top-K |
| Synthesiser | `sba.synthesis.synthesizer` | Gemini structured-output call to draft remediation |
| Eval suite | `evals/` | Three-layer eval: deterministic, retrieval, synthesis |
| CLI | `sba.cli` | End-to-end entry points |

### Data flow

```mermaid
sequenceDiagram
    participant U as User (CLI)
    participant R as HybridRetriever
    participant Q as Qdrant
    participant B as BM25
    participant K as Reranker
    participant S as Synthesizer
    participant G as Gemini API

    U->>R: search(query)
    R->>Q: dense search (top-20)
    R->>B: sparse search (top-20)
    R->>R: RRF fusion
    R-->>U: top-20 candidates
    U->>K: rerank(query, candidates)
    K-->>U: top-5 reranked
    U->>S: synthesize(notification, top-5)
    S->>G: prompt + response_schema
    G-->>S: structured RemediationSuggestion
    S->>S: validate citations against retrieved IDs
    S-->>U: validated RemediationSuggestion
```

## v0.2 (planned) — MCP server layer

```mermaid
flowchart TD
    A[Investigation Logic] --> B[MCP Client]
    B --> C[settlement-data-mcp Server]
    C --> D[SQLite: trades, SSIs, holidays]
    C --> E[Qdrant: historical breaks]

    A -.->|tool call| B
```

The retrieval logic from v0.1 stays unchanged — it just gets exposed as an MCP tool (`search_historical_breaks`) alongside structured data tools (`get_trade_detail`, `get_counterparty_ssi`, etc.).

## v0.3 (planned) — LangGraph agent

```mermaid
stateDiagram-v2
    [*] --> Triage
    Triage --> Investigate: severity classified
    Investigate --> RootCause: context gathered
    RootCause --> SimilarBreakLookup: category identified
    SimilarBreakLookup --> RemediationDrafting: historical context retrieved
    RemediationDrafting --> HITLGate: draft ready
    HITLGate --> Action: approved
    HITLGate --> RemediationDrafting: revision requested
    HITLGate --> [*]: rejected
    Action --> [*]: complete
```
