from ai_knowledge_agent.models import Chunk
from ai_knowledge_agent.embeddings import HashEmbeddingProvider
from ai_knowledge_agent.retrieval import clamp_vector_weight, retrieve


def test_retrieve_returns_best_matching_chunk():
    chunks = [
        Chunk("a", "doc", "a.md", "a.md", 0, "chunking embeddings retrieval", ["chunking", "embeddings", "retrieval"]),
        Chunk("b", "doc", "b.md", "b.md", 0, "packaging installer desktop", ["packaging", "installer", "desktop"]),
    ]

    results = retrieve("how does retrieval work", chunks, top_k=1)

    assert results[0].chunk.id == "a"


def test_retrieve_supports_hash_embeddings():
    provider = HashEmbeddingProvider(dimensions=32)
    chunks = [
        Chunk(
            "a",
            "doc",
            "a.md",
            "a.md",
            0,
            "chunking embeddings retrieval",
            ["chunking", "embeddings", "retrieval"],
            provider.embed("chunking embeddings retrieval"),
        ),
        Chunk(
            "b",
            "doc",
            "b.md",
            "b.md",
            0,
            "packaging installer desktop",
            ["packaging", "installer", "desktop"],
            provider.embed("packaging installer desktop"),
        ),
    ]

    results = retrieve("semantic retrieval", chunks, top_k=1, embedding_provider=provider)

    assert results[0].chunk.id == "a"


def test_clamp_vector_weight():
    assert clamp_vector_weight(-1) == 0
    assert clamp_vector_weight(0.25) == 0.25
    assert clamp_vector_weight(2) == 1
