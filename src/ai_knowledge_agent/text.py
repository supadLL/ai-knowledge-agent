from __future__ import annotations

import re


TOKEN_RE = re.compile(r"[A-Za-z0-9_\u4e00-\u9fff]+")


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_RE.finditer(text)]


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    text = normalize_text(text)
    if not text:
        return []

    if overlap >= chunk_size:
        raise ValueError("chunk overlap must be smaller than chunk size")

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        candidate = text[start:end]
        if end < len(text):
            split_at = max(candidate.rfind("\n\n"), candidate.rfind(". "), candidate.rfind("。"))
            if split_at > chunk_size * 0.55:
                end = start + split_at + 1
                candidate = text[start:end]
        chunks.append(candidate.strip())
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return [chunk for chunk in chunks if chunk]
