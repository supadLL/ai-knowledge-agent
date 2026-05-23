import json
import urllib.request

from ai_knowledge_agent.codex_proxy import (
    build_responses_body,
    build_chat_completion_payload,
    forward_codex_chat_completion,
    parse_sse_response,
)


def test_build_responses_body_from_chat_completions():
    body, model, _ = build_responses_body(
        {
            "model": "gpt-5.4",
            "messages": [
                {"role": "system", "content": "Use local context."},
                {"role": "user", "content": "hello"},
            ],
        }
    )

    assert model == "gpt-5.4"
    assert body["stream"] is True
    assert body["input"][0]["role"] == "developer"
    assert body["input"][1]["content"][0]["text"] == "hello"


def test_parse_sse_response_and_build_chat_payload():
    response = parse_sse_response(
        """event: response.output_text.delta
data: {"type":"response.output_text.delta","delta":"hello "}

event: response.output_text.delta
data: {"type":"response.output_text.delta","delta":"world"}

event: response.completed
data: {"type":"response.completed","response":{"id":"resp_1","created_at":123,"model":"gpt-5.4","status":"completed","usage":{"input_tokens":2,"output_tokens":3,"total_tokens":5}}}

"""
    )
    payload = build_chat_completion_payload(response, "gpt-5.4", {})

    assert payload["choices"][0]["message"]["content"] == "hello world"
    assert payload["usage"]["total_tokens"] == 5


def test_forward_codex_chat_completion_posts_to_upstream(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

        def read(self):
            return json.dumps(
                {
                    "id": "resp_json",
                    "model": "gpt-5.4",
                    "output": [
                        {
                            "type": "message",
                            "role": "assistant",
                            "content": [{"type": "output_text", "text": "ok"}],
                        }
                    ],
                    "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
                }
            ).encode("utf-8")

    def fake_urlopen(request: urllib.request.Request, timeout: int):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    result = forward_codex_chat_completion(
        {"model": "gpt-5.4", "messages": [{"role": "user", "content": "hello"}]},
        access_token="access-token",
    )

    assert captured["url"] == "https://chatgpt.com/backend-api/codex/responses"
    assert captured["headers"]["Authorization"] == "Bearer access-token"
    assert captured["body"]["input"][0]["content"][0]["text"] == "hello"
    assert result.response["choices"][0]["message"]["content"] == "ok"
