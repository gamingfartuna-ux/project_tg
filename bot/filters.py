"""Custom aiogram filters that don't fit CallbackData.filter()."""

from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery

from bot.keyboards.menus import Action, ExamplePick


class ActionFilter(BaseFilter):
    """Match a callback whose Action data has the given ``name``."""

    def __init__(self, name: str) -> None:
        self.name = name

    async def __call__(self, callback: CallbackQuery) -> bool:
        if not isinstance(callback.data, str):
            return False
        try:
            parsed = Action.unpack(callback.data)
        except Exception:
            return False
        return parsed.name == self.name


class ExampleFilter(BaseFilter):
    """Match an ExamplePick callback regardless of direction."""

    async def __call__(self, callback: CallbackQuery) -> bool:
        if not isinstance(callback.data, str):
            return False
        try:
            ExamplePick.unpack(callback.data)
            return True
        except Exception:
            return False