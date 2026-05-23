import pytest

from ai_knowledge_agent.embeddings import (
    HashEmbeddingProvider,
    OpenAICompatibleEmbeddingProvider,
    create_embedding_provider,
)


def test_create_hash_embedding_provider():
    provider = create_embedding_provider("hash", dimensions=32)

    assert isinstance(provider, HashEmbeddingProvider)
    assert provider.dimensions == 32


def test_create_openai_compatible_requires_key():
    with pytest.raises(ValueError, match="EMBEDDING_API_KEY"):
        create_embedding_provider("openai-compatible")


def test_create_openai_compatible_provider():
    provider = create_embedding_provider(
        "openai-compatible",
        api_key="test-key",
        model="embedding-model",
        base_url="https://example.com/v1/",
    )

    assert isinstance(provider, OpenAICompatibleEmbeddingProvider)
    assert provider.model == "embedding-model"
    assert provider.base_url == "https://example.com/v1"
