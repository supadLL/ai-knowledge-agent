from __future__ import annotations

import sqlite3
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .llm_access import app_db_path


@dataclass(frozen=True)
class DocumentSource:
    id: str
    label: str
    path: str
    created_at: int
    updated_at: int
    last_indexed_at: int | None = None
    last_chunk_count: int = 0


def now_ms() -> int:
    return int(time.time() * 1000)


def public_source(source: DocumentSource) -> dict[str, Any]:
    return asdict(source)


class DocumentSourceStore:
    def __init__(self, config_dir: Path) -> None:
        self.path = app_db_path(config_dir)

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            initialize_schema(connection)

    def list_sources(self) -> list[DocumentSource]:
        self.initialize()
        with sqlite3.connect(self.path) as connection:
            rows = connection.execute(
                """
                SELECT id, label, path, created_at, updated_at, last_indexed_at, last_chunk_count
                FROM document_sources
                ORDER BY updated_at DESC
                """
            )
            return [source_from_row(row) for row in rows]

    def get_source(self, source_id: str) -> DocumentSource | None:
        self.initialize()
        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                """
                SELECT id, label, path, created_at, updated_at, last_indexed_at, last_chunk_count
                FROM document_sources
                WHERE id = ?
                """,
                (source_id,),
            ).fetchone()
        return source_from_row(row) if row else None

    def upsert_source(self, path: Path, label: str | None = None) -> DocumentSource:
        source_path = str(path.resolve())
        source_label = (label or path.name or source_path).strip()
        timestamp = now_ms()
        self.initialize()
        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                """
                SELECT id, label, path, created_at, updated_at, last_indexed_at, last_chunk_count
                FROM document_sources
                WHERE path = ?
                """,
                (source_path,),
            ).fetchone()
            if row:
                source_id = row[0]
                connection.execute(
                    """
                    UPDATE document_sources
                    SET label = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (source_label, timestamp, source_id),
                )
            else:
                source_id = str(uuid.uuid4())
                connection.execute(
                    """
                    INSERT INTO document_sources (
                        id, label, path, created_at, updated_at, last_indexed_at, last_chunk_count
                    )
                    VALUES (?, ?, ?, ?, ?, NULL, 0)
                    """,
                    (source_id, source_label, source_path, timestamp, timestamp),
                )
        source = self.get_source(source_id)
        if source is None:
            raise RuntimeError("Document source was not saved.")
        return source

    def mark_indexed(self, source_id: str, chunk_count: int) -> DocumentSource | None:
        timestamp = now_ms()
        self.initialize()
        with sqlite3.connect(self.path) as connection:
            cursor = connection.execute(
                """
                UPDATE document_sources
                SET last_indexed_at = ?, last_chunk_count = ?, updated_at = ?
                WHERE id = ?
                """,
                (timestamp, max(0, chunk_count), timestamp, source_id),
            )
        return self.get_source(source_id) if cursor.rowcount else None

    def delete_source(self, source_id: str) -> bool:
        self.initialize()
        with sqlite3.connect(self.path) as connection:
            cursor = connection.execute("DELETE FROM document_sources WHERE id = ?", (source_id,))
            return cursor.rowcount > 0


def initialize_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS document_sources (
            id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            path TEXT NOT NULL UNIQUE,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            last_indexed_at INTEGER,
            last_chunk_count INTEGER NOT NULL DEFAULT 0
        )
        """
    )


def source_from_row(row: sqlite3.Row | tuple) -> DocumentSource:
    return DocumentSource(
        id=row[0],
        label=row[1],
        path=row[2],
        created_at=int(row[3]),
        updated_at=int(row[4]),
        last_indexed_at=int(row[5]) if row[5] is not None else None,
        last_chunk_count=int(row[6] or 0),
    )
