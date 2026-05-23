from ai_knowledge_agent.text import chunk_text, tokenize


def test_chunk_text_respects_overlap():
    chunks = chunk_text("alpha beta gamma delta epsilon", chunk_size=16, overlap=4)

    assert len(chunks) >= 2
    assert chunks[0]
    assert chunks[1]


def test_tokenize_supports_words_and_cjk():
    assert tokenize("Hello 知识库 123") == ["hello", "知识库", "123"]
