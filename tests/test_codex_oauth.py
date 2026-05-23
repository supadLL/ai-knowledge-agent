from ai_knowledge_agent.codex_oauth import (
    CLIENT_ID,
    CodexOAuthService,
    CodexOAuthTokens,
    authorized_callback_html,
    code_challenge,
)


def test_codex_oauth_builds_pkce_login(tmp_path):
    service = CodexOAuthService(tmp_path / "config")

    state = service.start_login(start_listener=False)

    assert state.login_id
    assert state.redirect_uri == "http://localhost:1455/auth/callback"
    assert f"client_id={CLIENT_ID}" in state.auth_url
    assert "code_challenge_method=S256" in state.auth_url
    assert code_challenge(state.code_verifier) in state.auth_url


def test_codex_oauth_manual_callback_verifies_state(tmp_path):
    service = CodexOAuthService(tmp_path / "config")
    state = service.start_login(start_listener=False)

    updated = service.submit_callback_url(
        state.login_id,
        f"http://localhost:1455/auth/callback?code=abc123&state={state.state}",
    )

    assert updated.code == "abc123"


def test_codex_oauth_complete_exchanges_token(tmp_path, monkeypatch):
    service = CodexOAuthService(tmp_path / "config")
    state = service.start_login(start_listener=False)
    service.submit_callback_params(state.state, "callback-code")

    def fake_exchange(code: str, verifier: str, redirect_uri: str) -> CodexOAuthTokens:
        assert code == "callback-code"
        assert verifier == state.code_verifier
        assert redirect_uri == state.redirect_uri
        return CodexOAuthTokens(access_token="access-token", id_token="id-token")

    monkeypatch.setattr("ai_knowledge_agent.codex_oauth.exchange_code_for_token", fake_exchange)

    result = service.complete_login(state.login_id)

    assert result.tokens.access_token == "access-token"
    assert service.pending_state() is None


def test_codex_oauth_callback_page_notifies_and_closes():
    html = authorized_callback_html().decode("utf-8")

    assert "ai-knowledge-agent.oauth-callback" in html
    assert "window.close()" in html
