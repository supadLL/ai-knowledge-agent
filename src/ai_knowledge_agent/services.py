from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .config import AppConfig
from .generation import GenerationProvider
from .ingestion import load_chunks
from .llm_access import LlmAccountStore
from .models import Chunk, DocumentSummary, RetrievalResult
from .providers import embedding_provider_from_config, generation_provider_from_config
from .retrieval import retrieve
from .store import (
    delete_document,
    index_path,
    index_updated_at,
    load_document_summaries,
    load_index,
    save_chunks,
    upsert_document_chunks,
)


@dataclass(frozen=True)
class IndexBuildResult:
    source: Path
    index_path: Path
    chunk_count: int
    embedding_provider: str
    embedding_dimensions: int


@dataclass(frozen=True)
class AskResult:
    question: str
    answer: str
    sources: list[RetrievalResult]
    generation_provider: str


@dataclass(frozen=True)
class IndexStats:
    data_dir: str
    raw_dir: str
    index_file: str
    indexed_documents: int
    indexed_chunks: int
    index_updated_at: str | None
    embedding_provider: str
    embedding_dimensions: int
    embedding_model: str | None
    vector_weight: float
    generation_provider: str
    generation_model: str | None
    generation_context_chars: int
    chunk_size: int
    chunk_overlap: int
    top_k: int


class IndexService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.embedding_provider = embedding_provider_from_config(config)

    def rebuild_index(self, source: Path) -> IndexBuildResult:
        chunks = load_chunks(source, self.config.chunk_size, self.config.chunk_overlap)
        path = save_chunks(self.config.index_dir, chunks, self.embedding_provider)
        return IndexBuildResult(
            source=source,
            index_path=path,
            chunk_count=len(chunks),
            embedding_provider=self.embedding_provider.name,
            embedding_dimensions=self.embedding_provider.dimensions,
        )

    def load_chunks(self) -> list[Chunk]:
        return load_index(self.config.index_dir)

    def documents(self) -> list[DocumentSummary]:
        return load_document_summaries(self.config.index_dir)

    def delete_document(self, document_id: str) -> bool:
        return delete_document(self.config.index_dir, document_id)

    def reindex_document(self, document_id: str) -> IndexBuildResult | None:
        summary = next((document for document in self.documents() if document.id == document_id), None)
        if summary is None:
            return None
        source = Path(summary.path)
        if not source.exists():
            raise FileNotFoundError(str(source))
        chunks = load_chunks(source, self.config.chunk_size, self.config.chunk_overlap)
        path = upsert_document_chunks(self.config.index_dir, chunks, self.embedding_provider)
        return IndexBuildResult(
            source=source,
            index_path=path,
            chunk_count=len(chunks),
            embedding_provider=self.embedding_provider.name,
            embedding_dimensions=self.embedding_provider.dimensions,
        )

    def search(self, question: str, top_k: int | None = None) -> list[RetrievalResult]:
        return retrieve(
            question,
            self.load_chunks(),
            top_k or self.config.top_k,
            self.embedding_provider,
            vector_weight=self.config.vector_weight,
        )

    def index_path(self) -> Path:
        return index_path(self.config.index_dir)

    def stats(self) -> IndexStats:
        documents = self.documents()
        chunks = self.load_chunks()
        updated = index_updated_at(self.config.index_dir)
        store = LlmAccountStore(self.config.config_dir)
        llm_account = store.first_enabled_account()
        generation_provider = (
            f"fuel-pool:{store.get_setting('fuel_strategy') or 'first_available'}"
            if llm_account is not None
            else self.config.generation_provider
        )
        generation_model = (
            llm_account.model
            if llm_account is not None
            else self.config.generation_model
            if self.config.generation_provider
            in {"openai", "openai-compatible", "openai-compatible-chat"}
            else None
        )
        return IndexStats(
            data_dir=str(self.config.data_dir),
            raw_dir=str(self.config.raw_dir),
            index_file=str(self.index_path()),
            indexed_documents=len(documents),
            indexed_chunks=len(chunks),
            index_updated_at=format_timestamp_ns(updated),
            embedding_provider=self.embedding_provider.name,
            embedding_dimensions=self.embedding_provider.dimensions,
            embedding_model=self.config.embedding_model
            if self.config.embedding_provider in {"openai", "openai-compatible"}
            else None,
            vector_weight=self.config.vector_weight,
            generation_provider=generation_provider,
            generation_model=generation_model,
            generation_context_chars=self.config.generation_context_chars,
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            top_k=self.config.top_k,
        )


def format_timestamp_ns(timestamp_ns: int | None) -> str | None:
    if timestamp_ns is None:
        return None
    timestamp_seconds = timestamp_ns / 1_000_000_000
    return datetime.fromtimestamp(timestamp_seconds, tz=UTC).isoformat()


class AnswerService:
    def __init__(
        self,
        index_service: IndexService,
        generation_provider: GenerationProvider | None = None,
    ) -> None:
        self.index_service = index_service
        self.generation_provider = generation_provider or generation_provider_from_config(
            index_service.config
        )

    def ask(self, question: str, top_k: int | None = None) -> AskResult:
        sources = self.index_service.search(question, top_k=top_k)
        answer = self.generation_provider.generate(question, sources)
        return AskResult(
            question=question,
            answer=answer,
            sources=sources,
            generation_provider=self.generation_provider.name,
        )
