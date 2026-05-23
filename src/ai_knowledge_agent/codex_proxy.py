from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .llm_access import build_headers


UPSTREAM_CODEX_BASE_URL = "https://chatgpt.com/backend-api/codex"
DEFAULT_CODEX_USER_AGENT = "AI Knowledge Agent Codex Local Proxy"
DEFAULT_CODEX_ORIGINATOR = "codex_vscode"


@dataclass(frozen=True)
class CodexProxyResult:
    response: dict[str, Any]
    latency_ms: int


def forward_codex_chat_completion(
    payload: dict[str, Any],
    *,
    access_token: str,
    base_url: str = UPSTREAM_CODEX_BASE_URL,
    timeout_seconds: int = 90,
) -> CodexProxyResult:
    started = int(time.time() * 1000)
    responses_body, requested_model, original_payload = build_responses_body(payload)
    upstream = post_codex_responses(
        responses_body,
        access_token=access_token,
        base_url=base_url,
        timeout_seconds=timeout_seconds,
    )
    parsed = parse_upstream_response(upstream)
    return CodexProxyResult(
        response=build_chat_completion_payload(parsed, requested_model, original_payload),
        latency_ms=int(time.time() * 1000) - started,
    )


def build_responses_body(payload: dict[str, Any]) -> tuple[dict[str, Any], str, dict[str, Any]]:
    model = str(payload.get("model") or "").strip()
    if not model:
        raise ValueError("model is required for Codex local proxy.")
    messages = payload.get("messages")
    if not isinstance(messages, list) or not messages:
        raise ValueError("messages is required for Codex local proxy.")
    stream = bool(payload.get("stream", False))
    if stream:
        raise ValueError("Codex local proxy streaming is not implemented yet.")

    body: dict[str, Any] = {
        "instructions": "",
        "stream": True,
        "store": False,
        "model": model,
        "input": normalize_chat_messages(messages),
        "parallel_tool_calls": True,
        "reasoning": {
            "effort": payload.get("reasoning_effort") or "medium",
            "summary": "auto",
        },
        "include": ["reasoning.encrypted_content"],
    }
    if "tools" in payload:
        body["tools"] = normalize_tools(payload["tools"])
    if "tool_choice" in payload:
        body["tool_choice"] = payload["tool_choice"]
    if "response_format" in payload:
        body["text"] = normalize_response_format(payload["response_format"])
    return body, model, dict(payload)


def normalize_chat_messages(messages: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role") or "user")
        if role == "tool":
            normalized.append(
                {
                    "type": "function_call_output",
                    "call_id": str(message.get("tool_call_id") or ""),
                    "output": content_text(message.get("content")),
                }
            )
            continue
        mapped_role = "developer" if role == "system" else role
        content = normalize_content(message.get("content"), role)
        if content:
            normalized.append(
                {
                    "type": "message",
                    "role": mapped_role,
                    "content": content,
                }
            )
        if role == "assistant":
            normalized.extend(normalize_tool_calls(message.get("tool_calls")))
    return normalized


def normalize_content(content: Any, role: str) -> list[dict[str, Any]]:
    if isinstance(content, list):
        parts = content
    else:
        parts = [content]
    normalized = []
    text_type = "output_text" if role == "assistant" else "input_text"
    for part in parts:
        if isinstance(part, str):
            normalized.append({"type": text_type, "text": part})
            continue
        if not isinstance(part, dict):
            continue
        part_type = str(part.get("type") or "text")
        if part_type == "text":
            normalized.append({"type": text_type, "text": str(part.get("text") or "")})
        elif part_type == "image_url" and role == "user":
            image_url = part.get("image_url")
            if isinstance(image_url, dict) and image_url.get("url"):
                normalized.append({"type": "input_image", "image_url": image_url["url"]})
    return normalized


def normalize_tool_calls(tool_calls: Any) -> list[dict[str, Any]]:
    if not isinstance(tool_calls, list):
        return []
    normalized = []
    for item in tool_calls:
        if not isinstance(item, dict):
            continue
        function = item.get("function") if isinstance(item.get("function"), dict) else {}
        name = str(function.get("name") or "").strip()
        if not name:
            continue
        normalized.append(
            {
                "type": "function_call",
                "call_id": str(item.get("id") or item.get("call_id") or ""),
                "name": name[:64],
                "arguments": str(function.get("arguments") or "{}"),
            }
        )
    return normalized


def normalize_tools(tools: Any) -> list[dict[str, Any]]:
    if not isinstance(tools, list):
        return []
    normalized = []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        if tool.get("type") != "function":
            normalized.append(tool)
            continue
        function = tool.get("function")
        if not isinstance(function, dict):
            continue
        item = {
            "type": "function",
            "name": str(function.get("name") or "")[:64],
            "description": function.get("description") or "",
            "parameters": function.get("parameters") or {},
        }
        if "strict" in function:
            item["strict"] = function["strict"]
        normalized.append(item)
    return normalized


def normalize_response_format(response_format: Any) -> dict[str, Any]:
    if not isinstance(response_format, dict):
        return {"format": {"type": "text"}}
    if response_format.get("type") == "json_schema":
        schema = response_format.get("json_schema")
        if isinstance(schema, dict):
            return {
                "format": {
                    "type": "json_schema",
                    "name": schema.get("name") or "response",
                    "schema": schema.get("schema") or {},
                    "strict": bool(schema.get("strict", False)),
                }
            }
    return {"format": {"type": "text"}}


def post_codex_responses(
    body: dict[str, Any],
    *,
    access_token: str,
    base_url: str,
    timeout_seconds: int,
) -> bytes:
    url = f"{base_url.rstrip('/')}/responses"
    headers = build_headers(access_token)
    headers.update(
        {
            "Accept": "text/event-stream",
            "User-Agent": DEFAULT_CODEX_USER_AGENT,
            "Originator": DEFAULT_CODEX_ORIGINATOR,
            "Session_id": prompt_cache_key(body),
            "Conversation_id": prompt_cache_key(body),
        }
    )
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Codex upstream failed: HTTP {error.code}: {detail}") from error
    except (OSError, TimeoutError, urllib.error.URLError) as error:
        raise RuntimeError(f"Codex upstream failed: {error}") from error


def parse_upstream_response(body: bytes) -> dict[str, Any]:
    try:
        parsed = json.loads(body.decode("utf-8"))
        return parsed.get("response") if isinstance(parsed.get("response"), dict) else parsed
    except ValueError:
        return parse_sse_response(body.decode("utf-8", errors="replace"))


def parse_sse_response(text: str) -> dict[str, Any]:
    completed: dict[str, Any] | None = None
    output_text = ""
    output_items: list[Any] = []
    for frame in text.replace("\r\n", "\n").split("\n\n"):
        payload_lines = []
        for line in frame.splitlines():
            if line.startswith("data:"):
                payload_lines.append(line.removeprefix("data:").strip())
        if not payload_lines:
            continue
        payload = "\n".join(payload_lines)
        if payload == "[DONE]":
            continue
        try:
            event = json.loads(payload)
        except ValueError:
            continue
        event_type = str(event.get("type") or "")
        if event_type == "response.output_text.delta":
            output_text += str(event.get("delta") or "")
        elif event_type == "response.output_text.done" and not output_text:
            output_text += str(event.get("text") or "")
        elif event_type == "response.output_item.done" and "item" in event:
            output_items.append(event["item"])
        elif event_type in {"response.completed", "response.done"}:
            response = event.get("response")
            completed = response if isinstance(response, dict) else event
    if completed is None:
        raise ValueError("Codex upstream response did not include response.completed.")
    if output_items and not completed.get("output"):
        completed["output"] = output_items
    if output_text and not completed.get("output_text"):
        completed["output_text"] = output_text
    return completed


def build_chat_completion_payload(
    response: dict[str, Any],
    requested_model: str,
    original_payload: dict[str, Any],
) -> dict[str, Any]:
    message = build_chat_message(response)
    usage = normalize_usage(response.get("usage") if isinstance(response, dict) else None)
    created = int(response.get("created_at") or response.get("created") or time.time())
    model = str(response.get("model") or requested_model)
    finish_reason = "tool_calls" if message.get("tool_calls") else "stop"
    return {
        "id": str(response.get("id") or f"chatcmpl-local-{int(time.time() * 1000)}"),
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": finish_reason,
                "native_finish_reason": finish_reason,
            }
        ],
        "usage": usage,
        "_codex_proxy": {
            "upstream": UPSTREAM_CODEX_BASE_URL,
            "requested_model": original_payload.get("model") or requested_model,
        },
    }


def build_chat_message(response: dict[str, Any]) -> dict[str, Any]:
    content = str(response.get("output_text") or "")
    tool_calls = []
    for item in response.get("output") or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "message":
            for part in item.get("content") or []:
                if isinstance(part, dict) and part.get("type") == "output_text":
                    content += str(part.get("text") or "")
        elif item.get("type") == "function_call":
            tool_calls.append(
                {
                    "id": item.get("call_id") or f"call_{len(tool_calls)}",
                    "type": "function",
                    "function": {
                        "name": item.get("name") or "",
                        "arguments": item.get("arguments") or "{}",
                    },
                }
            )
    message: dict[str, Any] = {"role": "assistant", "content": content or None}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return message


def normalize_usage(usage: Any) -> dict[str, Any]:
    usage = usage if isinstance(usage, dict) else {}
    prompt_tokens = int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
    completion_tokens = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
    total_tokens = int(usage.get("total_tokens") or prompt_tokens + completion_tokens)
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "prompt_tokens_details": {
            "cached_tokens": int(
                (usage.get("input_tokens_details") or {}).get("cached_tokens") or 0
            )
        },
        "completion_tokens_details": {
            "reasoning_tokens": int(
                (usage.get("output_tokens_details") or {}).get("reasoning_tokens") or 0
            )
        },
    }


def content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            str(part.get("text") or "") if isinstance(part, dict) else str(part)
            for part in content
        )
    return "" if content is None else str(content)


def prompt_cache_key(body: dict[str, Any]) -> str:
    raw = json.dumps(body.get("input") or body, ensure_ascii=False, sort_keys=True)
    return f"aka-{abs(hash(raw))}"
