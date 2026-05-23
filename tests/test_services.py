from ai_knowledge_agent.config import AppConfig
from ai_knowledge_agent.llm_access import LlmAccountStore
from ai_knowledge_agent.services import AnswerService, IndexService


def test_index_and_answer_services_work_together(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "note.md").write_text(
        "Local data stays outside the installed app directory.", encoding="utf-8"
    )
    config = AppConfig(
        data_dir=tmp_path,
        raw_dir=raw_dir,
        index_dir=tmp_path / "index",
        config_dir=tmp_path / "config",
        logs_dir=tmp_path / "logs",
    )
    index_service = IndexService(config)

    build = index_service.rebuild_index(raw_dir)
    answer = AnswerService(index_service).ask("Where does local data stay?")

    assert build.chunk_count == 1
    assert answer.sources
    assert "note.md#0" in answer.answer


def test_index_service_stats(tmp_path):
    config = AppConfig(
        data_dir=tmp_path,
        raw_dir=tmp_path / "raw",
        index_dir=tmp_path / "index",
        config_dir=tmp_path / "config",
        logs_dir=tmp_path / "logs",
    )

    stats = IndexService(config).stats()

    assert stats.indexed_chunks == 0
    assert stats.indexed_documents == 0
    assert stats.embedding_provider == "hash-embedding-v1"


def test_index_service_stats_show_enabled_llm_account(tmp_path):
    config = AppConfig(
        data_dir=tmp_path,
        raw_dir=tmp_path / "raw",
        index_dir=tmp_path / "index",
        config_dir=tmp_path / "config",
        logs_dir=tmp_path / "logs",
    )
    LlmAccountStore(config.config_dir).create_account(
        name="Codex gateway",
        provider_type="codex_local_access",
        base_url="http://127.0.0.1:1455/v1",
        model="gpt-5.4",
    )

    stats = IndexService(config).stats()

    assert stats.generation_provider == "fuel-pool:first_available"
    assert stats.generation_model == "gpt-5.4"
