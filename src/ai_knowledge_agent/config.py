from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    data_dir: Path
    raw_dir: Path
    index_dir: Path
    config_dir: Path
    logs_dir: Path
    chunk_size: int = 900
    chunk_overlap: int = 120
    top_k: int = 5
    embedding_provider: str = "hash"
    embedding_dimensions: int = 256
    embedding_model: str = "text-embedding-3-small"
    embedding_base_url: str = "https://api.openai.com/v1"
    embedding_api_key: str | None = None
    vector_weight: float = 0.65
    generation_provider: str = "local"
    generation_model: str = "gpt-4o-mini"
    generation_base_url: str = "https://api.openai.com/v1"
    generation_api_key: str | None = None
    generation_context_chars: int = 6000

    @classmethod
    def from_env(cls) -> "AppConfig":
        data_dir = Path(os.getenv("AI_KNOWLEDGE_AGENT_DATA_DIR", "./data")).resolve()
        embedding_provider = os.getenv("AI_KNOWLEDGE_AGENT_EMBEDDING_PROVIDER", "hash").strip().lower()
        return cls(
            data_dir=data_dir,
            raw_dir=data_dir / "raw",
            index_dir=data_dir / "index",
            config_dir=data_dir / "config",
            logs_dir=data_dir / "logs",
            chunk_size=int(os.getenv("AI_KNOWLEDGE_AGENT_CHUNK_SIZE", "900")),
            chunk_overlap=int(os.getenv("AI_KNOWLEDGE_AGENT_CHUNK_OVERLAP", "120")),
            top_k=int(os.getenv("AI_KNOWLEDGE_AGENT_TOP_K", "5")),
            embedding_provider=embedding_provider,
            embedding_dimensions=int(os.getenv("AI_KNOWLEDGE_AGENT_EMBEDDING_DIMENSIONS", "256")),
            embedding_model=os.getenv("AI_KNOWLEDGE_AGENT_EMBEDDING_MODEL", "text-embedding-3-small"),
            embedding_base_url=os.getenv(
                "AI_KNOWLEDGE_AGENT_EMBEDDING_BASE_URL", "https://api.openai.com/v1"
            ),
            embedding_api_key=os.getenv("AI_KNOWLEDGE_AGENT_EMBEDDING_API_KEY")
            or os.getenv("OPENAI_API_KEY"),
            vector_weight=float(os.getenv("AI_KNOWLEDGE_AGENT_VECTOR_WEIGHT", "0.65")),
            generation_provider=os.getenv("AI_KNOWLEDGE_AGENT_GENERATION_PROVIDER", "local")
            .strip()
            .lower(),
            generation_model=os.getenv("AI_KNOWLEDGE_AGENT_GENERATION_MODEL", "gpt-4o-mini"),
            generation_base_url=os.getenv(
                "AI_KNOWLEDGE_AGENT_GENERATION_BASE_URL", "https://api.openai.com/v1"
            ),
            generation_api_key=os.getenv("AI_KNOWLEDGE_AGENT_GENERATION_API_KEY")
            or os.getenv("OPENAI_API_KEY"),
            generation_context_chars=int(
                os.getenv("AI_KNOWLEDGE_AGENT_GENERATION_CONTEXT_CHARS", "6000")
            ),
        )

    def ensure_dirs(self) -> None:
        for directory in [
            self.data_dir,
            self.raw_dir,
            self.index_dir,
            self.config_dir,
            self.logs_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)


INDEX_FILE = "knowledge.db"
