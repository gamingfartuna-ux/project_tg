"""Telegram Mini Apps initData validation.

Implements the official HMAC-SHA256 signature scheme documented at
https://github.com/telegram-mini-apps/telegram-apps (see
``apps/docs/platform/init-data.md``).

Algorithm (bot-token flavour):
1. Parse ``initData`` as URL-encoded query string.
2. Build ``data_check_string`` by concatenating ``key=value`` for every pair
   EXCEPT ``hash`` (and ``signature`` if present), sorted alphabetically by
   key, joined by ``\\n``.
3. Compute ``secret_key = HMAC-SHA256(bot_token, "WebAppData")``.
4. Compute ``computed_hash = HMAC-SHA256(data_check_string, secret_key)``.
5. Compare ``computed_hash`` (hex) to the ``hash`` field.

The implementation uses ``hmac.compare_digest`` to avoid timing attacks and
performs an extra ``auth_date`` freshness check (configurable TTL).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, unquote


class InitDataError(Exception):
    """Raised when initData is malformed or signature is invalid."""


@dataclass(frozen=True)
class TgUser:
    """Subset of Telegram User that we expose to handlers."""

    id: int
    first_name: str
    last_name: str | None
    username: str | None
    language_code: str | None
    is_premium: bool
    photo_url: str | None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "TgUser":
        return cls(
            id=int(payload["id"]),
            first_name=str(payload.get("first_name") or ""),
            last_name=payload.get("last_name"),
            username=payload.get("username"),
            language_code=payload.get("language_code"),
            is_premium=bool(payload.get("is_premium", False)),
            photo_url=payload.get("photo_url"),
        )


def _build_data_check_string(pairs: dict[str, str]) -> str:
    """Build the canonical ``data_check_string``.

    Excludes ``hash`` (and ``signature`` if present). Sorted by key.
    """
    filtered = {
        k: v
        for k, v in pairs.items()
        if k not in {"hash", "signature"}
    }
    return "\n".join(f"{k}={filtered[k]}" for k in sorted(filtered))


def validate_init_data(
    init_data: str,
    bot_token: str,
    *,
    ttl_seconds: int = 3600,
    now: int | None = None,
) -> dict[str, Any]:
    """Validate raw ``initData`` against ``bot_token``.

    Returns the parsed init data dict (with ``user`` JSON-decoded) on success.
    Raises :class:`InitDataError` otherwise.

    ``ttl_seconds`` enforces ``auth_date`` freshness (anti-replay). Set to 0
    to disable the check (not recommended in production).
    """
    if not init_data:
        raise InitDataError("init_data is empty")
    if not bot_token:
        raise InitDataError("bot_token is empty")

    # parse_qs collapses duplicate keys; initData never contains them.
    parsed = parse_qs(init_data, keep_blank_values=True, strict_parsing=False)
    pairs: dict[str, str] = {k: v[0] for k, v in parsed.items()}

    received_hash = pairs.get("hash")
    if not received_hash:
        raise InitDataError("hash is missing")

    # 1+2: build data_check_string
    data_check_string = _build_data_check_string(pairs)

    # 3: secret_key = HMAC-SHA256(bot_token, "WebAppData")
    secret_key = hmac.new(
        b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256
    ).digest()

    # 4: computed_hash
    computed_hash = hmac.new(
        secret_key, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise InitDataError("hash mismatch")

    # Freshness check (anti-replay).
    if ttl_seconds > 0:
        auth_date_raw = pairs.get("auth_date")
        if not auth_date_raw:
            raise InitDataError("auth_date is missing")
        try:
            auth_date = int(auth_date_raw)
        except ValueError as exc:
            raise InitDataError("auth_date is not an integer") from exc
        current = now if now is not None else int(time.time())
        if abs(current - auth_date) > ttl_seconds:
            raise InitDataError("init_data is expired")

    # Decode the JSON ``user`` payload for the caller's convenience.
    user_raw = pairs.get("user")
    if user_raw:
        try:
            pairs["user"] = json.loads(unquote(user_raw))
        except json.JSONDecodeError:
            # Keep the raw string; downstream code can still inspect it.
            pairs["user"] = unquote(user_raw)
    return pairs


def extract_user(init_data_parsed: dict[str, Any]) -> TgUser:
    """Pull a :class:`TgUser` out of parsed initData."""
    user = init_data_parsed.get("user")
    if not isinstance(user, dict):
        raise InitDataError("user is missing or not a dict")
    return TgUser.from_payload(user)