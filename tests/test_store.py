from ai_knowledge_agent.embeddings import HashEmbeddingProvider
from ai_knowledge_agent.ingestion import load_chunks
from ai_knowledge_agent.store import (
    delete_document,
    load_document_summaries,
    load_index,
    save_chunks,
    upsert_document_chunks,
)


def test_save_and_load_sqlite_index(tmp_path):
    source = tmp_path / "raw"
    source.mkdir()
    (source / "note.md").write_text("# Note\n\nRetrieval needs citations.", encoding="utf-8")

    chunks = load_chunks(source, chunk_size=200, overlap=20)
    index_path = save_chunks(tmp_path / "index", chunks, HashEmbeddingProvider(dimensions=16))
    loaded = load_index(tmp_path / "index")

    assert index_path.name == "knowledge.db"
    assert len(loaded) == 1
    assert loaded[0].embedding


def test_load_document_summaries(tmp_path):
    source = tmp_path / "raw"
    source.mkdir()
    (source / "note.md").write_text("# Note\n\nRetrieval needs citations.", encoding="utf-8")
    chunks = load_chunks(source, chunk_size=200, overlap=20)

    save_chunks(tmp_path / "index", chunks, HashEmbeddingProvider(dimensions=16))
    summaries = load_document_summaries(tmp_path / "index")

    assert len(summaries) == 1
    assert summaries[0].filename == "note.md"
    assert summaries[0].chunk_count == 1


def test_upsert_and_delete_single_document(tmp_path):
    source = tmp_path / "raw"
    source.mkdir()
    note = source / "note.md"
    other = source / "other.md"
    note.write_text("First version.", encoding="utf-8")
    other.write_text("Other document.", encoding="utf-8")
    index_dir = tmp_path / "index"

    save_chunks(index_dir, load_chunks(source, chunk_size=200, overlap=20))
    note.write_text("Second version with replacement.", encoding="utf-8")
    upsert_document_chunks(index_dir, load_chunks(note, chunk_size=200, overlap=20))
    summaries = load_document_summaries(index_dir)
    note_summary = next(summary for summary in summaries if summary.filename == "note.md")

    assert len(summaries) == 2
    assert any("Second version" in chunk.content for chunk in load_index(index_dir))
    assert delete_document(index_dir, note_summary.id)
    assert [summary.filename for summary in load_document_summaries(index_dir)] == ["other.md"]
