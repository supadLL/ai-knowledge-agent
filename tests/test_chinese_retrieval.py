from ai_knowledge_agent.embeddings import HashEmbeddingProvider
from ai_knowledge_agent.ingestion import load_chunks
from ai_knowledge_agent.retrieval import retrieve


def test_chinese_query_retrieves_chinese_document(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "note.md").write_text(
        "本地知识库会先检索相关片段，然后交给 AI 总结回答。",
        encoding="utf-8",
    )
    chunks = load_chunks(raw_dir, chunk_size=120, overlap=20)

    results = retrieve(
        "知识库如何总结回答？",
        chunks,
        top_k=3,
        embedding_provider=HashEmbeddingProvider(),
    )

    assert results
    assert results[0].chunk.filename == "note.md"
