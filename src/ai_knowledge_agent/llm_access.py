from __future__ import annotations

import json
import sqlite3
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .credentials import has_sealed_credentials, seal_json_payload, unseal_json_payload


APP_DB_FILE = "app.db"
PROVIDER_TYPES = {
    "openai_compatible": "OpenAI-compatible API",
    "local_relay": "Upstream relay / sub2api",
    "codex_local_access": "Codex account relay",
}
ACCOUNT_SELECT_COLUMNS = """
id, name, provider_type, base_url, model, api_key, credential_payload, enabled,
created_at, updated_at, priority, weight, cooldown_until,
consecutive_failures, last_used_at, last_test_at, last_error
"""


@dataclass(frozen=True)
class LlmAccount:
    id: str
    name: str
    provider_type: str
    base_url: str
    model: str
    api_key: str
    credential_payload: str
    enabled: bool
    created_at: int
    updated_at: int
    priority: int = 100
    weight: int = 1
    cooldown_until: int | None = None
    consecutive_failures: int = 0
    last_used_at: int | None = None
    last_test_at: int | None = None
    last_error: str | None = None


@dataclass(frozen=True)
class LlmUsageEvent:
    id: str
    account_id: str | None
    operation: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    success: bool
    error: str | None
    created_at: int


@dataclass(frozen=True)
class LlmUsageSummary:
    request_count: int
    success_count: int
    failure_count: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    average_latency_ms: int


@dataclass(frozen=True)
class LlmAccountTestResult:
    ok: bool
    latency_ms: int
    model: str
    message: str


def app_db_path(config_dir: Path) -> Path:
    return config_dir / APP_DB_FILE


def now_ms() -> int:
    return int(time.time() * 1000)


def mask_secret(secret: str | None) -> str:
    value = (secret or "").strip()
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}...{value[-4:]}"


def redact_error(error: str | None) -> str | None:
    if not error:
        return None
    return " ".join(error.replace("\r", " ").replace("\n", " ").split())[:500]


def redact_known_secret(text: str | None, secret: str | None) -> str | None:
    if not text:
        return text
    value = (secret or "").strip()
    if not value:
        return text
    return text.replace(value, mask_secret(value))


def public_account(account: LlmAccount) -> dict[str, Any]:
    data = asdict(account)
    data.pop("api_key", None)
    data.pop("credential_payload", None)
    data["api_key_masked"] = mask_secret(account.api_key)
    data["has_refresh_credentials"] = has_sealed_credentials(account.credential_payload)
    return data


class LlmAccountStore:
    def __init__(self, config_dir: Path) -> None:
        self.path = app_db_path(config_dir)

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            initialize_schema(connection)

    def list_accounts(self) -> list[LlmAccount]:
        self.initialize()
        with sqlite3.connect(self.path) as connection:
            rows = connection.execute(
                """
                SELECT
                    """ + ACCOUNT_SELECT_COLUMNS + """
                FROM llm_accounts
                ORDER BY created_at DESC
                """
            )
            return [account_from_row(row) for row in rows]

    def get_account(self, account_id: str) -> LlmAccount | None:
        self.initialize()
        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                """
                SELECT
                    """ + ACCOUNT_SELECT_COLUMNS + """
                FROM llm_accounts
                WHERE id = ?
                """,
                (account_id,),
            ).fetchone()
            return account_from_row(row) if row else None

    def first_enabled_account(self) -> LlmAccount | None:
        self.initialize()
        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                """
                SELECT
                    """ + ACCOUNT_SELECT_COLUMNS + """
                FROM llm_accounts
                WHERE enabled = 1 AND (cooldown_until IS NULL OR cooldown_until <= ?)
                ORDER BY priority ASC, updated_at DESC
                LIMIT 1
                """,
                (now_ms(),),
            ).fetchone()
            return account_from_row(row) if row else None

    def create_account(
        self,
        *,
        name: str,
        provider_type: str,
        base_url: str,
        model: str,
        api_key: str = "",
        enabled: bool = True,
        priority: int = 100,
        weight: int = 1,
        credential_payload: dict[str, Any] | None = None,
    ) -> LlmAccount:
        validate_provider_type(provider_type)
        timestamp = now_ms()
        account = LlmAccount(
            id=str(uuid.uuid4()),
            name=required_text(name, "name"),
            provider_type=provider_type,
            base_url=normalize_base_url(base_url),
            model=required_text(model, "model"),
            api_key=api_key.strip(),
            credential_payload=seal_json_payload(credential_payload),
            enabled=enabled,
            created_at=timestamp,
            updated_at=timestamp,
            priority=normalize_int(priority, 0, 1000),
            weight=normalize_int(weight, 1, 100),
        )
        self.initialize()
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                INSERT INTO llm_accounts (
                    id, name, provider_type, base_url, model, api_key, credential_payload, enabled,
                    created_at, updated_at, priority, weight, cooldown_until,
                    consecutive_failures, last_used_at, last_test_at, last_error
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    account.id,
                    account.name,
                    account.provider_type,
                    account.base_url,
                    account.model,
                    account.api_key,
                    account.credential_payload,
                    int(account.enabled),
                    account.created_at,
                    account.updated_at,
                    account.priority,
                    account.weight,
                    account.cooldown_until,
                    account.consecutive_failures,
                    account.last_used_at,
                    account.last_test_at,
                    account.last_error,
                ),
            )
        return account

    def update_account(self, account_id: str, updates: dict[str, Any]) -> LlmAccount | None:
        account = self.get_account(account_id)
        if account is None:
            return None

        provider_type = value_or_existing(updates.get("provider_type"), account.provider_type)
        validate_provider_type(provider_type)
        api_key = value_or_existing(updates.get("api_key"), account.api_key)
        enabled = account.enabled if updates.get("enabled") is None else bool(updates["enabled"])
        priority = normalize_int(updates.get("priority", account.priority), 0, 1000)
        weight = normalize_int(updates.get("weight", account.weight), 1, 100)
        next_account = LlmAccount(
            id=account.id,
            name=required_text(value_or_existing(updates.get("name"), account.name), "name"),
            provider_type=provider_type,
            base_url=normalize_base_url(value_or_existing(updates.get("base_url"), account.base_url)),
            model=required_text(value_or_existing(updates.get("model"), account.model), "model"),
            api_key=api_key.strip(),
            credential_payload=account.credential_payload,
            enabled=enabled,
            created_at=account.created_at,
            updated_at=now_ms(),
            priority=priority,
            weight=weight,
            cooldown_until=account.cooldown_until,
            consecutive_failures=account.consecutive_failures,
            last_used_at=account.last_used_at,
            last_test_at=account.last_test_at,
            last_error=account.last_error,
        )

        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                UPDATE llm_accounts
                SET name = ?, provider_type = ?, base_url = ?, model = ?, api_key = ?,
                    enabled = ?, priority = ?, weight = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    next_account.name,
                    next_account.provider_type,
                    next_account.base_url,
                    next_account.model,
                    next_account.api_key,
                    int(next_account.enabled),
                    next_account.priority,
                    next_account.weight,
                    next_account.updated_at,
                    next_account.id,
                ),
            )
        return next_account

    def delete_account(self, account_id: str) -> bool:
        self.initialize()
        with sqlite3.connect(self.path) as connection:
            cursor = connection.execute("DELETE FROM llm_accounts WHERE id = ?", (account_id,))
            if cursor.rowcount > 0:
                connection.execute(
                    "DELETE FROM llm_usage_events WHERE account_id = ?",
                    (account_id,),
                )
            return cursor.rowcount > 0

    def credentials_for_account(self, account: LlmAccount | str) -> dict[str, Any]:
        if isinstance(account, str):
            loaded = self.get_account(account)
            return unseal_json_payload(loaded.credential_payload if loaded else "")
        return unseal_json_payload(account.credential_payload)

    def update_account_secret(
        self,
        account_id: str,
        *,
        api_key: str | None = None,
        credential_payload: dict[str, Any] | None = None,
    ) -> LlmAccount | None:
        account = self.get_account(account_id)
        if account is None:
            return None
        next_api_key = account.api_key if api_key is None else api_key.strip()
        next_payload = (
            account.credential_payload
            if credential_payload is None
            else seal_json_payload(credential_payload)
        )
        timestamp = now_ms()
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                UPDATE llm_accounts
                SET api_key = ?, credential_payload = ?, updated_at = ?
                WHERE id = ?
                """,
                (next_api_key, next_payload, timestamp, account_id),
            )
        return self.get_account(account_id)

    def mark_test_result(self, account_id: str, error: str | None) -> LlmAccount | None:
        timestamp = now_ms()
        safe_error = redact_error(error)
        self.initialize()
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                UPDATE llm_accounts
                SET last_test_at = ?, last_error = ?, updated_at = ?
                WHERE id = ?
                """,
                (timestamp, safe_error, timestamp, account_id),
            )
        return self.get_account(account_id)

    def mark_dispatch_success(self, account_id: str) -> None:
        timestamp = now_ms()
        self.initialize()
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                UPDATE llm_accounts
                SET last_used_at = ?, consecutive_failures = 0, cooldown_until = NULL,
                    last_error = NULL, updated_at = ?
                WHERE id = ?
                """,
                (timestamp, timestamp, account_id),
            )

    def mark_dispatch_failure(
        self, account_id: str, error: str, cooldown_ms: int = 60_000
    ) -> None:
        timestamp = now_ms()
        safe_error = redact_error(error)
        self.initialize()
        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                "SELECT consecutive_failures FROM llm_accounts WHERE id = ?",
                (account_id,),
            ).fetchone()
            failures = int(row[0] or 0) + 1 if row else 1
            connection.execute(
                """
                UPDATE llm_accounts
                SET consecutive_failures = ?, cooldown_until = ?, last_error = ?, updated_at = ?
                WHERE id = ?
                """,
                (failures, timestamp + cooldown_ms * failures, safe_error, timestamp, account_id),
            )

    def record_usage(
        self,
        *,
        account_id: str | None,
        operation: str,
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        latency_ms: int = 0,
        success: bool = True,
        error: str | None = None,
    ) -> LlmUsageEvent:
        event = LlmUsageEvent(
            id=str(uuid.uuid4()),
            account_id=account_id,
            operation=operation,
            model=model,
            prompt_tokens=max(0, prompt_tokens),
            completion_tokens=max(0, completion_tokens),
            total_tokens=max(0, total_tokens),
            latency_ms=max(0, latency_ms),
            success=success,
            error=redact_error(error),
            created_at=now_ms(),
        )
        self.initialize()
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                INSERT INTO llm_usage_events (
                    id, account_id, operation, model, prompt_tokens, completion_tokens,
                    total_tokens, latency_ms, success, error, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.account_id,
                    event.operation,
                    event.model,
                    event.prompt_tokens,
                    event.completion_tokens,
                    event.total_tokens,
                    event.latency_ms,
                    int(event.success),
                    event.error,
                    event.created_at,
                ),
            )
        return event

    def usage_summary(self) -> LlmUsageSummary:
        self.initialize()
        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                """
                SELECT COUNT(*), SUM(success), SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END),
                       SUM(prompt_tokens), SUM(completion_tokens), SUM(total_tokens),
                       AVG(latency_ms)
                FROM llm_usage_events
                """
            ).fetchone()
        request_count = int(row[0] or 0)
        return LlmUsageSummary(
            request_count=request_count,
            success_count=int(row[1] or 0),
            failure_count=int(row[2] or 0),
            prompt_tokens=int(row[3] or 0),
            completion_tokens=int(row[4] or 0),
            total_tokens=int(row[5] or 0),
            average_latency_ms=int(row[6] or 0),
        )

    def account_token_totals(self) -> dict[str, int]:
        self.initialize()
        with sqlite3.connect(self.path) as connection:
            rows = connection.execute(
                """
                SELECT account_id, SUM(total_tokens)
                FROM llm_usage_events
                WHERE account_id IS NOT NULL
                GROUP BY account_id
                """
            )
            return {row[0]: int(row[1] or 0) for row in rows}

    def get_setting(self, key: str) -> str | None:
        self.initialize()
        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                "SELECT value FROM fuel_pool_settings WHERE key = ?",
                (key,),
            ).fetchone()
            return str(row[0]) if row else None

    def set_setting(self, key: str, value: str) -> None:
        self.initialize()
        timestamp = now_ms()
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                INSERT INTO fuel_pool_settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (key, value, timestamp),
            )

class LlmAccessService:
    def __init__(self, store: LlmAccountStore) -> None:
        self.store = store

    def test_account(self, account: LlmAccount, timeout_seconds: int = 20) -> LlmAccountTestResult:
        started = now_ms()
        payload = {
            "model": account.model,
            "messages": [
                {"role": "system", "content": "Reply with a short health-check message."},
                {"role": "user", "content": "Say OK for this local knowledge-agent test."},
            ],
            "temperature": 0,
            "max_tokens": 16,
        }
        if account.provider_type == "codex_local_access":
            return self._test_codex_account(account, payload, started, timeout_seconds)
        request = urllib.request.Request(
            f"{account.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=build_headers(account.api_key),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
            message = extract_chat_message(body) or "Provider returned a response."
            usage = extract_usage(body)
            latency_ms = now_ms() - started
            self.store.mark_test_result(account.id, None)
            self.store.record_usage(
                account_id=account.id,
                operation="test",
                model=account.model,
                prompt_tokens=usage["prompt_tokens"],
                completion_tokens=usage["completion_tokens"],
                total_tokens=usage["total_tokens"],
                latency_ms=latency_ms,
                success=True,
            )
            return LlmAccountTestResult(True, latency_ms, account.model, message)
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            return self._failure(account, started, f"HTTP {error.code}: {detail}")
        except (OSError, TimeoutError, ValueError, urllib.error.URLError) as error:
            return self._failure(account, started, str(error))

    def _failure(self, account: LlmAccount, started: int, error: str) -> LlmAccountTestResult:
        latency_ms = now_ms() - started
        safe_error = redact_error(redact_known_secret(error, account.api_key)) or "Provider test failed."
        self.store.mark_test_result(account.id, safe_error)
        self.store.record_usage(
            account_id=account.id,
            operation="test",
            model=account.model,
            latency_ms=latency_ms,
            success=False,
            error=safe_error,
        )
        return LlmAccountTestResult(False, latency_ms, account.model, safe_error)

    def _test_codex_account(
        self,
        account: LlmAccount,
        payload: dict[str, Any],
        started: int,
        timeout_seconds: int,
    ) -> LlmAccountTestResult:
        try:
            from .codex_accounts import refresh_codex_account_if_possible
            from .codex_proxy import forward_codex_chat_completion

            account = refresh_codex_account_if_possible(self.store, account)
            result = forward_codex_chat_completion(
                payload,
                access_token=account.api_key,
                base_url=account.base_url,
                timeout_seconds=timeout_seconds,
            )
            message = extract_chat_message(result.response) or "Provider returned a response."
            usage = extract_usage(result.response)
            self.store.mark_test_result(account.id, None)
            self.store.record_usage(
                account_id=account.id,
                operation="test",
                model=account.model,
                prompt_tokens=usage["prompt_tokens"],
                completion_tokens=usage["completion_tokens"],
                total_tokens=usage["total_tokens"],
                latency_ms=result.latency_ms,
                success=True,
            )
            return LlmAccountTestResult(True, result.latency_ms, account.model, message)
        except (RuntimeError, ValueError, OSError, TimeoutError, urllib.error.URLError) as error:
            return self._failure(account, started, str(error))


def initialize_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_accounts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            provider_type TEXT NOT NULL,
            base_url TEXT NOT NULL,
            model TEXT NOT NULL,
            api_key TEXT NOT NULL DEFAULT '',
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            last_test_at INTEGER,
            last_error TEXT
        )
        """
    )
    ensure_column(connection, "llm_accounts", "priority", "INTEGER NOT NULL DEFAULT 100")
    ensure_column(connection, "llm_accounts", "credential_payload", "TEXT NOT NULL DEFAULT ''")
    ensure_column(connection, "llm_accounts", "weight", "INTEGER NOT NULL DEFAULT 1")
    ensure_column(connection, "llm_accounts", "cooldown_until", "INTEGER")
    ensure_column(
        connection,
        "llm_accounts",
        "consecutive_failures",
        "INTEGER NOT NULL DEFAULT 0",
    )
    ensure_column(connection, "llm_accounts", "last_used_at", "INTEGER")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_usage_events (
            id TEXT PRIMARY KEY,
            account_id TEXT,
            operation TEXT NOT NULL,
            model TEXT NOT NULL,
            prompt_tokens INTEGER NOT NULL DEFAULT 0,
            completion_tokens INTEGER NOT NULL DEFAULT 0,
            total_tokens INTEGER NOT NULL DEFAULT 0,
            latency_ms INTEGER NOT NULL DEFAULT 0,
            success INTEGER NOT NULL DEFAULT 1,
            error TEXT,
            created_at INTEGER NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_llm_usage_events_created_at
        ON llm_usage_events(created_at)
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS fuel_pool_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at INTEGER NOT NULL
        )
        """
    )


def account_from_row(row: sqlite3.Row | tuple[Any, ...]) -> LlmAccount:
    return LlmAccount(
        id=row[0],
        name=row[1],
        provider_type=row[2],
        base_url=row[3],
        model=row[4],
        api_key=row[5],
        credential_payload=row[6] or "",
        enabled=bool(row[7]),
        created_at=row[8],
        updated_at=row[9],
        priority=row[10],
        weight=row[11],
        cooldown_until=row[12],
        consecutive_failures=row[13],
        last_used_at=row[14],
        last_test_at=row[15],
        last_error=row[16],
    )


def ensure_column(
    connection: sqlite3.Connection, table: str, column: str, definition: str
) -> None:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    if column not in {row[1] for row in rows}:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def validate_provider_type(provider_type: str) -> None:
    if provider_type not in PROVIDER_TYPES:
        raise ValueError(f"Unknown LLM provider type: {provider_type}")


def required_text(value: str, field_name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def value_or_existing(value: Any, existing: str) -> str:
    if value is None:
        return existing
    return str(value)


def normalize_int(value: Any, minimum: int, maximum: int) -> int:
    parsed = int(value)
    return max(minimum, min(maximum, parsed))


def normalize_base_url(value: str) -> str:
    base_url = required_text(value, "base_url").rstrip("/")
    if not (base_url.startswith("http://") or base_url.startswith("https://")):
        raise ValueError("base_url must start with http:// or https://")
    return base_url


def build_headers(api_key: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key.strip():
        headers["Authorization"] = f"Bearer {api_key.strip()}"
    return headers


def extract_chat_message(body: dict[str, Any]) -> str | None:
    try:
        return str(body["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError):
        return None


def extract_usage(body: dict[str, Any]) -> dict[str, int]:
    usage = body.get("usage") if isinstance(body, dict) else None
    if not isinstance(usage, dict):
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    prompt_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    completion_tokens = int(
        usage.get("completion_tokens") or usage.get("output_tokens") or 0
    )
    total_tokens = int(usage.get("total_tokens") or prompt_tokens + completion_tokens)
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }
