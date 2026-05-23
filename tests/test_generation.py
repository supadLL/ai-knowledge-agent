import pytest

from ai_knowledge_agent.generation import (
    LocalExtractiveGenerator,
    OpenAICompatibleChatGenerator,
    build_context,
    create_generation_provider,
)
from ai_knowledge_agent.config import AppConfig
from ai_knowledge_agent.fuel_pool import FuelPoolGenerationProvider
from ai_knowledge_agent.llm_access import LlmAccountStore
from ai_knowledge_agent.models import Chunk, RetrievalResult
from ai_knowledge_agent.providers import generation_provider_from_config


def test_create_local_generation_provider():
    provider = create_generation_provider("local")

    assert isinstance(provider, LocalExtractiveGenerator)


def test_create_openai_generation_requires_key():
    with pytest.raises(ValueError, match="GENERATION_API_KEY"):
        create_generation_provider("openai-compatible")


def test_create_openai_generation_provider():
    provider = create_generation_provider(
        "openai-compatible",
        api_key="test-key",
        model="chat-model",
        base_url="https://example.com/v1/",
    )

    assert isinstance(provider, OpenAICompatibleChatGenerator)
    assert provider.model == "chat-model"
    assert provider.base_url == "https://example.com/v1"


def test_build_context_respects_char_budget():
    chunk = Chunk("a", "doc", "a.md", "a.md", 0, "abcdef", ["abcdef"], [0.1])
    context = build_context([RetrievalResult(chunk, 1.0)], char_budget=3)

    assert context == "[a.md#0]\nabc"


def test_generation_provider_prefers_fuel_pool_when_accounts_exist(tmp_path):
    config = AppConfig(
        data_dir=tmp_path,
        raw_dir=tmp_path / "raw",
        index_dir=tmp_path / "index",
        config_dir=tmp_path / "config",
        logs_dir=tmp_path / "logs",
    )
    LlmAccountStore(config.config_dir).create_account(
        name="Local relay",
        provider_type="local_relay",
        base_url="http://127.0.0.1:1455/v1",
        model="relay-model",
        api_key="",
    )

    provider = generation_provider_from_config(config)

    assert isinstance(provider, FuelPoolGenerationProvider)
