"""Entry point for the TWA aiohttp backend.

Usage:
    python api.py

Reads configuration from .env (or environment variables). Without BOT_TOKEN
the process prints a friendly error and exits.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from aiohttp import web
from dotenv import load_dotenv

from bot.api import build_app
from bot.config import Config
from bot.database import close_database, init_database
from bot.services import UserService


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    )
    load_dotenv()
    config = Config.from_env()
    if not config.has_token:
        print(
            "ERROR: BOT_TOKEN is empty.\n"
            "Set it in .env at the project root, or via the environment:\n"
            "    BOT_TOKEN=123:ABC python api.py",
            file=sys.stderr,
        )
        sys.exit(1)

    logging.info(
        "Starting TWA API on %s:%d", config.twa_api_host, config.twa_api_port
    )
    logging.info("Database: %s", config.database_url)
    logging.info(
        "TWA static dir: %s%s",
        config.twa_static_dir,
        "" if Path(config.twa_static_dir).is_dir() else " (NOT FOUND — UI will 404)",
    )

    await init_database(config.database_url)

    from bot import database as db_module

    assert db_module.session_factory is not None
    service = UserService(session_factory=db_module.session_factory)

    app = build_app(config, service)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.twa_api_host, config.twa_api_port)
    try:
        await site.start()
        logging.info(
            "TWA API ready: http://%s:%d/api/health",
            config.twa_api_host,
            config.twa_api_port,
        )
        # Idle forever — Ctrl-C to stop.
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()
        await close_database()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("TWA API stopped.")