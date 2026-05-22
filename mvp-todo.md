# AI Knowledge Agent MVP TODO

## MVP Goal

Build a minimal but complete personal knowledge-base Agent:

1. Import local Markdown or TXT documents.
2. Chunk and embed the content.
3. Retrieve relevant chunks for a user question.
4. Generate an answer with citations.
5. Run a small evaluation set to compare quality across prompt and retrieval settings.

## Definition Of Done

- A user can add documents from a local folder.
- The app creates and persists a searchable index.
- A user can ask a question and get an answer grounded in retrieved chunks.
- Each answer includes at least one source citation.
- An eval command can run at least 10 test questions.
- The project has a clear README, architecture diagram, and demo path.

## Phase 0: Project Setup

- [ ] Choose stack:
  - Suggested backend: Python + FastAPI.
  - Suggested vector store: Chroma or SQLite-backed local store.
  - Suggested UI: minimal React/Vite or simple CLI first.
- [ ] Create repository structure:
  - `src/`
  - `data/raw/`
  - `data/index/`
  - `evals/`
  - `docs/`
  - `tests/`
- [ ] Add `.env.example`.
- [ ] Add README with project goal and local run instructions.
- [ ] Add basic formatter/linter configuration.

## Phase 1: Document Ingestion

- [ ] Implement file loader for `.md`.
- [ ] Implement file loader for `.txt`.
- [ ] Normalize extracted text.
- [ ] Add metadata:
  - filename
  - file path
  - document id
  - chunk index
- [ ] Implement chunking strategy:
  - default chunk size
  - overlap size
  - stable chunk ids
- [ ] Add a command:
  - `index ./data/raw`
- [ ] Verify indexed chunk count is printed after ingestion.

## Phase 2: Embedding And Storage

- [ ] Add embedding provider abstraction.
- [ ] Implement first embedding provider.
- [ ] Persist chunk text, metadata, and vectors.
- [ ] Implement similarity search.
- [ ] Add top-k retrieval configuration.
- [ ] Add a smoke test with a tiny fixture document.

## Phase 3: Question Answering

- [ ] Implement query endpoint or CLI command:
  - `ask "your question"`
- [ ] Retrieve top-k chunks.
- [ ] Construct grounded prompt.
- [ ] Generate answer.
- [ ] Include citations using document name and chunk index.
- [ ] Add fallback behavior when no relevant context is found.
- [ ] Log:
  - query
  - retrieved chunk ids
  - similarity scores
  - latency
  - token usage if available

## Phase 4: Minimal UI Or CLI

- [ ] Choose MVP interface:
  - CLI is faster.
  - Web UI is better for portfolio display.
- [ ] If CLI:
  - Add `index`, `ask`, and `eval` commands.
- [ ] If Web UI:
  - Add document upload page.
  - Add chat/question page.
  - Add source citation display.
  - Add loading and error states.

## Phase 5: Evaluation

- [ ] Create `evals/questions.json`.
- [ ] Add at least 10 question-answer-source cases.
- [ ] Implement eval runner.
- [ ] Track:
  - answer correctness
  - citation correctness
  - retrieval hit rate
  - average latency
  - average token cost
- [ ] Save eval results to `evals/results/`.
- [ ] Add a short failure analysis section after each run.

## Phase 6: Polish For Resume

- [ ] Add architecture diagram to README.
- [ ] Add demo screenshots or GIF.
- [ ] Add example documents and example questions.
- [ ] Add a section explaining RAG design tradeoffs:
  - chunk size
  - overlap
  - top-k
  - prompt rules
  - citation strategy
- [ ] Add a section explaining evaluation results.
- [ ] Write resume bullets.

## Suggested First Implementation Order

1. CLI-only ingestion.
2. Local vector search.
3. CLI question answering with citations.
4. Eval runner.
5. Web UI after the core pipeline works.

## Minimal Folder Structure

```text
ai-knowledge-agent/
  knowledge-graph.md
  mvp-todo.md
  README.md
  .env.example
  src/
    app/
    ingestion/
    retrieval/
    generation/
    evaluation/
  data/
    raw/
    index/
  evals/
    questions.json
    results/
  tests/
```

## Initial Resume Bullets Draft

- Built a personal AI knowledge-base Agent with document ingestion, chunking, embeddings, vector retrieval, grounded generation, and citation-backed answers.
- Designed a lightweight RAG evaluation pipeline to measure retrieval hit rate, citation correctness, latency, and answer quality across prompt and retrieval configurations.
- Implemented an extensible architecture separating ingestion, retrieval, generation, and evaluation modules for future support of PDF parsing, web import, and MCP tool integration.

## Near-Term Stretch Goals

- [ ] Add PDF parsing.
- [ ] Add reranking.
- [ ] Add web page import.
- [ ] Add model/provider switcher.
- [ ] Add MCP server for external tool integration.
- [ ] Add GitHub repository indexing.
- [ ] Add learning-roadmap generation from indexed notes.
