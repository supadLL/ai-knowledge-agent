from ai_knowledge_agent.codex_oauth import CodexOAuthTokens
from ai_knowledge_agent.fuel_pool import FuelPoolService
from ai_knowledge_agent.llm_access import LlmAccountStore


def test_fuel_pool_selects_first_available_by_priority(tmp_path):
    store = LlmAccountStore(tmp_path / "config")
    low = store.create_account(
        name="Low priority",
        provider_type="local_relay",
        base_url="http://127.0.0.1:1455/v1",
        model="gpt-low",
        priority=200,
    )
    high = store.create_account(
        name="High priority",
        provider_type="openai_compatible",
        base_url="https://api.example.com/v1",
        model="gpt-high",
        priority=10,
    )

    selected = FuelPoolService(store).select_account()

    assert selected is not None
    assert selected.id == high.id
    assert selected.id != low.id


def test_fuel_pool_skips_cooling_accounts(tmp_path):
    store = LlmAccountStore(tmp_path / "config")
    cooling = store.create_account(
        name="Cooling",
        provider_type="local_relay",
        base_url="http://127.0.0.1:1455/v1",
        model="gpt-cooling",
        priority=1,
    )
    fallback = store.create_account(
        name="Fallback",
        provider_type="local_relay",
        base_url="http://127.0.0.1:1456/v1",
        model="gpt-fallback",
        priority=10,
    )
    store.mark_dispatch_failure(cooling.id, "rate limited", cooldown_ms=60_000)

    selected = FuelPoolService(store).select_account()

    assert selected is not None
    assert selected.id == fallback.id


def test_fuel_pool_uses_codex_reverse_proxy(tmp_path, monkeypatch):
    store = LlmAccountStore(tmp_path / "config")
    account = store.create_account(
        name="Codex OAuth",
        provider_type="codex_local_access",
        base_url="https://chatgpt.com/backend-api/codex",
        model="gpt-5.4",
        api_key="access-token",
    )

    def fake_forward(payload, *, access_token, base_url, timeout_seconds):
        assert payload["model"] == "gpt-5.4"
        assert access_token == "access-token"
        assert base_url == "https://chatgpt.com/backend-api/codex"
        return type(
            "Result",
            (),
            {
                "response": {
                    "choices": [{"message": {"content": "proxied"}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
                },
                "latency_ms": 12,
            },
        )()

    monkeypatch.setattr("ai_knowledge_agent.fuel_pool.forward_codex_chat_completion", fake_forward)

    result = FuelPoolService(store).forward_chat_completion(
        {"model": "gpt-5.4", "messages": [{"role": "user", "content": "hello"}]}
    )

    assert result.account_id == account.id
    assert result.response["choices"][0]["message"]["content"] == "proxied"
    assert store.get_account(account.id).last_error is None


def test_fuel_pool_refreshes_codex_token_before_forwarding(tmp_path, monkeypatch):
    store = LlmAccountStore(tmp_path / "config")
    account = store.create_account(
        name="Codex OAuth",
        provider_type="codex_local_access",
        base_url="https://chatgpt.com/backend-api/codex",
        model="gpt-5.4",
        api_key="stale-access-token",
        credential_payload={"refresh_token": "refresh-token"},
    )

    def fake_refresh(refresh_token: str) -> CodexOAuthTokens:
        assert refresh_token == "refresh-token"
        return CodexOAuthTokens(
            access_token="fresh-access-token",
            refresh_token="next-refresh-token",
        )

    def fake_forward(payload, *, access_token, base_url, timeout_seconds):
        assert access_token == "fresh-access-token"
        return type(
            "Result",
            (),
            {
                "response": {
                    "choices": [{"message": {"content": "fresh"}}],
                    "usage": {"total_tokens": 1},
                },
                "latency_ms": 5,
            },
        )()

    monkeypatch.setattr("ai_knowledge_agent.codex_oauth.exchange_refresh_token", fake_refresh)
    monkeypatch.setattr("ai_knowledge_agent.fuel_pool.forward_codex_chat_completion", fake_forward)

    result = FuelPoolService(store).forward_chat_completion(
        {"model": "gpt-5.4", "messages": [{"role": "user", "content": "hello"}]}
    )
    updated = store.get_account(account.id)

    assert result.response["choices"][0]["message"]["content"] == "fresh"
    assert updated.api_key == "fresh-access-token"
    assert store.credentials_for_account(updated)["refresh_token"] == "next-refresh-token"
