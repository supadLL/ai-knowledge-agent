from __future__ import annotations

import base64
import hashlib
import json
import secrets
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from .llm_access import app_db_path, mask_secret, now_ms, redact_error


CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
AUTH_ENDPOINT = "https://auth.openai.com/oauth/authorize"
TOKEN_ENDPOINT = "https://auth.openai.com/oauth/token"
SCOPES = "openid profile email offline_access api.connectors.read api.connectors.invoke"
ORIGINATOR = "codex_vscode"
DEFAULT_CALLBACK_PORT = 1455
OAUTH_TIMEOUT_SECONDS = 300


@dataclass(frozen=True)
class CodexOAuthState:
    login_id: str
    auth_url: str
    redirect_uri: str
    code_verifier: str
    state: str
    port: int
    expires_at: int
    code: str | None = None
    callback_mode: str = "manual"


@dataclass(frozen=True)
class CodexOAuthTokens:
    access_token: str
    id_token: str = ""
    refresh_token: str | None = None
    expires_in: int | None = None
    token_type: str | None = None


@dataclass(frozen=True)
class CodexOAuthCompleteResult:
    tokens: CodexOAuthTokens
    token_payload: dict[str, Any]


class CodexOAuthService:
    def __init__(self, config_dir: Path, callback_port: int = DEFAULT_CALLBACK_PORT) -> None:
        self.path = app_db_path(config_dir)
        self.callback_port = callback_port

    def start_login(self, start_listener: bool = True) -> CodexOAuthState:
        existing = self.pending_state()
        if existing and existing.expires_at > now_seconds() and existing.code is None:
            if start_listener:
                callback_mode = self._try_start_listener(existing)
                if callback_mode != existing.callback_mode:
                    existing = self._save_state(replace_state(existing, callback_mode=callback_mode))
            return existing

        code_verifier = token_urlsafe()
        state_token = token_urlsafe()
        redirect_uri = f"http://localhost:{self.callback_port}/auth/callback"
        state = CodexOAuthState(
            login_id=token_urlsafe(),
            auth_url=build_auth_url(
                redirect_uri=redirect_uri,
                code_challenge=code_challenge(code_verifier),
                state=state_token,
            ),
            redirect_uri=redirect_uri,
            code_verifier=code_verifier,
            state=state_token,
            port=self.callback_port,
            expires_at=now_seconds() + OAUTH_TIMEOUT_SECONDS,
            callback_mode="manual",
        )
        self._save_state(state)
        if start_listener:
            state = self._save_state(
                replace_state(state, callback_mode=self._try_start_listener(state))
            )
        return state

    def pending_state(self, login_id: str | None = None) -> CodexOAuthState | None:
        self._initialize()
        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                """
                SELECT login_id, auth_url, redirect_uri, code_verifier, state, port,
                       expires_at, code, callback_mode
                FROM codex_oauth_pending
                ORDER BY created_at DESC
                LIMIT 1
                """
            ).fetchone()
        if not row:
            return None
        state = CodexOAuthState(
            login_id=row[0],
            auth_url=row[1],
            redirect_uri=row[2],
            code_verifier=row[3],
            state=row[4],
            port=int(row[5]),
            expires_at=int(row[6]),
            code=row[7],
            callback_mode=row[8] or "manual",
        )
        if state.expires_at <= now_seconds():
            self.clear_state(state.login_id)
            return None
        if login_id and state.login_id != login_id:
            return None
        return state

    def submit_callback_url(self, login_id: str, callback_url: str) -> CodexOAuthState:
        state = self.pending_state(login_id)
        if state is None:
            raise ValueError("OAuth login has expired or was not started.")
        parsed = urllib.parse.urlparse(callback_url.strip())
        query = urllib.parse.parse_qs(parsed.query)
        code = first_query_value(query, "code")
        incoming_state = first_query_value(query, "state")
        if not code:
            raise ValueError("Callback URL is missing code.")
        if incoming_state != state.state:
            raise ValueError("OAuth state mismatch.")
        return self._save_state(replace_state(state, code=code))

    def submit_callback_params(self, state_token: str, code: str) -> CodexOAuthState:
        state = self.pending_state()
        if state is None:
            raise ValueError("OAuth login has expired or was not started.")
        if state_token != state.state:
            raise ValueError("OAuth state mismatch.")
        if not code.strip():
            raise ValueError("Callback is missing code.")
        return self._save_state(replace_state(state, code=code.strip()))

    def complete_login(self, login_id: str) -> CodexOAuthCompleteResult:
        state = self.pending_state(login_id)
        if state is None:
            raise ValueError("OAuth login has expired or was not started.")
        if not state.code:
            raise ValueError("OAuth callback has not been received yet.")
        tokens = exchange_code_for_token(state.code, state.code_verifier, state.redirect_uri)
        self.clear_state(login_id)
        return CodexOAuthCompleteResult(
            tokens=tokens,
            token_payload={
                "provider": "codex_oauth",
                "access_token": tokens.access_token,
                "id_token": tokens.id_token,
                "refresh_token": tokens.refresh_token,
                "expires_in": tokens.expires_in,
                "token_type": tokens.token_type,
            },
        )

    def clear_state(self, login_id: str | None = None) -> None:
        self._initialize()
        with sqlite3.connect(self.path) as connection:
            if login_id:
                connection.execute("DELETE FROM codex_oauth_pending WHERE login_id = ?", (login_id,))
            else:
                connection.execute("DELETE FROM codex_oauth_pending")

    def public_state(self, state: CodexOAuthState) -> dict[str, Any]:
        data = asdict(state)
        data.pop("code_verifier", None)
        data.pop("state", None)
        data["has_callback_code"] = bool(state.code)
        data["expires_in"] = max(0, state.expires_at - now_seconds())
        data["callback_port"] = state.port
        data.pop("code", None)
        return data

    def _save_state(self, state: CodexOAuthState) -> CodexOAuthState:
        self._initialize()
        with sqlite3.connect(self.path) as connection:
            connection.execute("DELETE FROM codex_oauth_pending")
            connection.execute(
                """
                INSERT INTO codex_oauth_pending (
                    login_id, auth_url, redirect_uri, code_verifier, state, port,
                    expires_at, code, callback_mode, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    state.login_id,
                    state.auth_url,
                    state.redirect_uri,
                    state.code_verifier,
                    state.state,
                    state.port,
                    state.expires_at,
                    state.code,
                    state.callback_mode,
                    now_ms(),
                    now_ms(),
                ),
            )
        return state

    def _try_start_listener(self, state: CodexOAuthState) -> str:
        try:
            server = OAuthCallbackServer(("127.0.0.1", state.port), OAuthCallbackHandler, self.path)
        except OSError:
            return "manual"
        thread = threading.Thread(target=server.serve_until_callback, daemon=True)
        thread.start()
        return "local_listener"

    def _initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS codex_oauth_pending (
                    login_id TEXT PRIMARY KEY,
                    auth_url TEXT NOT NULL,
                    redirect_uri TEXT NOT NULL,
                    code_verifier TEXT NOT NULL,
                    state TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL,
                    code TEXT,
                    callback_mode TEXT NOT NULL DEFAULT 'manual',
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
                """
            )


class OAuthCallbackServer(HTTPServer):
    def __init__(self, address: tuple[str, int], handler: type[BaseHTTPRequestHandler], db_path: Path):
        super().__init__(address, handler)
        self.db_path = db_path
        self.timeout = 0.5
        self.stop_at = time.monotonic() + OAUTH_TIMEOUT_SECONDS
        self.completed = False

    def serve_until_callback(self) -> None:
        while not self.completed and time.monotonic() < self.stop_at:
            self.handle_request()
        self.server_close()


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    server: OAuthCallbackServer

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/auth/callback":
            self.send_response(404)
            self.end_headers()
            return
        query = urllib.parse.parse_qs(parsed.query)
        service = CodexOAuthService(self.server.db_path.parent)
        try:
            service.submit_callback_params(
                first_query_value(query, "state"),
                first_query_value(query, "code"),
            )
        except ValueError as error:
            self.send_response(400)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(str(error).encode("utf-8"))
            return

        self.server.completed = True
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(authorized_callback_html())

    def log_message(self, format: str, *args: Any) -> None:
        return


def token_urlsafe() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii").rstrip("=")


def code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def build_auth_url(*, redirect_uri: str, code_challenge: str, state: str) -> str:
    query = urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": CLIENT_ID,
            "redirect_uri": redirect_uri,
            "scope": SCOPES,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "id_token_add_organizations": "true",
            "codex_cli_simplified_flow": "true",
            "state": state,
            "originator": ORIGINATOR,
        }
    )
    return f"{AUTH_ENDPOINT}?{query}"


def exchange_code_for_token(code: str, code_verifier: str, redirect_uri: str) -> CodexOAuthTokens:
    body = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": CLIENT_ID,
            "code_verifier": code_verifier,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        TOKEN_ENDPOINT,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise ValueError(f"Token exchange failed: HTTP {error.code}, {redact_error(detail)}") from error
    except (OSError, ValueError, urllib.error.URLError) as error:
        raise ValueError(f"Token exchange failed: {redact_error(str(error))}") from error

    access_token = str(payload.get("access_token") or "").strip()
    id_token = str(payload.get("id_token") or "").strip()
    if not access_token or not id_token:
        raise ValueError("Token exchange response is missing access_token or id_token.")
    refresh_token = payload.get("refresh_token")
    return CodexOAuthTokens(
        access_token=access_token,
        id_token=id_token,
        refresh_token=str(refresh_token).strip() if refresh_token else None,
        expires_in=int(payload["expires_in"]) if payload.get("expires_in") else None,
        token_type=str(payload.get("token_type")) if payload.get("token_type") else None,
    )


def exchange_refresh_token(refresh_token: str, current_id_token: str | None = None) -> CodexOAuthTokens:
    body = json.dumps(
        {
            "client_id": CLIENT_ID,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        TOKEN_ENDPOINT,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise ValueError(f"Token refresh failed: HTTP {error.code}, {redact_error(detail)}") from error
    except (OSError, ValueError, urllib.error.URLError) as error:
        raise ValueError(f"Token refresh failed: {redact_error(str(error))}") from error

    access_token = str(payload.get("access_token") or "").strip()
    if not access_token:
        raise ValueError("Token refresh response is missing access_token.")
    id_token = str(payload.get("id_token") or current_id_token or "").strip()
    next_refresh_token = str(payload.get("refresh_token") or refresh_token).strip()
    return CodexOAuthTokens(
        access_token=access_token,
        id_token=id_token,
        refresh_token=next_refresh_token,
        expires_in=int(payload["expires_in"]) if payload.get("expires_in") else None,
        token_type=str(payload.get("token_type")) if payload.get("token_type") else None,
    )


def first_query_value(query: dict[str, list[str]], key: str) -> str:
    values = query.get(key)
    return values[0].strip() if values else ""


def now_seconds() -> int:
    return int(time.time())


def replace_state(state: CodexOAuthState, **updates: Any) -> CodexOAuthState:
    values = asdict(state)
    values.update(updates)
    return CodexOAuthState(**values)


def authorized_callback_html() -> bytes:
    return b"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Authorized</title>
  </head>
  <body style="font-family:system-ui;margin:48px">
    <h1>Authorized</h1>
    <p>AI Knowledge Agent is importing this account. This window will close automatically.</p>
    <p>If it stays open, you can close it and return to the app.</p>
    <script>
      (function () {
        try {
          if (window.opener) {
            window.opener.postMessage({ type: "ai-knowledge-agent.oauth-callback" }, "*");
          }
        } catch (error) {}
        window.setTimeout(function () {
          window.close();
        }, 900);
      })();
    </script>
  </body>
</html>"""


def public_token_payload(tokens: CodexOAuthTokens) -> dict[str, Any]:
    return {
        "access_token_masked": mask_secret(tokens.access_token),
        "id_token_masked": mask_secret(tokens.id_token),
        "refresh_token_masked": mask_secret(tokens.refresh_token),
        "expires_in": tokens.expires_in,
        "token_type": tokens.token_type,
    }
