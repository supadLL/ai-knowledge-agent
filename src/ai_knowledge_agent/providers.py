from __future__ import annotations

from .config import AppConfig
from .embeddings import EmbeddingProvider, create_embedding_provider
from .fuel_pool import fuel_pool_generation_provider
from .generation import GenerationProvider, create_generation_provider
from .llm_access import LlmAccountStore


def embedding_provider_from_config(config: AppConfig) -> EmbeddingProvider:
    return create_embedding_provider(
        provider=config.embedding_provider,
        dimensions=config.embedding_dimensions,
        api_key=config.embedding_api_key,
        model=config.embedding_model,
        base_url=config.embedding_base_url,
    )


def generation_provider_from_config(config: AppConfig) -> GenerationProvider:
    store = LlmAccountStore(config.config_dir)
    fuel_provider = fuel_pool_generation_provider(store, config.generation_context_chars)
    if fuel_provider is not None:
        return fuel_provider
    return create_generation_provider(
        provider=config.generation_provider,
        api_key=config.generation_api_key,
        model=config.generation_model,
        base_url=config.generation_base_url,
        context_char_budget=config.generation_context_chars,
    )
