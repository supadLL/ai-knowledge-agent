from ai_knowledge_agent.text import chunk_text, tokenize


def test_chunk_text_respects_overlap():
    chunks = chunk_text("alpha beta gamma delta epsilon", chunk_size=16, overlap=4)

    assert len(chunks) >= 2
    assert chunks[0]
    assert chunks[1]


def test_tokenize_supports_words_numbers_and_cjk():
    tokens = tokenize("Hello 知识库123")

    assert "hello" in tokens
    assert "知识" in tokens
    assert "识库" in tokens
    assert "123" in tokens


def test_chunk_text_preserves_cjk_sentence_boundary():
    chunks = chunk_text("知识库检索。第二句话包含答案。", chunk_size=8, overlap=2)

    assert chunks[0].endswith("。")


def test_tokenize_supports_cjk_character_and_bigram_matches():
    tokens = tokenize("知识库检索")

    assert "知" in tokens
    assert "知识" in tokens
    assert "检索" in tokens
