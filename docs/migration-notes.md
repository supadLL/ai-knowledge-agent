# App Data Migration Notes

AI Knowledge Agent keeps user data local. Future upgrades should preserve these folders unless the user explicitly chooses to reset them.

## Local Data Roots

Default paths are relative to the app folder:

```text
data\raw\        source documents and samples
data\index\      searchable SQLite index
data\config\     app.db account registry, Fuel Pool settings, OAuth state
data\logs\       local logs when enabled
evals\results\   saved eval reports
```

Portable packages use the same layout inside `dist\ai-knowledge-agent\`.

## Before Upgrade

1. Stop the web server.
2. Back up `data\config\app.db`, `data\index\knowledge.db`, `data\raw\`, and `evals\results\`.
3. Keep `.env` local and do not commit it.
4. If moving to another Windows user account, re-import OAuth/session accounts because DPAPI-protected refresh payloads are bound to the Windows user that created them.

## Schema Policy

SQLite schema changes should be additive where possible.

- Add columns through `ensure_column(...)`.
- Keep old columns readable until a documented cleanup release.
- Never expose raw `api_key` or `credential_payload` through API responses.
- If a migration needs to rewrite secrets, keep the old value until the new encrypted value has been verified.

Current app database:

- `llm_accounts`
- `llm_usage_events`
- `fuel_pool_settings`
- `document_sources`
- `codex_oauth_pending`

`document_sources` also stores auto-index state: whether a source is enabled, the last scan fingerprint, last automatic index time, and the last automatic index error.

Current index database:

- document/chunk/vector records managed by `src/ai_knowledge_agent/store.py`

## Rebuild Rules

If index format changes:

1. Keep `data\raw\` unchanged.
2. Move the old `data\index\knowledge.db` to a timestamped backup.
3. Rebuild from saved document sources or from `data\raw\`.
4. Run eval and compare against the previous saved report.

If auto-index behavior changes:

1. Keep saved source paths intact.
2. Reset `last_auto_fingerprint` only when a full source rescan is intended.
3. Prefer source-level replacement indexing so one source refresh does not delete other saved sources.
4. Verify added, modified, and removed `.md` / `.txt` files are reflected in `data\index\knowledge.db`.

If account schema changes:

1. Run tests that assert public account responses are masked.
2. Run a local account import flow.
3. Verify Fuel Pool status without printing raw credentials.
4. Verify app-internal dispatch does not alter global Codex/OpenAI/proxy config.

## Release Checklist

Before handing off an upgrade:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
node --check src\ai_knowledge_agent\static\app.js
.\scripts\smoke.ps1
.\scripts\package.ps1
powershell -ExecutionPolicy Bypass -File .\dist\ai-knowledge-agent\smoke-packaged.ps1
```
