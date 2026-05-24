from __future__ import annotations

import base64
import binascii
import json
from typing import Any


def decode_jwt_payload(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    parts = token.split(".")
    if len(parts) != 3:
        return None
    payload = parts[1]
    payload += "=" * (-len(payload) % 4)
    try:
        raw = base64.urlsafe_b64decode(payload.encode("ascii"))
        decoded = json.loads(raw.decode("utf-8"))
    except (binascii.Error, ValueError, TypeError, UnicodeDecodeError):
        return None
    return decoded if isinstance(decoded, dict) else None


def extract_chatgpt_account_id_from_access_token(access_token: str) -> str | None:
    auth_data = access_token_auth_claims(access_token)
    if not auth_data:
        return None
    return first_string(auth_data, "chatgpt_account_id", "account_id")


def extract_chatgpt_plan_type_from_token(token: str | None) -> str | None:
    payload = decode_jwt_payload(token)
    if not payload:
        return None
    auth_data = payload.get("https://api.openai.com/auth")
    profile_data = payload.get("https://api.openai.com/profile")
    for data in (auth_data, profile_data, payload):
        if isinstance(data, dict):
            plan_type = first_string(data, "chatgpt_plan_type", "plan_type", "planType")
            if plan_type:
                return plan_type
    return None


def access_token_auth_claims(access_token: str) -> dict[str, Any] | None:
    payload = decode_jwt_payload(access_token)
    if not payload:
        return None
    auth_data = payload.get("https://api.openai.com/auth")
    return auth_data if isinstance(auth_data, dict) else None


def first_string(data: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None
