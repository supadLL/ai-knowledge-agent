from __future__ import annotations

from .llm_access import LlmAccount, LlmAccountStore


def refresh_codex_account_if_possible(store: LlmAccountStore, account: LlmAccount) -> LlmAccount:
    credentials = store.credentials_for_account(account)
    refresh_token = str(credentials.get("refresh_token") or "").strip()
    if not refresh_token:
        return account

    from .codex_oauth import exchange_refresh_token

    current_id_token = str(credentials.get("id_token") or "").strip()
    tokens = exchange_refresh_token(refresh_token, current_id_token=current_id_token)
    next_credentials = dict(credentials)
    if tokens.refresh_token:
        next_credentials["refresh_token"] = tokens.refresh_token
    if tokens.id_token:
        next_credentials["id_token"] = tokens.id_token
    if tokens.expires_in:
        next_credentials["expires_in"] = tokens.expires_in
    if tokens.token_type:
        next_credentials["token_type"] = tokens.token_type
    updated = store.update_account_secret(
        account.id,
        api_key=tokens.access_token,
        credential_payload=next_credentials,
    )
    return updated or account
