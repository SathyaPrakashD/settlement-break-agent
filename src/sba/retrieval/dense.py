"""Dense retrieval against Qdrant."""
from dataclasses import dataclass

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from sba.config import settings


@dataclass(frozen=True)
class RetrievedCase:
    """A retrieved case from any retriever (dense, sparse, or fused).

    `score` interpretation is retriever-dependent — for cosine similarity it's
    [0, 1]; for BM25 it's unbounded positive; for RRF it's [0, ~0.03].
    Comparing scores across retrievers is meaningless; rank-based fusion is
    the only correct way to combine them. (See ADR-003.)
    """

    case_id: str
    score: float
    payload: dict


class DenseRetriever:
    """Vector retrieval over the Qdrant collection.

    Held as a class so the embedding model is loaded once per process.
    Embedding takes seconds; doing it per query would dominate latency.
    """

    def __init__(self) -> None:
        self.client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        self.model = SentenceTransformer(settings.embedding_model)

    def search(self, query: str, top_k: int | None = None) -> list[RetrievedCase]:
        top_k = top_k or settings.retrieval_top_k
        query_vector = self.model.encode(query).tolist()

        results = self.client.search(
            collection_name=settings.qdrant_collection,
            query_vector=query_vector,
            limit=top_k,
        )

        return [
            RetrievedCase(
                case_id=str(hit.payload["case_id"]) if hit.payload else "",
                score=hit.score,
                payload=hit.payload or {},
            )
            for hit in results
        ]
