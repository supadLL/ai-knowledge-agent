# /goal: AI Knowledge Agent Final Goal

## North Star

Build a Windows-first, local-first AI knowledge workspace that lets a user import local files, build a persistent searchable index, connect app-internal LLM accounts through a private Fuel Pool, and chat with their own knowledge base with inspectable citations.

The application must feel like a local product, not a script demo:

- It runs from a predictable local URL during development.
- It keeps user documents, indexes, account config, logs, and eval results outside source code.
- It never exposes imported account credentials as a general local relay for other tools.
- It can be packaged later without changing the core RAG pipeline.
- It gives the user a clear UI for indexing, asking, inspecting sources, importing accounts, testing accounts, and checking status.

## Current Product Target

The current target is a complete local web MVP:

1. Index local Markdown and TXT files.
2. Store document chunks, metadata, and vectors in a local SQLite index.
3. Ask questions in a chat-style interface.
4. Retrieve relevant context and answer with source citations.
5. Run retrieval evaluation cases and save reports.
6. Import model accounts through OAuth, pasted token/session JSON, API keys, import URLs, or local JSON files.
7. Route generation through an app-internal Fuel Pool with account priority, weight, cooldown, health checks, and usage tracking.
8. Keep all imported account usage internal to this app's RAG and eval operations.
9. Provide diagnostics, settings, status messages, and bilingual UI switching.
10. Maintain tests that protect the core ingestion, retrieval, generation, eval, account, OAuth, proxy, and web flows.

## Definition Of Done

The MVP is considered complete when:

- A fresh checkout can install dependencies, run tests, start the web app, build the sample index, and answer a sample question.
- `/goal` shows this target and can be used as the project checkpoint.
- `README.md` describes the actual current app, not only the early plan.
- `mvp-todo.md` reflects completed work and the next remaining phases.
- The web UI can complete the main user flow without manual API calls:
  - open app
  - index local files
  - ask in chat
  - inspect citations
  - import or add an account
  - test account health
  - run eval
- Tests pass locally with `pytest`.
- Linting passes with `ruff`.
- JavaScript syntax checks pass with `node --check`.
- Generated indexes, local config databases, logs, env files, virtualenvs, caches, and dependency folders are ignored by Git.
- GitHub has the latest clean commit after authentication is configured.

## Next Build Direction

After the current MVP is stable, continue in this order:

1. Add PDF ingestion.
2. Add a document registry and per-folder reindex controls.
3. Add token refresh and safer credential storage.
4. Add eval history comparison in the UI.
5. Add packaged Windows launch flow.
6. Add app data migration and upgrade checks.
7. Add a packaging smoke test.

## Non-Goals

- Do not turn the account Fuel Pool into a system-wide local proxy.
- Do not modify Codex, OpenAI, or other local machine API settings.
- Do not expose raw account tokens from APIs, logs, tests, or UI responses.
- Do not require cloud deployment for normal use.
