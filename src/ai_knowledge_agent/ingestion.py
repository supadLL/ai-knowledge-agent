from __future__ import annotations

import hashlib
from pathlib import Path

from .models import Chunk, Document
from .text import chunk_text, normalize_text, tokenize


SUPPORTED_EXTENSIONS = {".md", ".txt"}


def iter_source_files(source: Path) -> list[Path]:
    if source.is_file():
        files = [source]
    else:
        files = [path for path in source.rglob("*") if path.is_file()]
    return sorted(path for path in files if path.suffix.lower() in SUPPORTED_EXTENSIONS)


def read_document(path: Path) -> str:
    return normalize_text(path.read_text(encoding="utf-8"))


def document_id(path: Path, content: str) -> str:
    digest = hashlib.sha256()
    digest.update(str(path.resolve()).encode("utf-8"))
    digest.update(b"\0")
    digest.update(content.encode("utf-8"))
    return digest.hexdigest()[:16]


def load_chunks(source: Path, chunk_size: int, overlap: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in iter_source_files(source):
        content = read_document(path)
        doc = Document(
            id=document_id(path, content),
            path=str(path.resolve()),
            filename=path.name,
            type=path.suffix.lower().lstrip("."),
        )
        for index, chunk_content in enumerate(chunk_text(content, chunk_size, overlap)):
            chunk_id = f"{doc.id}:{index}"
            chunks.append(
                Chunk(
                    id=chunk_id,
                    document_id=doc.id,
                    filename=doc.filename,
                    path=doc.path,
                    index=index,
                    content=chunk_content,
                    tokens=tokenize(chunk_content),
                )
            )
    return chunks
