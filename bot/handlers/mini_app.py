"""Admin commands for configuring the bot's Telegram Mini App menu button.

These commands replace the manual ``/setmenubutton`` flow in @BotFather.
They call ``setChatMenuButton`` / ``getChatMenuButton`` via the aiogram
``Bot`` instance — see :mod:`bot.services.menu_button` for the underlying
implementation.

Commands
--------
``/setmenu``     — register/update the Mini App button using ``TWA_URL``.
                   Idempotent: safe to re-run after editing ``.env``.
``/menustatus``  — show the current menu button state for this chat.
``/menuoff``     — revert to the default ("commands list") button.
``/miniapp``     — alias for /setmenu that also re-renders the main menu.

Access control
--------------
All commands are restricted to ``ADMIN_IDS`` from the environment (same
policy as the rest of the bot). Without admin rights the commands silently
no-op — the user sees nothing. This prevents random users from spamming
``setChatMenuButton``.
"""

from __future__ import annotations

import logging
from typing import Any

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.config import Config
from bot.keyboards import main_menu_kb
from bot.locales import main_menu_text
from bot.services import (
    MenuButtonError,
    get_menu_button,
    reset_menu_button,
    set_webapp_menu_button,
)

router = Router(name="mini_app")
log = logging.getLogger(__name__)


def _is_admin(message: Message, config: Config) -> bool:
    if not config.admin_ids:
        return False
    if message.from_user is None:
        return False
    return message.from_user.id in config.admin_ids


def _default_button_text(twa_url: str) -> str:
    """Pick a sensible button label for the configured Mini App URL."""
    # We deliberately keep this short — Telegram truncates long labels.
    return "📱 Mini App"


@router.message(Command("setmenu"))
async def cmd_set_menu(
    message: Message,
    bot: Bot,
    config: Config,
    state: FSMContext,
) -> None:
    """/setmenu — register/update the chat menu button with TWA_URL."""
    if message.from_user is None:
        return
    await state.clear()

    if not _is_admin(message, config):
        await message.answer("Эта команда только для админов бота.")
        return

    url = (config.twa_url or "").strip()
    if not url:
        await message.answer(
            "❌ <b>TWA_URL не задан</b>.\n"
            "Добавьте в <code>.env</code> строку вида\n"
            "<code>TWA_URL=https://your-host/</code>\n"
            "и перезапустите бота.",
        )
        return

    try:
        info = await set_webapp_menu_button(
            bot,
            text=_default_button_text(url),
            url=url,
            chat_id=message.chat.id,
        )
    except MenuButtonError as exc:
        log.warning("setmenu failed: %s", exc)
        await message.answer(f"❌ Не удалось зарегистрировать кнопку:\n<code>{exc}</code>")
        return

    await message.answer(
        "✅ <b>Кнопка Mini App зарегистрирована</b>\n\n"
        f"Текст: <code>{info.text}</code>\n"
        f"URL: <code>{info.url}</code>\n\n"
        "Откройте чат с ботом — в правом нижнем углу должна появиться кнопка.\n"
        "Если её нет — перезапустите Telegram и проверьте, что URL начинается с https://.",
    )


@router.message(Command("menustatus"))
async def cmd_menu_status(
    message: Message,
    bot: Bot,
    config: Config,
) -> None:
    """/menustatus — show the current menu button state for this chat."""
    if not _is_admin(message, config):
        await message.answer("Эта команда только для админов бота.")
        return
    try:
        chat_info = await get_menu_button(bot, chat_id=message.chat.id)
    except MenuButtonError as exc:
        await message.answer(f"❌ Ошибка: <code>{exc}</code>")
        return
    try:
        default_info = await get_menu_button(bot)
    except MenuButtonError:
        default_info = None  # non-fatal — chat-level info is the important one

    text = (
        f"📍 <b>В этом чате:</b> {chat_info.describe()}\n"
        + (
            f"🌐 <b>По умолчанию (для новых чатов):</b> {default_info.describe()}"
            if default_info is not None
            else ""
        )
        + "\n\n"
        "Чтобы изменить — используйте /setmenu (зарегистрировать Mini App) "
        "или /menuoff (сбросить на команды)."
    )
    await message.answer(text)


@router.message(Command("menuoff"))
async def cmd_menu_off(
    message: Message,
    bot: Bot,
    config: Config,
) -> None:
    """/menuoff — revert the menu button for this chat to default."""
    if not _is_admin(message, config):
        await message.answer("Эта команда только для админов бота.")
        return
    try:
        await reset_menu_button(bot, chat_id=message.chat.id)
    except MenuButtonError as exc:
        await message.answer(f"❌ Ошибка: <code>{exc}</code>")
        return
    await message.answer("✅ Кнопка Mini App сброшена. По умолчанию — список команд.")


@router.message(Command("miniapp"))
async def cmd_miniapp(
    message: Message,
    bot: Bot,
    config: Config,
    state: FSMContext,
) -> None:
    """/miniapp — register the menu button and re-send the main menu.

    Useful during local development: one command both wires the button
    via the Bot API and re-displays the menu (so the user can immediately
    tap «Открыть Mini App»).
    """
    if not _is_admin(message, config):
        await message.answer("Эта команда только для админов бота.")
        return
    await state.clear()
    url = (config.twa_url or "").strip()
    if not url:
        await message.answer(
            "❌ TWA_URL не задан в .env. Команда /setmenu покажет то же самое."
        )
        return

    try:
        await set_webapp_menu_button(
            bot,
            text=_default_button_text(url),
            url=url,
            chat_id=message.chat.id,
        )
    except MenuButtonError as exc:
        await message.answer(f"⚠️ Кнопка не зарегистрирована: <code>{exc}</code>")

    await message.answer(
        main_menu_text(),
        reply_markup=main_menu_kb(twa_url=config.twa_url),
    )


async def auto_register_default_menu_button(bot: Bot, config: Config) -> None:
    """Best-effort: set the bot's DEFAULT menu button on startup if missing.

    Called from ``bot.py`` after the dispatcher is up but before polling.
    Silent on errors — this is a convenience for dev / demo, not a
    guarantee. If it fails (e.g. the bot token is for a webhook-only bot,
    or there's no network), the admin can always call ``/setmenu`` later.
    """
    url = (config.twa_url or "").strip()
    if not url:
        return
    try:
        # Check first to avoid pointless churn in the logs.
        current = await get_menu_button(bot)
    except MenuButtonError as exc:
        log.info("auto-register menu button skipped: %s", exc)
        return
    if current.is_webapp and current.url == url:
        return
    try:
        info = await set_webapp_menu_button(
            bot,
            text=_default_button_text(url),
            url=url,
        )
        log.info("auto-registered default menu button: %s", info.describe())
    except MenuButtonError as exc:
        log.warning("auto-register menu button failed: %s", exc)


__all__ = [
    "auto_register_default_menu_button",
    "router",
]