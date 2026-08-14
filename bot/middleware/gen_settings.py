"""Middleware that loads/saves GenSettings in FSM data."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import TelegramObject

from bot.locales.texts import GenSettings


class GenSettingsMiddleware(BaseMiddleware):
    """Populate state data with a GenSettings dataclass on entry."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        state: FSMContext | None = data.get("state")
        if state is not None:
            raw = await state.get_data()
            gs = raw.get("gs")
            if not isinstance(gs, GenSettings):
                gs = GenSettings()
                await state.update_data(gs=gs)
            data["gs"] = gs
        return await handler(event, data)