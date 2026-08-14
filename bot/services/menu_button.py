"""High-level helpers for the bot's chat Menu Button (Telegram Mini App).

Why this lives in its own module
--------------------------------
Telegram exposes a single, persistent button at the bottom of the bot chat
(see ``MenuButtonWebApp`` in the official Bot API docs). Setting it up by
hand in @BotFather works, but is easy to forget and impossible to script
across multiple environments. We expose three operations:

* :func:`set_webapp_menu_button` — register/update the Mini App button
* :func:`get_menu_button` — read the current state (handy for ``/menustatus``)
* :func:`reset_menu_button` — remove a custom button (revert to commands)

All operations are thin wrappers around the aiogram 3 ``Bot`` methods. They
accept a ``Bot`` instance so they can be invoked both from bot handlers
(``bot`` already in scope) and from one-off CLI scripts
(``scripts/setup_menu_button.py``).

References
----------
* Telegram Bot API — setChatMenuButton / getChatMenuButton
  https://core.telegram.org/bots/api#setchatmenubutton
* MenuButtonWebApp object — ``type='web_app'``, ``text``, ``web_app.url``
  https://core.telegram.org/bots/api#menubuttonwebapp
* Mini Apps launching docs — HTTPS required (localhost is the only
  http:// exception)
  https://github.com/telegram-mini-apps/telegram-apps
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from aiogram import Bot
from aiogram.methods import GetChatMenuButton, SetChatMenuButton
from aiogram.methods.base import TelegramMethod


class MenuButtonError(RuntimeError):
    """Raised when Menu Button cannot be configured (bad URL, API error)."""


def _is_valid_mini_app_url(url: str) -> bool:
    """Mini Apps require HTTPS (or http://localhost / 127.0.0.1 in dev).

    The official Bot API accepts arbitrary strings, but the client will refuse
    to launch the Web App if the URL doesn't satisfy these constraints. We
    fail fast in Python so a misconfigured ``.env`` doesn't silently break
    the integration.
    """
    if not url:
        return False
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        return False
    if parsed.scheme == "https":
        return True
    host = (parsed.hostname or "").lower()
    return host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


@dataclass(frozen=True)
class MenuButtonInfo:
    """Snapshot of the current menu button state — returned by :func:`get_menu_button`."""

    type: str  # commands | web_app | default
    text: str | None = None
    url: str | None = None

    @property
    def is_webapp(self) -> bool:
        return self.type == "web_app"

    def describe(self) -> str:
        """Human-readable one-line description (Russian, for /menustatus)."""
        if self.type == "web_app":
            return f"📱 Web App: «{self.text or ''}» → {self.url or ''}"
        if self.type == "commands":
            return "📋 Список команд (по умолчанию)"
        return "🔘 По умолчанию (MenuButtonDefault)"


def _to_info(raw: Any) -> MenuButtonInfo:
    """Convert whatever aiogram returns into our :class:`MenuButtonInfo`.

    The aiogram object has ``type``, ``text`` and ``web_app.url`` fields —
    but the type signature changes across versions, so we read attributes
    defensively (anyio.aiogram.models.MenuButtonWebApp etc.).
    """
    btn_type = getattr(raw, "type", "default") or "default"
    text = getattr(raw, "text", None)
    webapp = getattr(raw, "web_app", None)
    url = getattr(webapp, "url", None) if webapp is not None else None
    return MenuButtonInfo(type=str(btn_type), text=text, url=url)


async def set_webapp_menu_button(
    bot: Bot,
    *,
    text: str,
    url: str,
    chat_id: int | None = None,
) -> MenuButtonInfo:
    """Register / update the bot's Mini App menu button.

    Parameters
    ----------
    bot
        aiogram ``Bot`` instance (already initialised with the bot token).
    text
        Label shown on the button. Must be non-empty, ≤ 32 chars is a safe
        upper bound for the Telegram UI (the docs don't specify but UI
        truncates aggressively).
    url
        HTTPS URL of the Mini App (or http://localhost in dev). Validated
        by :func:`_is_valid_mini_app_url`.
    chat_id
        If set — change the button **only** for that private chat.
        If ``None`` — change the bot's **default** menu button (recommended:
        applies to every chat the bot is added to).

    Returns
    -------
    :class:`MenuButtonInfo`
        Confirmed state as reported by the server.

    Raises
    ------
    MenuButtonError
        If ``url`` is not HTTPS / localhost, or the Telegram API call
        fails (network, invalid token, quota, etc.).
    """
    text = (text or "").strip()
    if not text:
        raise MenuButtonError("button text must not be empty")
    if not _is_valid_mini_app_url(url):
        raise MenuButtonError(
            f"invalid Mini App URL: {url!r}. "
            "Telegram requires HTTPS (or http://localhost/127.0.0.1 in dev). "
            "See https://github.com/telegram-mini-apps/telegram-apps/blob/master/apps/docs/platform/getting-app-link.md"
        )

    payload: dict[str, Any] = {
        "menu_button": {
            "type": "web_app",
            "text": text,
            "web_app": {"url": url},
        }
    }
    if chat_id is not None:
        payload["chat_id"] = chat_id

    try:
        # aiogram serialises the dict via the `menu_button` model, which is
        # typed as MenuButton in newer aiogram — both paths accept a dict.
        response = await bot(SetChatMenuButton(**payload))  # type: ignore[arg-type]
    except Exception as exc:  # pragma: no cover — network path
        raise MenuButtonError(f"setChatMenuButton failed: {exc}") from exc

    return _to_info(response)


async def get_menu_button(bot: Bot, *, chat_id: int | None = None) -> MenuButtonInfo:
    """Read the current menu button state.

    Parameters
    ----------
    bot
        aiogram ``Bot``.
    chat_id
        If set — query the per-chat button. If ``None`` — query the bot's
        default button.
    """
    kwargs: dict[str, Any] = {}
    if chat_id is not None:
        kwargs["chat_id"] = chat_id
    try:
        response = await bot(GetChatMenuButton(**kwargs))  # type: ignore[arg-type]
    except Exception as exc:  # pragma: no cover — network path
        raise MenuButtonError(f"getChatMenuButton failed: {exc}") from exc
    return _to_info(response)


async def reset_menu_button(bot: Bot, *, chat_id: int | None = None) -> MenuButtonInfo:
    """Revert the menu button to the default ("commands list").

    Useful when a deployment switches from one Mini App URL to another and
    we want to make sure no stale button lingers for users who installed
    the previous version.
    """
    payload: dict[str, Any] = {"menu_button": {"type": "default"}}
    if chat_id is not None:
        payload["chat_id"] = chat_id
    try:
        response = await bot(SetChatMenuButton(**payload))  # type: ignore[arg-type]
    except Exception as exc:  # pragma: no cover — network path
        raise MenuButtonError(f"reset menu button failed: {exc}") from exc
    return _to_info(response)


__all__ = [
    "MenuButtonError",
    "MenuButtonInfo",
    "get_menu_button",
    "reset_menu_button",
    "set_webapp_menu_button",
]