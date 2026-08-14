"""Entry point for the VideoVeoBot demo.

Usage:
    python bot.py

Reads configuration from .env (or environment variables). Without BOT_TOKEN
the bot just prints a friendly error and exits.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from bot.config import Config
from bot.database import close_database, init_database
from bot.handlers import build_root_router
from bot.middleware import GenSettingsMiddleware
from bot.services import UserService


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    )
    # Load .env from the project root (next to bot.py).
    load_dotenv()
    config = Config.from_env()
    if not config.has_token:
        print(
            "ERROR: BOT_TOKEN is empty.\n"
            "Set it in .env at the project root, or via the environment:\n"
            "    BOT_TOKEN=123:ABC python bot.py",
            file=sys.stderr,
        )
        sys.exit(1)

    logging.info("Starting VideoVeoBot demo…")
    logging.info("TWA URL: %s", config.twa_url or "(not set)")
    logging.info("Database: %s", config.database_url)

    await init_database(config.database_url)

    bot = Bot(
        config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Build the service that handlers depend on. Access the live module
    # attribute (init_database assigns into bot.database.* globals).
    from bot import database as db_module

    assert db_module.session_factory is not None
    service = UserService(session_factory=db_module.session_factory)

    # Middleware подгружает GenSettings в data["gs"] из FSM data
    dp.message.middleware(GenSettingsMiddleware())
    dp.callback_query.middleware(GenSettingsMiddleware())

    dp.include_router(build_root_router())

    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            config=config,
            service=service,
        )
    finally:
        await close_database()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped.")