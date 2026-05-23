from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .config import INDEX_FILE
from .embeddings import EmbeddingProvider
from .models import Chunk, DocumentSummary


def index_path(index_dir: Path) -> Path:
    return index_dir / INDEX_FILE


def save_chunks(
    index_dir: Path, chunks: list[Chunk], embedding_provider: EmbeddingProvider | None = None
) -> Path:
    index_dir.mkdir(parents=True, exist_ok=True)
    path = index_path(index_dir)
    with sqlite3.connect(path) as connection:
        initialize_schema(connection)
        connection.execute("DELETE FROM chunks")
        connection.execute("DELETE FROM documents")
        for chunk in chunks:
            embedding = (
                embedding_provider.embed(chunk.content)
                if embedding_provider is not None
                else chunk.embedding
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO documents (id, filename, path, type)
                VALUES (?, ?, ?, ?)
                """,
                (chunk.document_id, chunk.filename, chunk.path, Path(chunk.path).suffix.lstrip(".")),
            )
            connection.execute(
                """
                INSERT INTO chunks (
                    id, document_id, filename, path, chunk_index, content, tokens, embedding
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk.id,
                    chunk.document_id,
                    chunk.filename,
                    chunk.path,
                    chunk.index,
                    chunk.content,
                    json.dumps(chunk.tokens, ensure_ascii=False),
                    json.dumps(embedding),
                ),
            )
    return path


def upsert_document_chunks(
    index_dir: Path,
    chunks: list[Chunk],
    embedding_provider: EmbeddingProvider | None = None,
) -> Path:
    index_dir.mkdir(parents=True, exist_ok=True)
    path = index_path(index_dir)
    document_paths = sorted({chunk.path for chunk in chunks})
    with sqlite3.connect(path) as connection:
        initialize_schema(connection)
        for document_path in document_paths:
            connection.execute("DELETE FROM documents WHERE path = ?", (document_path,))
        for chunk in chunks:
            embedding = (
                embedding_provider.embed(chunk.content)
                if embedding_provider is not None
                else chunk.embedding
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO documents (id, filename, path, type)
                VALUES (?, ?, ?, ?)
                """,
                (chunk.document_id, chunk.filename, chunk.path, Path(chunk.path).suffix.lstrip(".")),
            )
            connection.execute(
                """
                INSERT INTO chunks (
                    id, document_id, filename, path, chunk_index, content, tokens, embedding
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk.id,
                    chunk.document_id,
                    chunk.filename,
                    chunk.path,
                    chunk.index,
                    chunk.content,
                    json.dumps(chunk.tokens, ensure_ascii=False),
                    json.dumps(embedding),
                ),
            )
    return path


def delete_document(index_dir: Path, document_id: str) -> bool:
    path = index_path(index_dir)
    if not path.exists():
        return False
    with sqlite3.connect(path) as connection:
        initialize_schema(connection)
        cursor = connection.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        return cursor.rowcount > 0


def load_index(index_dir: Path) -> list[Chunk]:
    path = index_path(index_dir)
    if not path.exists():
        return []

    chunks: list[Chunk] = []
    with sqlite3.connect(path) as connection:
        initialize_schema(connection)
        rows = connection.execute(
            """
            SELECT id, document_id, filename, path, chunk_index, content, tokens, embedding
            FROM chunks
            ORDER BY filename, chunk_index
            """
        )
        for row in rows:
            chunks.append(
                Chunk(
                    id=row[0],
                    document_id=row[1],
                    filename=row[2],
                    path=row[3],
                    index=row[4],
                    content=row[5],
                    tokens=json.loads(row[6]),
                    embedding=json.loads(row[7]),
                )
            )
    return chunks


def load_document_summaries(index_dir: Path) -> list[DocumentSummary]:
    path = index_path(index_dir)
    if not path.exists():
        return []

    summaries: list[DocumentSummary] = []
    with sqlite3.connect(path) as connection:
        initialize_schema(connection)
        rows = connection.execute(
            """
            SELECT documents.id, documents.filename, documents.path, documents.type, COUNT(chunks.id)
            FROM documents
            LEFT JOIN chunks ON chunks.document_id = documents.id
            GROUP BY documents.id, documents.filename, documents.path, documents.type
            ORDER BY documents.filename
            """
        )
        for row in rows:
            summaries.append(
                DocumentSummary(
                    id=row[0],
                    filename=row[1],
                    path=row[2],
                    type=row[3],
                    chunk_count=row[4],
                )
            )
    return summaries


def index_updated_at(index_dir: Path) -> int | None:
    path = index_path(index_dir)
    if not path.exists():
        return None
    return path.stat().st_mtime_ns


def initialize_schema(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            path TEXT NOT NULL,
            type TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            filename TEXT NOT NULL,
            path TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            tokens TEXT NOT NULL,
            embedding TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_chunks_document_index
        ON chunks(document_id, chunk_index)
        """
    )
