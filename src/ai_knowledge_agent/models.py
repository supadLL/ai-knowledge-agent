from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Document:
    id: str
    path: str
    filename: str
    type: str


@dataclass(frozen=True)
class Chunk:
    id: str
    document_id: str
    filename: str
    path: str
    index: int
    content: str
    tokens: list[str] = field(default_factory=list)
    embedding: list[float] = field(default_factory=list)


@dataclass(frozen=True)
class RetrievalResult:
    chunk: Chunk
    score: float


@dataclass(frozen=True)
class DocumentSummary:
    id: str
    filename: str
    path: str
    type: str
    chunk_count: int
