from ai_knowledge_agent.config import AppConfig


def test_embedding_provider_is_normalized(monkeypatch):
    monkeypatch.setenv("AI_KNOWLEDGE_AGENT_EMBEDDING_PROVIDER", " OpenAI-Compatible ")

    config = AppConfig.from_env()

    assert config.embedding_provider == "openai-compatible"
