import sqlite3

from ai_knowledge_agent.llm_access import (
    LlmAccessService,
    LlmAccountStore,
    mask_secret,
    public_account,
    redact_known_secret,
)


def test_llm_account_crud_masks_secret(tmp_path):
    store = LlmAccountStore(tmp_path / "config")

    account = store.create_account(
        name="Local relay",
        provider_type="local_relay",
        base_url="http://127.0.0.1:1455/v1/",
        model="gpt-test",
        api_key="secret-token-1234",
        credential_payload={"refresh_token": "refresh-secret-token"},
    )
    listed = store.list_accounts()
    public = public_account(listed[0])
    raw_secret_payload = sqlite3.connect(store.path).execute(
        "SELECT credential_payload FROM llm_accounts WHERE id = ?",
        (account.id,),
    ).fetchone()[0]

    assert account.base_url == "http://127.0.0.1:1455/v1"
    assert len(listed) == 1
    assert public["api_key_masked"] == "secr...1234"
    assert public["has_refresh_credentials"]
    assert "api_key" not in public
    assert "credential_payload" not in public
    assert "refresh-secret-token" not in raw_secret_payload
    assert store.credentials_for_account(account)["refresh_token"] == "refresh-secret-token"

    updated = store.update_account(account.id, {"enabled": False, "model": "gpt-next"})

    assert updated is not None
    assert not updated.enabled
    assert updated.model == "gpt-next"
    assert store.delete_account(account.id)
    assert store.list_accounts() == []


def test_llm_usage_summary(tmp_path):
    store = LlmAccountStore(tmp_path / "config")
    account = store.create_account(
        name="API",
        provider_type="openai_compatible",
        base_url="https://api.example.com/v1",
        model="gpt-test",
        api_key="key",
    )

    store.record_usage(
        account_id=account.id,
        operation="ask",
        model=account.model,
        prompt_tokens=7,
        completion_tokens=5,
        total_tokens=12,
        latency_ms=120,
        success=True,
    )
    store.record_usage(
        account_id=account.id,
        operation="test",
        model=account.model,
        latency_ms=20,
        success=False,
        error="bad\nsecret-key",
    )

    summary = store.usage_summary()

    assert summary.request_count == 2
    assert summary.success_count == 1
    assert summary.failure_count == 1
    assert summary.total_tokens == 12
    assert summary.average_latency_ms == 70

    assert store.delete_account(account.id)
    assert store.usage_summary().request_count == 0


def test_mask_secret_handles_short_and_empty_values():
    assert mask_secret("") == ""
    assert mask_secret("short") == "****"
    assert mask_secret("abcdefghi") == "abcd...fghi"


def test_redact_known_secret_masks_provider_error_text():
    assert (
        redact_known_secret("Authorization failed for secret-token-1234", "secret-token-1234")
        == "Authorization failed for secr...1234"
    )


def test_codex_account_health_check_uses_internal_proxy(tmp_path, monkeypatch):
    store = LlmAccountStore(tmp_path / "config")
    account = store.create_account(
        name="Codex",
        provider_type="codex_local_access",
        base_url="https://chatgpt.com/backend-api/codex",
        model="gpt-5.4",
        api_key="access-token",
    )

    def fake_forward(payload, *, access_token, base_url, timeout_seconds):
        assert payload["messages"][0]["role"] == "system"
        assert access_token == "access-token"
        assert base_url == "https://chatgpt.com/backend-api/codex"
        assert timeout_seconds == 20
        return type(
            "Result",
            (),
            {
                "response": {
                    "choices": [{"message": {"content": "ok"}}],
                    "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3},
                },
                "latency_ms": 9,
            },
        )()

    monkeypatch.setattr("ai_knowledge_agent.codex_proxy.forward_codex_chat_completion", fake_forward)

    result = LlmAccessService(store).test_account(account)

    assert result.ok
    assert result.message == "ok"
    assert store.usage_summary().total_tokens == 3


def test_codex_account_health_check_refreshes_before_proxy_call(tmp_path, monkeypatch):
    from ai_knowledge_agent.codex_oauth import CodexOAuthTokens

    store = LlmAccountStore(tmp_path / "config")
    account = store.create_account(
        name="Codex",
        provider_type="codex_local_access",
        base_url="https://chatgpt.com/backend-api/codex",
        model="gpt-5.4",
        api_key="stale-access-token",
        credential_payload={"refresh_token": "refresh-token", "id_token": "existing-id-token"},
    )

    def fake_exchange_refresh_token(refresh_token, current_id_token=None):
        assert refresh_token == "refresh-token"
        assert current_id_token == "existing-id-token"
        return CodexOAuthTokens(
            access_token="fresh-access-token",
            refresh_token="next-refresh-token",
            expires_in=3600,
            token_type="Bearer",
        )

    def fake_forward(payload, *, access_token, base_url, timeout_seconds):
        assert payload["model"] == "gpt-5.4"
        assert access_token == "fresh-access-token"
        assert base_url == "https://chatgpt.com/backend-api/codex"
        assert timeout_seconds == 20
        return type(
            "Result",
            (),
            {
                "response": {
                    "choices": [{"message": {"content": "ok"}}],
                    "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3},
                },
                "latency_ms": 9,
            },
        )()

    monkeypatch.setattr("ai_knowledge_agent.codex_oauth.exchange_refresh_token", fake_exchange_refresh_token)
    monkeypatch.setattr("ai_knowledge_agent.codex_proxy.forward_codex_chat_completion", fake_forward)

    result = LlmAccessService(store).test_account(account)
    refreshed = store.get_account(account.id)

    assert result.ok
    assert refreshed is not None
    assert refreshed.api_key == "fresh-access-token"
    assert store.credentials_for_account(refreshed)["refresh_token"] == "next-refresh-token"
