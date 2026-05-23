from __future__ import annotations

import hashlib
import json
import math
import urllib.error
import urllib.request
from typing import Protocol

from .text import tokenize


class EmbeddingProvider(Protocol):
    name: str
    dimensions: int

    def embed(self, text: str) -> list[float]:
        """Return a deterministic vector for the input text."""


class HashEmbeddingProvider:
    name = "hash-embedding-v1"

    def __init__(self, dimensions: int = 256) -> None:
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in tokenize(text):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign
        return normalize_vector(vector)


class OpenAICompatibleEmbeddingProvider:
    name = "openai-compatible"

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: int = 60,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.dimensions = 0

    def embed(self, text: str) -> list[float]:
        payload = json.dumps({"model": self.model, "input": text}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/embeddings",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            message = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Embedding request failed: HTTP {error.code} {message}") from error
        except urllib.error.URLError as error:
            raise RuntimeError(f"Embedding request failed: {error.reason}") from error

        try:
            embedding = body["data"][0]["embedding"]
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError(f"Embedding response did not contain data[0].embedding: {body}") from error
        self.dimensions = len(embedding)
        return [float(value) for value in embedding]


def create_embedding_provider(
    provider: str,
    dimensions: int = 256,
    api_key: str | None = None,
    model: str = "text-embedding-3-small",
    base_url: str = "https://api.openai.com/v1",
) -> EmbeddingProvider:
    normalized = provider.strip().lower()
    if normalized == "hash":
        return HashEmbeddingProvider(dimensions=dimensions)
    if normalized in {"openai", "openai-compatible"}:
        if not api_key:
            raise ValueError(
                "AI_KNOWLEDGE_AGENT_EMBEDDING_API_KEY or OPENAI_API_KEY is required "
                "for the OpenAI-compatible embedding provider."
            )
        return OpenAICompatibleEmbeddingProvider(api_key=api_key, model=model, base_url=base_url)
    raise ValueError(f"Unknown embedding provider: {provider}")


def normalize_vector(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(left_value * right_value for left_value, right_value in zip(left, right, strict=True))
