"""Configuration loaded from environment variables.

Single source of truth for all tunable parameters. Anything that varies between
dev/test/prod or that you might want to A/B test goes here, not as a magic constant
elsewhere in the code.
"""
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ──────────────── LLM ────────────────
    gemini_api_key: str = Field(..., description="Google Gemini API key")
    synthesis_model: str = Field(default="gemini-2.0-flash-exp")
    judge_model: str = Field(default="gemini-2.5-pro")

    # ──────────────── Qdrant ────────────────
    qdrant_host: str = Field(default="localhost")
    qdrant_port: int = Field(default=6333)
    qdrant_collection: str = Field(default="settlement_breaks")

    # ──────────────── Models ────────────────
    embedding_model: str = Field(default="BAAI/bge-large-en-v1.5")
    embedding_dim: int = Field(default=1024)  # bge-large-en-v1.5 is 1024-dim
    reranker_model: str = Field(default="BAAI/bge-reranker-base")

    # ──────────────── Retrieval params ────────────────
    retrieval_top_k: int = Field(default=20, description="Candidates before rerank")
    rerank_top_k: int = Field(default=5, description="Final results after rerank")
    rrf_k: int = Field(default=60, description="RRF fusion constant")

    # ──────────────── Paths ────────────────
    project_root: Path = Field(default=Path(__file__).parent.parent.parent)

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def corpus_path(self) -> Path:
        return self.data_dir / "breaks_corpus.jsonl"

    @property
    def golden_set_path(self) -> Path:
        return self.data_dir / "golden_set.jsonl"


# Module-level singleton — import this, not the class
settings = Settings()  # type: ignore[call-arg]
