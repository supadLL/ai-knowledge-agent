# AI Knowledge Agent MVP TODO

## Final Goal

The live project goal is maintained in [docs/goal.md](docs/goal.md).

When the app is running, open:

```text
http://127.0.0.1:8766/goal
```

## MVP Definition

Build a Windows-first, local-first knowledge workspace that can:

1. Index local Markdown and TXT files.
2. Persist chunks, metadata, vectors, config, logs, and eval reports locally.
3. Answer user questions in a chat-style UI with citations.
4. Evaluate retrieval quality with saved reports.
5. Import model accounts through OAuth, Token/JSON, API Key, import URL, or local file.
6. Route generation through an app-internal Fuel Pool without changing machine-wide proxy settings.
7. Keep secrets masked in API responses, UI, errors, and test output.

## Completed

- [x] Python package structure under `src/ai_knowledge_agent`.
- [x] Local data layout for raw files, index, config, logs, and eval results.
- [x] `.env.example` and Git ignore rules for env files, local databases, indexes, logs, virtualenvs, caches, dependency folders, and generated eval output.
- [x] CLI commands for indexing, asking, eval, and diagnostics.
- [x] FastAPI local web server and static frontend.
- [x] Markdown/TXT ingestion.
- [x] Text normalization, CJK-aware tokenization, chunking, stable chunk ids, and overlap handling.
- [x] Local hash embedding provider.
- [x] SQLite-backed document, chunk, and vector store.
- [x] Hybrid retrieval with top-k configuration.
- [x] Local extractive answer generation with citations.
- [x] OpenAI-compatible generation and embedding provider boundaries.
- [x] Chat-style ask UI with source expansion.
- [x] Document/index status page.
- [x] Eval runner and web eval trigger.
- [x] Fuel Pool account storage, masking, usage tracking, cooldown, priority, weight, and dispatch strategies.
- [x] Internal-only account dispatch for app RAG/eval generation.
- [x] OAuth account import with automatic callback completion.
- [x] Token/session JSON, raw token, API Key, import URL, and local JSON file account imports.
- [x] Account health checks.
- [x] Bilingual UI switch.
- [x] `/goal` and `/api/goal` project target checkpoint.
- [x] Tests for ingestion, chunking, embeddings, storage, retrieval, generation, eval, Fuel Pool, account storage, OAuth, internal conversion, web APIs, and goal routes.

## Current Verification

Run before every handoff:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
node --check src\ai_knowledge_agent\static\app.js
```

## Remaining MVP Hardening

- [x] Add a local smoke script that runs tests, lint, JavaScript syntax checks, sample indexing, sample ask, eval, and `/goal` HTTP check when the server is running.
- [x] Add browser-driven frontend smoke test that opens `http://127.0.0.1:8766/`, indexes sample files, asks a sample question, and verifies citations.
- [x] Add a document registry so folders can be reindexed without retyping paths.
- [x] Add per-document delete/reindex controls.
- [x] Add eval history list in the UI.
- [x] Add eval history comparison in the UI.
- [x] Add safer credential storage for refresh token sets before long-lived account refresh.
- [x] Add token refresh before Codex-account generation when refresh credentials are available.
- [x] Add a Windows-first packaged launch path and smoke test.
- [x] Add app data migration notes for future upgrades.

## Next Build Order

1. Final release-oriented smoke checks.
2. Final review and push once GitHub auth is available.
3. Stretch goals after MVP sign-off.

## Stretch Goals

- [ ] PDF parsing.
- [ ] Reranking.
- [ ] Web page import.
- [ ] GitHub repository indexing.
- [ ] MCP server for external tool integration.
- [ ] Learning-roadmap generation from indexed notes.
- [ ] Windows installer.
- [ ] Automatic update flow or documented manual upgrade path.
