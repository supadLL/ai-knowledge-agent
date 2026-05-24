from ai_knowledge_agent.auto_index import AutoIndexService
from ai_knowledge_agent.config import AppConfig
from ai_knowledge_agent.document_sources import DocumentSourceStore
from ai_knowledge_agent.services import IndexService


def test_auto_index_indexes_changed_source_and_preserves_other_sources(tmp_path):
    raw_a = tmp_path / "a"
    raw_b = tmp_path / "b"
    raw_a.mkdir()
    raw_b.mkdir()
    (raw_a / "a.md").write_text("Alpha local knowledge.", encoding="utf-8")
    (raw_b / "b.md").write_text("Beta local knowledge.", encoding="utf-8")
    config = AppConfig(
        data_dir=tmp_path,
        raw_dir=raw_a,
        index_dir=tmp_path / "index",
        config_dir=tmp_path / "config",
        logs_dir=tmp_path / "logs",
    )
    store = DocumentSourceStore(config.config_dir)
    store.upsert_source(raw_a, "A")
    source_b = store.upsert_source(raw_b, "B")
    service = AutoIndexService(config)

    first_results = service.scan_once()
    (raw_b / "b.md").write_text("Beta updated local knowledge.", encoding="utf-8")
    second_results = service.scan_once()
    documents = IndexService(config).documents()

    assert len([result for result in first_results if result.indexed]) == 2
    assert [result.source_id for result in second_results if result.indexed] == [source_b.id]
    assert sorted(document.filename for document in documents) == ["a.md", "b.md"]


def test_auto_index_respects_disabled_source(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "note.md").write_text("Disabled source.", encoding="utf-8")
    config = AppConfig(
        data_dir=tmp_path,
        raw_dir=raw_dir,
        index_dir=tmp_path / "index",
        config_dir=tmp_path / "config",
        logs_dir=tmp_path / "logs",
    )
    store = DocumentSourceStore(config.config_dir)
    source = store.upsert_source(raw_dir, "Disabled")
    store.update_auto_index(source.id, False)

    results = AutoIndexService(config).scan_once()

    assert results == []
    assert IndexService(config).documents() == []
