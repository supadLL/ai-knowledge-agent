from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .codex_proxy import UPSTREAM_CODEX_BASE_URL, forward_codex_chat_completion
from .generation import GenerationProvider, answer_from_context, build_context
from .llm_access import (
    LlmAccount,
    LlmAccountStore,
    build_headers,
    extract_chat_message,
    extract_usage,
    public_account,
    redact_known_secret,
)
from .models import RetrievalResult


POOL_STRATEGIES = {
    "first_available": "First available",
    "round_robin": "Round robin",
    "least_used": "Least used",
    "priority_weighted": "Priority weighted",
}


@dataclass(frozen=True)
class FuelDispatchResult:
    account_id: str
    account_name: str
    provider_type: str
    model: str
    response: dict[str, Any]
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class FuelPoolService:
    def __init__(self, store: LlmAccountStore, strategy: str = "first_available") -> None:
        self.store = store
        self.strategy = strategy if strategy in POOL_STRATEGIES else "first_available"

    def status(self) -> dict[str, Any]:
        accounts = self.store.list_accounts()
        active = [account for account in accounts if self._is_available(account)]
        return {
            "strategy": self.strategy,
            "strategies": [
                {"id": strategy_id, "label": label}
                for strategy_id, label in POOL_STRATEGIES.items()
            ],
            "enabled_accounts": sum(1 for account in accounts if account.enabled),
            "available_accounts": len(active),
            "accounts": [public_account(account) for account in accounts],
        }

    def select_account(self, model: str | None = None) -> LlmAccount | None:
        candidates = [
            account
            for account in self.store.list_accounts()
            if self._is_available(account)
        ]
        if not candidates:
            return None
        if self.strategy == "round_robin":
            return min(candidates, key=lambda account: account.last_used_at or 0)
        if self.strategy == "least_used":
            totals = self.store.account_token_totals()
            return min(candidates, key=lambda account: (totals.get(account.id, 0), account.priority))
        if self.strategy == "priority_weighted":
            return sorted(
                candidates,
                key=lambda account: (account.priority, -account.weight, account.last_used_at or 0),
            )[0]
        return sorted(candidates, key=lambda account: (account.priority, account.created_at))[0]

    def forward_chat_completion(
        self,
        payload: dict[str, Any],
        *,
        operation: str = "internal",
        timeout_seconds: int = 90,
    ) -> FuelDispatchResult:
        requested_model = str(payload.get("model") or "").strip() or None
        account = self.select_account(requested_model)
        if account is None:
            raise RuntimeError("No available Fuel Pool account. Add or enable an LLM account first.")
        outbound = dict(payload)
        outbound["model"] = requested_model or account.model
        started = int(time.time() * 1000)
        if account.provider_type == "codex_local_access":
            try:
                account = self._refresh_codex_account_if_possible(account)
                result = forward_codex_chat_completion(
                    outbound,
                    access_token=account.api_key,
                    base_url=account.base_url or UPSTREAM_CODEX_BASE_URL,
                    timeout_seconds=timeout_seconds,
                )
                usage = extract_usage(result.response)
                self.store.mark_dispatch_success(account.id)
                self.store.record_usage(
                    account_id=account.id,
                    operation=operation,
                    model=outbound["model"],
                    prompt_tokens=usage["prompt_tokens"],
                    completion_tokens=usage["completion_tokens"],
                    total_tokens=usage["total_tokens"],
                    latency_ms=result.latency_ms,
                    success=True,
                )
                return FuelDispatchResult(
                    account_id=account.id,
                    account_name=account.name,
                    provider_type=account.provider_type,
                    model=outbound["model"],
                    response=result.response,
                    latency_ms=result.latency_ms,
                    prompt_tokens=usage["prompt_tokens"],
                    completion_tokens=usage["completion_tokens"],
                    total_tokens=usage["total_tokens"],
                )
            except (RuntimeError, ValueError) as error:
                raise self._record_failure(
                    account,
                    operation,
                    outbound["model"],
                    int(time.time() * 1000) - started,
                    str(error),
                ) from error
        request = urllib.request.Request(
            f"{account.base_url}/chat/completions",
            data=json.dumps(outbound).encode("utf-8"),
            headers=build_headers(account.api_key),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
            usage = extract_usage(body)
            latency_ms = int(time.time() * 1000) - started
            self.store.mark_dispatch_success(account.id)
            self.store.record_usage(
                account_id=account.id,
                operation=operation,
                model=outbound["model"],
                prompt_tokens=usage["prompt_tokens"],
                completion_tokens=usage["completion_tokens"],
                total_tokens=usage["total_tokens"],
                latency_ms=latency_ms,
                success=True,
            )
            return FuelDispatchResult(
                account_id=account.id,
                account_name=account.name,
                provider_type=account.provider_type,
                model=outbound["model"],
                response=body,
                latency_ms=latency_ms,
                prompt_tokens=usage["prompt_tokens"],
                completion_tokens=usage["completion_tokens"],
                total_tokens=usage["total_tokens"],
            )
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise self._record_failure(
                account,
                operation,
                outbound["model"],
                int(time.time() * 1000) - started,
                f"HTTP {error.code}: {detail}",
            ) from error
        except (OSError, TimeoutError, ValueError, urllib.error.URLError) as error:
            raise self._record_failure(
                account,
                operation,
                outbound["model"],
                int(time.time() * 1000) - started,
                str(error),
            ) from error

    def _record_failure(
        self, account: LlmAccount, operation: str, model: str, latency_ms: int, error: str
    ) -> RuntimeError:
        safe_error = redact_known_secret(error, account.api_key) or "Fuel Pool dispatch failed."
        self.store.mark_dispatch_failure(account.id, safe_error)
        self.store.record_usage(
            account_id=account.id,
            operation=operation,
            model=model,
            latency_ms=latency_ms,
            success=False,
            error=safe_error,
        )
        return RuntimeError(safe_error)

    def _is_available(self, account: LlmAccount) -> bool:
        now_ms = int(time.time() * 1000)
        return account.enabled and (
            account.cooldown_until is None or account.cooldown_until <= now_ms
        )

    def _refresh_codex_account_if_possible(self, account: LlmAccount) -> LlmAccount:
        credentials = self.store.credentials_for_account(account)
        refresh_token = str(credentials.get("refresh_token") or "").strip()
        if not refresh_token:
            return account

        from .codex_oauth import exchange_refresh_token

        tokens = exchange_refresh_token(refresh_token)
        next_credentials = dict(credentials)
        if tokens.refresh_token:
            next_credentials["refresh_token"] = tokens.refresh_token
        if tokens.id_token:
            next_credentials["id_token"] = tokens.id_token
        if tokens.expires_in:
            next_credentials["expires_in"] = tokens.expires_in
        if tokens.token_type:
            next_credentials["token_type"] = tokens.token_type
        updated = self.store.update_account_secret(
            account.id,
            api_key=tokens.access_token,
            credential_payload=next_credentials,
        )
        return updated or account

class FuelPoolGenerationProvider:
    name = "fuel-pool"

    def __init__(
        self,
        fuel_pool: FuelPoolService,
        context_char_budget: int = 6000,
    ) -> None:
        self.fuel_pool = fuel_pool
        self.context_char_budget = context_char_budget

    def generate(self, question: str, results: list[RetrievalResult]) -> str:
        if not results:
            return answer_from_context(question, results)
        context = build_context(results, self.context_char_budget)
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Answer only from the provided local context. "
                        "Cite sources using the exact [filename#index] labels. "
                        "If the context is insufficient, say so plainly."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Question:\n{question}\n\nLocal context:\n{context}",
                },
            ],
            "temperature": 0.2,
        }
        dispatch = self.fuel_pool.forward_chat_completion(payload, operation="ask")
        message = extract_chat_message(dispatch.response)
        if message is None:
            raise RuntimeError("Fuel Pool response did not contain choices[0].message.content.")
        return message


def fuel_pool_generation_provider(
    store: LlmAccountStore, context_char_budget: int
) -> GenerationProvider | None:
    if not any(account.enabled for account in store.list_accounts()):
        return None
    return FuelPoolGenerationProvider(
        FuelPoolService(
            store, strategy=store.get_setting("fuel_strategy") or "first_available"
        ),
        context_char_budget=context_char_budget,
    )
