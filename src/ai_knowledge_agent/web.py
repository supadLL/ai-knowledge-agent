from __future__ import annotations

import json
from html import escape
from dataclasses import asdict
from pathlib import Path
from typing import Annotated
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import AppConfig
from .codex_proxy import UPSTREAM_CODEX_BASE_URL
from .codex_oauth import (
    CodexOAuthService,
    authorized_callback_html,
    exchange_refresh_token,
    public_token_payload,
)
from .document_sources import DocumentSourceStore, public_source
from .evaluation import list_eval_results, run_eval
from .fuel_pool import FuelPoolService
from .fuel_pool import POOL_STRATEGIES
from .llm_access import LlmAccessService, LlmAccountStore, PROVIDER_TYPES, public_account
from .services import AnswerService, IndexService


STATIC_DIR = Path(__file__).resolve().parent / "static"
GOAL_DOC = Path(__file__).resolve().parents[2] / "docs" / "goal.md"


class IndexRequest(BaseModel):
    source: str = Field(default="./data/raw")


class DocumentSourceCreateRequest(BaseModel):
    path: str = Field(min_length=1)
    label: str | None = None


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)


class EvalRequest(BaseModel):
    questions_path: str = Field(default="./evals/questions.json")


class LlmAccountCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    provider_type: str = Field(default="openai_compatible")
    base_url: str = Field(default="https://api.openai.com/v1")
    model: str = Field(default="gpt-4o-mini", min_length=1)
    api_key: str = Field(default="")
    enabled: bool = Field(default=True)
    priority: int = Field(default=100, ge=0, le=1000)
    weight: int = Field(default=1, ge=1, le=100)


class LlmAccountUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    provider_type: str | None = None
    base_url: str | None = None
    model: str | None = Field(default=None, min_length=1)
    api_key: str | None = None
    enabled: bool | None = None
    priority: int | None = Field(default=None, ge=0, le=1000)
    weight: int | None = Field(default=None, ge=1, le=100)


class TokenImportRequest(BaseModel):
    payload: str = Field(min_length=1)


class ExternalImportRequest(BaseModel):
    source: str = Field(default="json")
    payload: str | None = None
    url: str | None = None
    provider_type: str = Field(default="auto")


class FuelPoolUpdateRequest(BaseModel):
    strategy: str | None = None


class CodexOAuthCallbackRequest(BaseModel):
    login_id: str = Field(min_length=1)
    callback_url: str = Field(min_length=1)


class CodexOAuthCompleteRequest(BaseModel):
    login_id: str = Field(min_length=1)


def get_config() -> AppConfig:
    config = AppConfig.from_env()
    config.ensure_dirs()
    return config


def create_app() -> FastAPI:
    app = FastAPI(title="AI Knowledge Agent", version="0.1.0")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/goal")
    def goal_page() -> HTMLResponse:
        return HTMLResponse(render_goal_html(read_goal_doc()))

    @app.get("/api/goal")
    def goal_api() -> dict:
        return {"goal": read_goal_doc()}

    @app.get("/api/stats")
    def stats(config: Annotated[AppConfig, Depends(get_config)]) -> dict:
        return asdict(IndexService(config).stats())

    @app.get("/api/documents")
    def documents(config: Annotated[AppConfig, Depends(get_config)]) -> dict:
        return {
            "documents": [
                asdict(document) for document in IndexService(config).documents()
            ]
        }

    @app.delete("/api/documents/{document_id}")
    def delete_indexed_document(
        document_id: str,
        config: Annotated[AppConfig, Depends(get_config)],
    ) -> dict:
        deleted = IndexService(config).delete_document(document_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Indexed document not found")
        return {"deleted": True}

    @app.post("/api/documents/{document_id}/index")
    def reindex_indexed_document(
        document_id: str,
        config: Annotated[AppConfig, Depends(get_config)],
    ) -> dict:
        try:
            result = IndexService(config).reindex_document(document_id)
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail=f"Source does not exist: {error}") from error
        if result is None:
            raise HTTPException(status_code=404, detail="Indexed document not found")
        return asdict(result)

    @app.get("/api/document-sources")
    def document_sources(config: Annotated[AppConfig, Depends(get_config)]) -> dict:
        store = DocumentSourceStore(config.config_dir)
        return {"sources": [public_source(source) for source in store.list_sources()]}

    @app.post("/api/document-sources")
    def create_document_source(
        request: DocumentSourceCreateRequest,
        config: Annotated[AppConfig, Depends(get_config)],
    ) -> dict:
        source_path = Path(request.path).resolve()
        if not source_path.exists():
            raise HTTPException(status_code=404, detail=f"Source does not exist: {source_path}")
        source = DocumentSourceStore(config.config_dir).upsert_source(
            source_path,
            label=request.label,
        )
        return {"source": public_source(source)}

    @app.delete("/api/document-sources/{source_id}")
    def delete_document_source(
        source_id: str,
        config: Annotated[AppConfig, Depends(get_config)],
    ) -> dict:
        deleted = DocumentSourceStore(config.config_dir).delete_source(source_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Document source not found")
        return {"deleted": True}

    @app.post("/api/document-sources/{source_id}/index")
    def rebuild_document_source(
        source_id: str,
        config: Annotated[AppConfig, Depends(get_config)],
    ) -> dict:
        store = DocumentSourceStore(config.config_dir)
        source = store.get_source(source_id)
        if source is None:
            raise HTTPException(status_code=404, detail="Document source not found")
        source_path = Path(source.path).resolve()
        if not source_path.exists():
            raise HTTPException(status_code=404, detail=f"Source does not exist: {source_path}")
        result = IndexService(config).rebuild_index(source_path)
        indexed_source = store.mark_indexed(source.id, result.chunk_count)
        return {
            "source": public_source(indexed_source or source),
            "index": asdict(result),
        }

    @app.post("/api/index")
    def rebuild_index(
        request: IndexRequest, config: Annotated[AppConfig, Depends(get_config)]
    ) -> dict:
        source = Path(request.source).resolve()
        if not source.exists():
            raise HTTPException(status_code=404, detail=f"Source does not exist: {source}")
        result = IndexService(config).rebuild_index(source)
        return asdict(result)

    @app.post("/api/ask")
    def ask(request: AskRequest, config: Annotated[AppConfig, Depends(get_config)]) -> dict:
        index_service = IndexService(config)
        if not index_service.load_chunks():
            raise HTTPException(status_code=400, detail="No index found. Build an index first.")
        result = AnswerService(index_service).ask(request.question, top_k=request.top_k)
        return {
            "question": result.question,
            "answer": result.answer,
            "generation_provider": result.generation_provider,
            "sources": [
                {
                    "filename": source.chunk.filename,
                    "chunk_index": source.chunk.index,
                    "path": source.chunk.path,
                    "score": round(source.score, 4),
                    "preview": source.chunk.content[:500],
                }
                for source in result.sources
            ],
        }

    @app.post("/api/eval")
    def evaluate(request: EvalRequest, config: Annotated[AppConfig, Depends(get_config)]) -> dict:
        questions_path = Path(request.questions_path).resolve()
        if not questions_path.exists():
            raise HTTPException(
                status_code=404, detail=f"Eval questions file does not exist: {questions_path}"
            )
        return run_eval(config, questions_path, Path("evals/results"))

    @app.get("/api/eval/results")
    def eval_results() -> dict:
        return {"results": list_eval_results(Path("evals/results"))}

    @app.get("/api/llm/providers")
    def llm_providers() -> dict:
        return {
            "providers": [
                {"id": provider_id, "label": label}
                for provider_id, label in PROVIDER_TYPES.items()
            ],
            "planned": [
                {
                    "id": "token_import",
                    "label": "Auth/session token import",
                    "enabled": True,
                    "reason": "OAuth, pasted token JSON, API key presets, and internal Fuel Pool imports.",
                }
            ],
        }

    @app.post("/api/oauth/codex/start")
    def start_codex_oauth(config: Annotated[AppConfig, Depends(get_config)]) -> dict:
        service = CodexOAuthService(config.config_dir)
        state = service.start_login(start_listener=True)
        return {"oauth": service.public_state(state)}

    @app.get("/api/oauth/codex/status")
    def codex_oauth_status(config: Annotated[AppConfig, Depends(get_config)]) -> dict:
        service = CodexOAuthService(config.config_dir)
        state = service.pending_state()
        return {"oauth": service.public_state(state) if state else None}

    @app.post("/api/oauth/codex/callback-url")
    def submit_codex_oauth_callback(
        request: CodexOAuthCallbackRequest,
        config: Annotated[AppConfig, Depends(get_config)],
    ) -> dict:
        service = CodexOAuthService(config.config_dir)
        try:
            state = service.submit_callback_url(request.login_id, request.callback_url)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return {"oauth": service.public_state(state)}

    @app.post("/api/oauth/codex/complete")
    def complete_codex_oauth(
        request: CodexOAuthCompleteRequest,
        config: Annotated[AppConfig, Depends(get_config)],
    ) -> dict:
        store = LlmAccountStore(config.config_dir)
        service = CodexOAuthService(config.config_dir)
        try:
            result = service.complete_login(request.login_id)
            account = store.create_account(
                name="Codex OAuth",
                provider_type="codex_local_access",
                base_url=UPSTREAM_CODEX_BASE_URL,
                model="gpt-5.4",
                api_key=result.tokens.access_token,
                enabled=True,
                priority=90,
                weight=1,
                credential_payload={
                    "refresh_token": result.tokens.refresh_token,
                    "id_token": result.tokens.id_token,
                    "expires_in": result.tokens.expires_in,
                    "token_type": result.tokens.token_type,
                },
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return {
            "account": public_account(account),
            "tokens": public_token_payload(result.tokens),
        }

    @app.get("/auth/callback")
    def codex_oauth_callback(
        config: Annotated[AppConfig, Depends(get_config)],
        code: str | None = None,
        state: str | None = None,
    ) -> HTMLResponse:
        if not code or not state:
            raise HTTPException(status_code=400, detail="Missing OAuth code or state")
        try:
            CodexOAuthService(config.config_dir).submit_callback_params(state, code)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return HTMLResponse(authorized_callback_html().decode("utf-8"))

    @app.get("/api/llm/accounts")
    def llm_accounts(config: Annotated[AppConfig, Depends(get_config)]) -> dict:
        store = LlmAccountStore(config.config_dir)
        return {
            "accounts": [public_account(account) for account in store.list_accounts()],
            "usage": asdict(store.usage_summary()),
        }

    @app.post("/api/llm/accounts")
    def create_llm_account(
        request: LlmAccountCreateRequest,
        config: Annotated[AppConfig, Depends(get_config)],
    ) -> dict:
        store = LlmAccountStore(config.config_dir)
        try:
            account = store.create_account(
                name=request.name,
                provider_type=request.provider_type,
                base_url=request.base_url,
                model=request.model,
                api_key=request.api_key,
                enabled=request.enabled,
                priority=request.priority,
                weight=request.weight,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return {"account": public_account(account)}

    @app.post("/api/llm/import-token")
    def import_llm_token(
        request: TokenImportRequest,
        config: Annotated[AppConfig, Depends(get_config)],
    ) -> dict:
        try:
            parsed = parse_token_import_payload(request.payload)
            access_token = parsed["access_token"]
            refresh_token = parsed["refresh_token"]
            if not access_token and parsed["refresh_token"]:
                refreshed = exchange_refresh_token(parsed["refresh_token"])
                access_token = refreshed.access_token
                refresh_token = refreshed.refresh_token or parsed["refresh_token"]
            if not access_token:
                raise ValueError("Could not find accessToken, apiKey, or refresh_token.")
            account = LlmAccountStore(config.config_dir).create_account(
                name=parsed["name"],
                provider_type="codex_local_access",
                base_url=parsed["base_url"],
                model=parsed["model"],
                api_key=access_token,
                enabled=True,
                priority=90,
                weight=1,
                credential_payload={"refresh_token": refresh_token},
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return {"account": public_account(account)}

    @app.post("/api/llm/import-external")
    def import_external_llm_accounts(
        request: ExternalImportRequest,
        config: Annotated[AppConfig, Depends(get_config)],
    ) -> dict:
        try:
            payload = import_payload_from_request(request)
            account_specs = parse_external_import_payload(payload, request.provider_type)
            store = LlmAccountStore(config.config_dir)
            accounts = [
                store.create_account(
                    name=spec["name"],
                    provider_type=spec["provider_type"],
                    base_url=spec["base_url"],
                    model=spec["model"],
                    api_key=spec["api_key"],
                    enabled=spec["enabled"],
                    priority=spec["priority"],
                    weight=spec["weight"],
                    credential_payload=spec.get("credential_payload"),
                )
                for spec in account_specs
            ]
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return {
            "accounts": [public_account(account) for account in accounts],
            "count": len(accounts),
        }

    @app.patch("/api/llm/accounts/{account_id}")
    def update_llm_account(
        account_id: str,
        request: LlmAccountUpdateRequest,
        config: Annotated[AppConfig, Depends(get_config)],
    ) -> dict:
        store = LlmAccountStore(config.config_dir)
        updates = request.model_dump(exclude_unset=True)
        try:
            account = store.update_account(account_id, updates)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        if account is None:
            raise HTTPException(status_code=404, detail="LLM account not found")
        return {"account": public_account(account)}

    @app.delete("/api/llm/accounts/{account_id}")
    def delete_llm_account(
        account_id: str,
        config: Annotated[AppConfig, Depends(get_config)],
    ) -> dict:
        deleted = LlmAccountStore(config.config_dir).delete_account(account_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="LLM account not found")
        return {"deleted": True}

    @app.post("/api/llm/accounts/{account_id}/test")
    def test_llm_account(
        account_id: str,
        config: Annotated[AppConfig, Depends(get_config)],
    ) -> dict:
        store = LlmAccountStore(config.config_dir)
        account = store.get_account(account_id)
        if account is None:
            raise HTTPException(status_code=404, detail="LLM account not found")
        result = LlmAccessService(store).test_account(account)
        return {"result": asdict(result), "account": public_account(store.get_account(account_id))}

    @app.get("/api/llm/usage")
    def llm_usage(config: Annotated[AppConfig, Depends(get_config)]) -> dict:
        return {"usage": asdict(LlmAccountStore(config.config_dir).usage_summary())}

    @app.get("/api/fuel-pool")
    def fuel_pool_status(
        config: Annotated[AppConfig, Depends(get_config)],
    ) -> dict:
        store = LlmAccountStore(config.config_dir)
        status = FuelPoolService(
            store, strategy=store.get_setting("fuel_strategy") or "first_available"
        ).status()
        return {
            "status": status,
            "usage": asdict(store.usage_summary()),
        }

    @app.patch("/api/fuel-pool")
    def update_fuel_pool(
        request: FuelPoolUpdateRequest,
        config: Annotated[AppConfig, Depends(get_config)],
    ) -> dict:
        store = LlmAccountStore(config.config_dir)
        if request.strategy is not None:
            if request.strategy not in POOL_STRATEGIES:
                raise HTTPException(status_code=400, detail="Unknown fuel pool strategy")
            store.set_setting("fuel_strategy", request.strategy)
        return fuel_pool_status(config)

    return app


app = create_app()


MAX_IMPORT_PAYLOAD_BYTES = 1024 * 1024


def read_goal_doc() -> str:
    if not GOAL_DOC.exists():
        return "# /goal\n\nProject goal document has not been created yet."
    return GOAL_DOC.read_text(encoding="utf-8")


def render_goal_html(goal_markdown: str) -> str:
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>AI Knowledge Agent /goal</title>
    <style>
      body {{
        margin: 0;
        background: #f5f7fb;
        color: #172033;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }}
      main {{
        max-width: 920px;
        margin: 0 auto;
        padding: 40px 20px 64px;
      }}
      a {{
        color: #2457d6;
      }}
      .top {{
        display: flex;
        justify-content: space-between;
        gap: 16px;
        align-items: center;
        margin-bottom: 20px;
      }}
      .top a {{
        border: 1px solid #ccd6e6;
        border-radius: 8px;
        padding: 8px 12px;
        background: #ffffff;
        text-decoration: none;
        font-size: 14px;
      }}
      pre {{
        white-space: pre-wrap;
        overflow-wrap: anywhere;
        border: 1px solid #dbe3ef;
        border-radius: 8px;
        background: #ffffff;
        padding: 22px;
        line-height: 1.6;
        font: 15px/1.65 ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
        box-shadow: 0 16px 40px rgba(23, 32, 51, 0.08);
      }}
    </style>
  </head>
  <body>
    <main>
      <div class="top">
        <strong>AI Knowledge Agent /goal</strong>
        <a href="/">Back to app</a>
      </div>
      <pre>{escape(goal_markdown)}</pre>
    </main>
  </body>
</html>"""


def parse_token_import_payload(raw: str) -> dict[str, str]:
    text = raw.strip()
    if not text:
        raise ValueError("Import payload is empty.")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {
            "access_token": text,
            "refresh_token": "",
            "name": "Token import",
            "base_url": UPSTREAM_CODEX_BASE_URL,
            "model": "gpt-5.4",
        }
    if not isinstance(parsed, dict):
        raise ValueError("Token import JSON must be an object.")
    access_token = pick_string(
        parsed,
        "accessToken",
        "access_token",
        "apiKey",
        "api_key",
        "key",
        "token",
        "session_token",
        "sessionToken",
    ) or pick_nested_string(parsed, ("tokens", "auth"), "accessToken", "access_token")
    refresh_token = pick_string(parsed, "refreshToken", "refresh_token") or pick_nested_string(
        parsed,
        ("tokens", "auth"),
        "refreshToken",
        "refresh_token",
    )
    return {
        "access_token": access_token or "",
        "refresh_token": refresh_token or "",
        "name": pick_string(parsed, "name", "email", "account") or "Token import",
        "base_url": pick_string(parsed, "base_url", "baseUrl") or UPSTREAM_CODEX_BASE_URL,
        "model": pick_string(parsed, "model") or "gpt-5.4",
    }


def import_payload_from_request(request: ExternalImportRequest) -> str:
    if request.url and request.url.strip():
        return fetch_import_url(request.url.strip())
    if request.payload and request.payload.strip():
        return request.payload
    raise ValueError("Paste import JSON or enter an import URL.")


def fetch_import_url(url: str) -> str:
    parsed_url = urlparse(url)
    if parsed_url.scheme not in {"http", "https"}:
        raise ValueError("Import URL must start with http:// or https://.")
    try:
        request = Request(url, headers={"Accept": "application/json,text/plain,*/*"})
        with urlopen(request, timeout=15) as response:
            payload = response.read(MAX_IMPORT_PAYLOAD_BYTES + 1)
    except (OSError, TimeoutError, URLError) as error:
        raise ValueError("Could not fetch the import URL.") from error
    if len(payload) > MAX_IMPORT_PAYLOAD_BYTES:
        raise ValueError("Import payload is too large.")
    return payload.decode("utf-8", errors="replace")


def parse_external_import_payload(raw: str, provider_type_hint: str = "auto") -> list[dict]:
    text = raw.strip()
    if not text:
        raise ValueError("Import payload is empty.")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return [account_spec_from_token(parse_token_import_payload(text))]

    candidates = import_candidates(parsed)
    if not candidates:
        raise ValueError("Import JSON does not contain any account items.")
    return [account_spec_from_import_item(item, provider_type_hint) for item in candidates]


def import_candidates(parsed: object) -> list[object]:
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        for key in ("accounts", "items", "data", "providers"):
            value = parsed.get(key)
            if isinstance(value, list):
                return value
        return [parsed]
    raise ValueError("Import JSON must be an object or an array.")


def account_spec_from_token(parsed: dict[str, str]) -> dict:
    api_key = parsed["access_token"]
    refresh_token = parsed["refresh_token"]
    if not api_key and parsed["refresh_token"]:
        refreshed = exchange_refresh_token(parsed["refresh_token"])
        api_key = refreshed.access_token
        refresh_token = refreshed.refresh_token or parsed["refresh_token"]
    if not api_key:
        raise ValueError("Import item is missing accessToken, apiKey, or refresh_token.")
    return {
        "name": parsed["name"],
        "provider_type": "codex_local_access",
        "base_url": parsed["base_url"],
        "model": parsed["model"],
        "api_key": api_key,
        "enabled": True,
        "priority": 90,
        "weight": 1,
        "credential_payload": {"refresh_token": refresh_token},
    }


def account_spec_from_import_item(item: object, provider_type_hint: str = "auto") -> dict:
    if isinstance(item, str):
        return account_spec_from_token(parse_token_import_payload(item))
    if not isinstance(item, dict):
        raise ValueError("Import account items must be objects.")

    base_url = pick_string(item, "base_url", "baseUrl", "api_base", "apiBase", "endpoint")
    provider_type = normalize_provider_type(
        pick_string(item, "provider_type", "providerType", "provider", "type"),
        provider_type_hint,
        base_url,
        has_session_token_fields(item),
    )
    api_key = normalize_secret(
        pick_string(
            item,
            "apiKey",
            "api_key",
            "key",
            "token",
            "accessToken",
            "access_token",
            "session_token",
            "sessionToken",
            "authorization",
            "Authorization",
        )
        or pick_nested_string(
            item,
            ("tokens", "auth", "credentials"),
            "apiKey",
            "api_key",
            "accessToken",
            "access_token",
            "token",
        )
    )
    refresh_token = pick_string(item, "refreshToken", "refresh_token") or pick_nested_string(
        item,
        ("tokens", "auth", "credentials"),
        "refreshToken",
        "refresh_token",
    )
    if not api_key and refresh_token:
        refreshed = exchange_refresh_token(refresh_token)
        api_key = refreshed.access_token
        refresh_token = refreshed.refresh_token or refresh_token
    if not api_key:
        raise ValueError("Import item is missing accessToken, apiKey, or refresh_token.")
    if not base_url:
        if provider_type == "codex_local_access":
            base_url = UPSTREAM_CODEX_BASE_URL
        else:
            raise ValueError("Import item is missing base_url.")

    return {
        "name": pick_string(item, "name", "email", "account", "label") or "Imported account",
        "provider_type": provider_type,
        "base_url": base_url,
        "model": pick_string(item, "model") or default_model_for_provider(provider_type),
        "api_key": api_key,
        "enabled": bool_from_item(item, "enabled", default=True),
        "priority": int_from_item(item, "priority", default=90, minimum=0, maximum=1000),
        "weight": int_from_item(item, "weight", default=1, minimum=1, maximum=100),
        "credential_payload": {"refresh_token": refresh_token},
    }


def normalize_provider_type(
    raw_type: str | None,
    hint: str,
    base_url: str | None,
    has_session_token: bool = False,
) -> str:
    chosen = hint if hint and hint != "auto" else raw_type
    aliases = {
        "openai": "openai_compatible",
        "openai-compatible": "openai_compatible",
        "openai_compatible": "openai_compatible",
        "api": "openai_compatible",
        "local": "local_relay",
        "relay": "local_relay",
        "local_relay": "local_relay",
        "sub2api": "local_relay",
        "codex": "codex_local_access",
        "chatgpt": "codex_local_access",
        "codex_local_access": "codex_local_access",
    }
    normalized = aliases.get((chosen or "").strip().lower())
    if normalized:
        return normalized
    if base_url and "chatgpt.com/backend-api/codex" in base_url:
        return "codex_local_access"
    if has_session_token and not base_url:
        return "codex_local_access"
    return "openai_compatible"


def normalize_secret(secret: str | None) -> str | None:
    if not secret:
        return None
    cleaned = secret.strip()
    if cleaned.lower().startswith("bearer "):
        return cleaned[7:].strip()
    return cleaned


def default_model_for_provider(provider_type: str) -> str:
    return "gpt-5.4" if provider_type == "codex_local_access" else "gpt-4o-mini"


def has_session_token_fields(item: dict) -> bool:
    return bool(
        pick_string(
            item,
            "accessToken",
            "access_token",
            "refreshToken",
            "refresh_token",
            "session_token",
            "sessionToken",
        )
        or pick_nested_string(
            item,
            ("tokens", "auth", "credentials"),
            "accessToken",
            "access_token",
            "refreshToken",
            "refresh_token",
        )
    )


def bool_from_item(item: dict, key: str, default: bool) -> bool:
    value = item.get(key)
    return value if isinstance(value, bool) else default


def int_from_item(
    item: dict,
    key: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    value = item.get(key)
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def pick_string(data: dict, *keys: str) -> str | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def pick_nested_string(data: dict, containers: tuple[str, ...], *keys: str) -> str | None:
    for container in containers:
        value = data.get(container)
        if isinstance(value, dict):
            found = pick_string(value, *keys)
            if found:
                return found
    return None
