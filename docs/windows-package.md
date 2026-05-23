# Windows Package Path

The project has a Windows-first portable package path for local release checks.

## Build

```powershell
.\scripts\package.ps1
```

This creates:

```text
dist\ai-knowledge-agent\
```

The package contains source code, static UI, sample data, docs, eval questions, and two local scripts:

- `launch.ps1`: creates an in-package `.venv`, installs the app in editable mode, and starts the web UI on `127.0.0.1:8766`.
- `smoke-packaged.ps1`: validates the packaged environment, Python tests, ruff, JavaScript syntax, CLI diagnostics, and `/api/goal`.

## Run

```powershell
powershell -ExecutionPolicy Bypass -File .\dist\ai-knowledge-agent\launch.ps1
```

Open:

```text
http://127.0.0.1:8766/
```

## Smoke

```powershell
powershell -ExecutionPolicy Bypass -File .\dist\ai-knowledge-agent\smoke-packaged.ps1
```

The package scripts only configure the copied app folder. They do not modify machine-wide Codex, OpenAI, proxy, or shell profile settings.
