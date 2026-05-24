from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from ai_knowledge_agent.codex_oauth import CodexOAuthTokens
from ai_knowledge_agent.config import AppConfig
from ai_knowledge_agent.web import create_app, get_config


def test_web_stats_and_ask_flow(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "note.md").write_text("Citations use filename and chunk index.", encoding="utf-8")
    config = AppConfig(
        data_dir=tmp_path,
        raw_dir=raw_dir,
        index_dir=tmp_path / "index",
        config_dir=tmp_path / "config",
        logs_dir=tmp_path / "logs",
    )
    app = create_app()
    app.dependency_overrides[get_config] = lambda: config
    client = TestClient(app)

    index_response = client.post("/api/index", json={"source": str(raw_dir)})
    ask_response = client.post("/api/ask", json={"question": "How do citations work?"})
    stats_response = client.get("/api/stats")
    documents_response = client.get("/api/documents")

    assert index_response.status_code == 200
    assert ask_response.status_code == 200
    assert stats_response.json()["indexed_chunks"] == 1
    assert documents_response.json()["documents"][0]["filename"] == "note.md"
    assert ask_response.json()["sources"][0]["filename"] == "note.md"


def test_web_goal_routes_are_available(tmp_path):
    config = AppConfig(
        data_dir=tmp_path,
        raw_dir=tmp_path / "raw",
        index_dir=tmp_path / "index",
        config_dir=tmp_path / "config",
        logs_dir=tmp_path / "logs",
    )
    app = create_app()
    app.dependency_overrides[get_config] = lambda: config
    client = TestClient(app)

    page_response = client.get("/goal")
    api_response = client.get("/api/goal")

    assert page_response.status_code == 200
    assert "/goal: AI Knowledge Agent Final Goal" in page_response.text
    assert api_response.status_code == 200
    assert "local-first AI knowledge workspace" in api_response.json()["goal"]


def test_web_document_source_registry_flow(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "note.md").write_text("Saved sources can be reindexed.", encoding="utf-8")
    config = AppConfig(
        data_dir=tmp_path,
        raw_dir=raw_dir,
        index_dir=tmp_path / "index",
        config_dir=tmp_path / "config",
        logs_dir=tmp_path / "logs",
    )
    app = create_app()
    app.dependency_overrides[get_config] = lambda: config
    client = TestClient(app)

    create_response = client.post(
        "/api/document-sources",
        json={"path": str(raw_dir), "label": "Notes"},
    )
    source = create_response.json()["source"]
    list_response = client.get("/api/document-sources")
    index_response = client.post(f"/api/document-sources/{source['id']}/index")
    delete_response = client.delete(f"/api/document-sources/{source['id']}")

    assert create_response.status_code == 200
    assert source["label"] == "Notes"
    assert source["path"] == str(raw_dir.resolve())
    assert list_response.json()["sources"][0]["id"] == source["id"]
    assert index_response.status_code == 200
    assert index_response.json()["index"]["chunk_count"] == 1
    assert index_response.json()["source"]["last_chunk_count"] == 1
    assert delete_response.status_code == 200
    assert client.get("/api/document-sources").json()["sources"] == []


def test_web_document_source_auto_index_flow(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "note.md").write_text("Auto index watches local notes.", encoding="utf-8")
    config = AppConfig(
        data_dir=tmp_path,
        raw_dir=raw_dir,
        index_dir=tmp_path / "index",
        config_dir=tmp_path / "config",
        logs_dir=tmp_path / "logs",
    )
    app = create_app()
    app.dependency_overrides[get_config] = lambda: config
    client = TestClient(app)

    create_response = client.post("/api/document-sources", json={"path": str(raw_dir)})
    source = create_response.json()["source"]
    scan_response = client.post("/api/auto-index/scan")
    disable_response = client.patch(
        f"/api/document-sources/{source['id']}/auto-index",
        json={"enabled": False},
    )
    status_response = client.get("/api/auto-index")

    assert create_response.status_code == 200
    assert source["auto_index_enabled"]
    assert source["last_chunk_count"] == 1
    assert scan_response.status_code == 200
    assert not scan_response.json()["results"][0]["changed"]
    assert disable_response.json()["source"]["auto_index_enabled"] is False
    assert status_response.json()["enabled_sources"] == 0


def test_web_indexed_document_delete_and_reindex(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    note = raw_dir / "note.md"
    other = raw_dir / "other.md"
    note.write_text("First note content.", encoding="utf-8")
    other.write_text("Other note content.", encoding="utf-8")
    config = AppConfig(
        data_dir=tmp_path,
        raw_dir=raw_dir,
        index_dir=tmp_path / "index",
        config_dir=tmp_path / "config",
        logs_dir=tmp_path / "logs",
    )
    app = create_app()
    app.dependency_overrides[get_config] = lambda: config
    client = TestClient(app)

    client.post("/api/index", json={"source": str(raw_dir)})
    documents = client.get("/api/documents").json()["documents"]
    note_doc = next(document for document in documents if document["filename"] == "note.md")
    other_doc = next(document for document in documents if document["filename"] == "other.md")
    note.write_text("Updated note content.", encoding="utf-8")
    reindex_response = client.post(f"/api/documents/{note_doc['id']}/index")
    delete_response = client.delete(f"/api/documents/{other_doc['id']}")
    next_documents = client.get("/api/documents").json()["documents"]

    assert reindex_response.status_code == 200
    assert reindex_response.json()["chunk_count"] == 1
    assert delete_response.status_code == 200
    assert [document["filename"] for document in next_documents] == ["note.md"]


def test_web_eval_results_lists_history(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "note.md").write_text("Chunks store filename and chunk index.", encoding="utf-8")
    questions = tmp_path / "questions.json"
    questions.write_text(
        '[{"question":"What do chunks store?","source_doc":"note.md"}]',
        encoding="utf-8",
    )
    config = AppConfig(
        data_dir=tmp_path,
        raw_dir=raw_dir,
        index_dir=tmp_path / "index",
        config_dir=tmp_path / "config",
        logs_dir=tmp_path / "logs",
    )
    app = create_app()
    app.dependency_overrides[get_config] = lambda: config
    client = TestClient(app)

    client.post("/api/index", json={"source": str(raw_dir)})
    client.post("/api/eval", json={"questions_path": str(questions)})
    response = client.get("/api/eval/results")

    assert response.status_code == 200
    assert response.json()["results"][0]["case_count"] == 1
    assert "comparison" in response.json()["results"][0]


def test_web_llm_account_flow(tmp_path):
    config = AppConfig(
        data_dir=tmp_path,
        raw_dir=tmp_path / "raw",
        index_dir=tmp_path / "index",
        config_dir=tmp_path / "config",
        logs_dir=tmp_path / "logs",
    )
    app = create_app()
    app.dependency_overrides[get_config] = lambda: config
    client = TestClient(app)

    providers_response = client.get("/api/llm/providers")
    create_response = client.post(
        "/api/llm/accounts",
        json={
            "name": "Codex gateway",
            "provider_type": "codex_local_access",
            "base_url": "http://127.0.0.1:1455/v1",
            "model": "gpt-5.4",
            "api_key": "local-secret-token",
        },
    )
    account = create_response.json()["account"]
    list_response = client.get("/api/llm/accounts")
    patch_response = client.patch(
        f"/api/llm/accounts/{account['id']}",
        json={"enabled": False},
    )
    usage_response = client.get("/api/llm/usage")

    assert providers_response.status_code == 200
    assert create_response.status_code == 200
    assert account["api_key_masked"] == "loca...oken"
    assert "api_key" not in account
    assert list_response.json()["accounts"][0]["name"] == "Codex gateway"
    assert not patch_response.json()["account"]["enabled"]
    assert usage_response.json()["usage"]["request_count"] == 0

    delete_response = client.delete(f"/api/llm/accounts/{account['id']}")

    assert delete_response.status_code == 200
    assert client.get("/api/llm/accounts").json()["accounts"] == []


def test_web_fuel_pool_status_and_strategy(tmp_path):
    config = AppConfig(
        data_dir=tmp_path,
        raw_dir=tmp_path / "raw",
        index_dir=tmp_path / "index",
        config_dir=tmp_path / "config",
        logs_dir=tmp_path / "logs",
    )
    app = create_app()
    app.dependency_overrides[get_config] = lambda: config
    client = TestClient(app)
    client.post(
        "/api/llm/accounts",
        json={
            "name": "Relay",
            "provider_type": "local_relay",
            "base_url": "http://127.0.0.1:1455/v1",
            "model": "gpt-test",
            "api_key": "fuel-secret-token",
        },
    )

    status_response = client.get("/api/fuel-pool")
    update_response = client.patch("/api/fuel-pool", json={"strategy": "round_robin"})

    assert status_response.status_code == 200
    account = status_response.json()["status"]["accounts"][0]
    assert "api_key" not in account
    assert account["api_key_masked"] == "fuel...oken"
    assert update_response.json()["status"]["strategy"] == "round_robin"
    assert "relay" not in status_response.json()


def test_web_codex_oauth_import_creates_masked_account(tmp_path, monkeypatch):
    config = AppConfig(
        data_dir=tmp_path,
        raw_dir=tmp_path / "raw",
        index_dir=tmp_path / "index",
        config_dir=tmp_path / "config",
        logs_dir=tmp_path / "logs",
    )
    app = create_app()
    app.dependency_overrides[get_config] = lambda: config
    client = TestClient(app)

    def fake_exchange(code: str, verifier: str, redirect_uri: str) -> CodexOAuthTokens:
        return CodexOAuthTokens(
            access_token=f"access-{code}",
            id_token="id-token",
            refresh_token="refresh-token",
        )

    monkeypatch.setattr("ai_knowledge_agent.codex_oauth.CodexOAuthService._try_start_listener", lambda self, state: "manual")
    monkeypatch.setattr("ai_knowledge_agent.codex_oauth.exchange_code_for_token", fake_exchange)

    start_response = client.post("/api/oauth/codex/start")
    oauth = start_response.json()["oauth"]
    state = parse_qs(urlparse(oauth["auth_url"]).query)["state"][0]
    callback_response = client.post(
        "/api/oauth/codex/callback-url",
        json={
            "login_id": oauth["login_id"],
            "callback_url": f"{oauth['redirect_uri']}?code=ok-code&state={state}",
        },
    )
    complete_response = client.post(
        "/api/oauth/codex/complete",
        json={"login_id": oauth["login_id"]},
    )

    assert start_response.status_code == 200
    assert callback_response.status_code == 200
    account = complete_response.json()["account"]
    assert account["provider_type"] == "codex_local_access"
    assert account["api_key_masked"] == "acce...code"
    assert account["has_refresh_credentials"]
    assert "api_key" not in account


def test_web_token_import_accepts_raw_token(tmp_path):
    config = AppConfig(
        data_dir=tmp_path,
        raw_dir=tmp_path / "raw",
        index_dir=tmp_path / "index",
        config_dir=tmp_path / "config",
        logs_dir=tmp_path / "logs",
    )
    app = create_app()
    app.dependency_overrides[get_config] = lambda: config
    client = TestClient(app)

    response = client.post("/api/llm/import-token", json={"payload": "raw-access-token"})

    assert response.status_code == 200
    account = response.json()["account"]
    assert account["name"] == "Token import"
    assert account["provider_type"] == "codex_local_access"
    assert account["base_url"] == "https://chatgpt.com/backend-api/codex"
    assert account["api_key_masked"] == "raw-...oken"
    assert not account["has_refresh_credentials"]


def test_web_token_import_refreshes_refresh_token(tmp_path, monkeypatch):
    config = AppConfig(
        data_dir=tmp_path,
        raw_dir=tmp_path / "raw",
        index_dir=tmp_path / "index",
        config_dir=tmp_path / "config",
        logs_dir=tmp_path / "logs",
    )
    app = create_app()
    app.dependency_overrides[get_config] = lambda: config
    client = TestClient(app)

    def fake_refresh(refresh_token: str) -> CodexOAuthTokens:
        assert refresh_token == "refresh-token"
        return CodexOAuthTokens(access_token="access-from-refresh")

    monkeypatch.setattr("ai_knowledge_agent.web.exchange_refresh_token", fake_refresh)

    response = client.post(
        "/api/llm/import-token",
        json={"payload": '{"refresh_token":"refresh-token","email":"me@example.com"}'},
    )

    assert response.status_code == 200
    account = response.json()["account"]
    assert account["name"] == "me@example.com"
    assert account["api_key_masked"] == "acce...resh"
    assert account["has_refresh_credentials"]


def test_web_external_import_accepts_account_array(tmp_path):
    config = AppConfig(
        data_dir=tmp_path,
        raw_dir=tmp_path / "raw",
        index_dir=tmp_path / "index",
        config_dir=tmp_path / "config",
        logs_dir=tmp_path / "logs",
    )
    app = create_app()
    app.dependency_overrides[get_config] = lambda: config
    client = TestClient(app)

    response = client.post(
        "/api/llm/import-external",
        json={
            "provider_type": "local_relay",
            "payload": """
            {
              "accounts": [
                {
                  "name": "Sub2API",
                  "base_url": "https://gateway.example/v1",
                  "api_key": "relay-secret-token",
                  "model": "gpt-5.4",
                  "priority": 70,
                  "weight": 3
                }
              ]
            }
            """,
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["count"] == 1
    account = result["accounts"][0]
    assert account["name"] == "Sub2API"
    assert account["provider_type"] == "local_relay"
    assert account["api_key_masked"] == "rela...oken"
    assert "api_key" not in account


def test_web_external_import_accepts_raw_codex_token(tmp_path):
    config = AppConfig(
        data_dir=tmp_path,
        raw_dir=tmp_path / "raw",
        index_dir=tmp_path / "index",
        config_dir=tmp_path / "config",
        logs_dir=tmp_path / "logs",
    )
    app = create_app()
    app.dependency_overrides[get_config] = lambda: config
    client = TestClient(app)

    response = client.post(
        "/api/llm/import-external",
        json={"payload": "raw-codex-token"},
    )

    assert response.status_code == 200
    account = response.json()["accounts"][0]
    assert account["provider_type"] == "codex_local_access"
    assert account["base_url"] == "https://chatgpt.com/backend-api/codex"


def test_web_external_import_infers_codex_json_token(tmp_path):
    config = AppConfig(
        data_dir=tmp_path,
        raw_dir=tmp_path / "raw",
        index_dir=tmp_path / "index",
        config_dir=tmp_path / "config",
        logs_dir=tmp_path / "logs",
    )
    app = create_app()
    app.dependency_overrides[get_config] = lambda: config
    client = TestClient(app)

    response = client.post(
        "/api/llm/import-external",
        json={"payload": '{"accessToken":"json-codex-token","email":"codex@example.com"}'},
    )

    assert response.status_code == 200
    account = response.json()["accounts"][0]
    assert account["name"] == "codex@example.com"
    assert account["provider_type"] == "codex_local_access"
    assert account["base_url"] == "https://chatgpt.com/backend-api/codex"
