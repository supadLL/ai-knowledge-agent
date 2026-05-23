# AI Knowledge Agent

Local-first personal knowledge-base app for indexing local files, asking citation-backed questions, evaluating retrieval quality, and routing app-internal LLM work through a local account Fuel Pool.

## Goal

The project target is documented at:

```text
docs/goal.md
```

When the web app is running, open:

```text
http://127.0.0.1:8766/goal
```

## Current MVP

- Index local `.md` and `.txt` files.
- Save document source folders and reindex them later from the UI.
- Persist chunks, metadata, and vectors to `data/index/knowledge.db`.
- Ask questions through a chat-style local web UI.
- Return grounded answers with source citations.
- Inspect document/index status and provider settings.
- Run retrieval evaluation cases and save reports.
- Import model accounts through OAuth, pasted token/session JSON, API keys, import URLs, or local JSON files.
- Dispatch app-internal generation through the Fuel Pool with account priority, weight, cooldown, health checks, and usage tracking.
- Keep imported account usage internal to this app; it does not modify local Codex or machine-wide API proxy settings.
- Switch UI language between Chinese and English.

## Setup

```powershell
cd E:\ai-play\ai-knowledge-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m playwright install chromium
npm install
```

## Run The Web App

```powershell
.\scripts\web.ps1
```

Then open:

```text
http://127.0.0.1:8766/
```

Goal checkpoint:

```text
http://127.0.0.1:8766/goal
```

## Windows Package

```powershell
.\scripts\package.ps1
powershell -ExecutionPolicy Bypass -File .\dist\ai-knowledge-agent\launch.ps1
```

Packaged smoke:

```powershell
powershell -ExecutionPolicy Bypass -File .\dist\ai-knowledge-agent\smoke-packaged.ps1
```

More details: [docs/windows-package.md](docs/windows-package.md).

Upgrade and data migration notes: [docs/migration-notes.md](docs/migration-notes.md).

## CLI

Index sample documents:

```powershell
aka index .\data\raw
```

Ask a question:

```powershell
aka ask "How does the app preserve local data?"
```

Run diagnostics:

```powershell
aka diagnose
```

Run eval:

```powershell
aka eval --questions .\evals\questions.json
```

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
node --check src\ai_knowledge_agent\static\app.js
```

Full local smoke check:

```powershell
.\scripts\smoke.ps1
```

Browser-driven UI smoke check:

```powershell
.\scripts\web.ps1
.\scripts\frontend-smoke.ps1
```

## Local Data Layout

```text
data/
  raw/       sample source documents
  index/     generated chunk index, ignored by Git
  config/    local app database and account config, ignored by Git
  logs/      local diagnostics logs, ignored by Git
evals/
  questions.json
  results/   generated eval reports, ignored by Git
```

## Account Boundary

Fuel Pool accounts are only used inside this app for RAG and evaluation generation. The app does not expose a general local relay endpoint for other tools and does not change local Codex, OpenAI, or other API settings.

API responses return masked account secrets. Refresh credentials are stored in a separate local secret payload, protected by Windows DPAPI when running on Windows, and are only used by this app's Fuel Pool refresh path. Generated local config databases, env files, logs, indexes, virtualenvs, caches, and dependency folders are ignored by Git.

## UI Design

Design image:

```text
stitch-ui-design.png
stitch-ui-design-latest.png
```

Prompt and rerun notes:

```text
docs/stitch-ui-design.md
```
