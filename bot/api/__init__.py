"""aiohttp web-app backing the Telegram Mini App (TWA)."""

from bot.api.app import build_app

__all__ = ["build_app"]