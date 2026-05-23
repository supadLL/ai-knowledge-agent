from __future__ import annotations

import math
from collections import Counter

from .embeddings import EmbeddingProvider, cosine_similarity
from .models import Chunk, RetrievalResult
from .text import tokenize


def lexical_score(query_tokens: list[str], chunk: Chunk) -> float:
    if not query_tokens or not chunk.tokens:
        return 0.0
    query_counts = Counter(query_tokens)
    chunk_counts = Counter(chunk.tokens)
    common = set(query_counts) & set(chunk_counts)
    if not common:
        return 0.0

    dot = sum(query_counts[token] * chunk_counts[token] for token in common)
    query_norm = math.sqrt(sum(value * value for value in query_counts.values()))
    chunk_norm = math.sqrt(sum(value * value for value in chunk_counts.values()))
    return dot / (query_norm * chunk_norm)


def hybrid_score(
    query_tokens: list[str],
    query_embedding: list[float],
    chunk: Chunk,
    vector_weight: float,
) -> float:
    vector_weight = clamp_vector_weight(vector_weight)
    lexical = lexical_score(query_tokens, chunk)
    vector = cosine_similarity(query_embedding, chunk.embedding)
    if not chunk.embedding:
        return lexical
    return (lexical * (1.0 - vector_weight)) + (vector * vector_weight)


def clamp_vector_weight(vector_weight: float) -> float:
    return max(0.0, min(1.0, vector_weight))


def retrieve(
    query: str,
    chunks: list[Chunk],
    top_k: int,
    embedding_provider: EmbeddingProvider | None = None,
    vector_weight: float = 0.65,
) -> list[RetrievalResult]:
    query_tokens = tokenize(query)
    vector_weight = clamp_vector_weight(vector_weight)
    query_embedding = embedding_provider.embed(query) if embedding_provider is not None else []
    results = [
        RetrievalResult(
            chunk=chunk,
            score=hybrid_score(query_tokens, query_embedding, chunk, vector_weight)
            if embedding_provider is not None
            else lexical_score(query_tokens, chunk),
        )
        for chunk in chunks
    ]
    results = [result for result in results if result.score > 0]
    return sorted(results, key=lambda result: result.score, reverse=True)[:top_k]
