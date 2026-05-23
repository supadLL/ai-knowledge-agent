from __future__ import annotations

import base64
import ctypes
import json
import sys
from ctypes import wintypes
from typing import Any


DPAPI_SCHEME = "win32-dpapi"
FALLBACK_SCHEME = "base64-json"


class DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


def seal_json_payload(payload: dict[str, Any] | None) -> str:
    cleaned = {key: value for key, value in (payload or {}).items() if value not in (None, "")}
    if not cleaned:
        return ""
    raw = json.dumps(cleaned, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if sys.platform == "win32":
        return json.dumps(
            {
                "scheme": DPAPI_SCHEME,
                "data": base64.b64encode(dpapi_protect(raw)).decode("ascii"),
            },
            separators=(",", ":"),
        )
    return json.dumps(
        {
            "scheme": FALLBACK_SCHEME,
            "data": base64.b64encode(raw).decode("ascii"),
        },
        separators=(",", ":"),
    )


def unseal_json_payload(sealed: str | None) -> dict[str, Any]:
    if not sealed:
        return {}
    try:
        envelope = json.loads(sealed)
        scheme = envelope.get("scheme")
        data = base64.b64decode(str(envelope.get("data") or ""))
        if scheme == DPAPI_SCHEME:
            raw = dpapi_unprotect(data)
        elif scheme == FALLBACK_SCHEME:
            raw = data
        else:
            return {}
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def has_sealed_credentials(sealed: str | None) -> bool:
    return bool(unseal_json_payload(sealed))


def dpapi_protect(raw: bytes) -> bytes:
    if sys.platform != "win32":
        raise OSError("Windows DPAPI is only available on Windows.")
    in_blob, buffer = blob_from_bytes(raw)
    out_blob = DataBlob()
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)
        del buffer


def dpapi_unprotect(encrypted: bytes) -> bytes:
    if sys.platform != "win32":
        raise OSError("Windows DPAPI is only available on Windows.")
    in_blob, buffer = blob_from_bytes(encrypted)
    out_blob = DataBlob()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)
        del buffer


def blob_from_bytes(raw: bytes) -> tuple[DataBlob, ctypes.Array[ctypes.c_char]]:
    buffer = ctypes.create_string_buffer(raw)
    blob = DataBlob(len(raw), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    return blob, buffer
