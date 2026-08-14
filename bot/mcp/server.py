"""MCP server exposing veo_video_bot project documentation as tools.

Built with the MCP Python SDK (stdio transport).  Run directly:
    python -m bot.mcp

Or via the SDK CLI:
    mcp run bot.mcp:server
    mcp dev bot.mcp:server

Tools
-----
list_docs()              → list all available documentation sections
get_handler(name)        → full source of a handler module
get_service(name)        → full source of a service module
get_api()                → full source of the aiohttp API backend
get_config()             → full source of config.py
get_model(name)          → get MODEL_NAMES / MODEL_DESCRIPTIONS for one model
get_texts()              → get all locale texts
get_example_catalog()    → get example video catalog
get_schema()             → database schema (User, Generation models)
get_wizard_flow()        → FSM wizard state flow
get_keyboard_schema()    → CallbackData / keyboard layout
get_miniapp_api()        → TWA Mini App REST API spec (/api/* endpoints)
get_init_data_auth()     → initData HMAC-SHA256 auth explanation
get_bot_commands()       → all bot commands and what they do
get_project_summary()    → high-level project overview

All tools return structured text suitable for an LLM context window.
"""

from __future__ import annotations

import inspect
import os
import sys
from pathlib import Path
from textwrap import dedent

# Resolve the project root (two levels up from this file: bot/mcp/server.py)
_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read(rel_path: str) -> str:
    """Read a file relative to the project root, return '' on failure."""
    try:
        return (Path(_ROOT) / rel_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"[File not found: {rel_path}]"


def _source(mod_name: str, attr: str | None = None) -> str:
    """Return the source code for a module or a named attribute within it."""
    try:
        if attr is None:
            obj = __import__(mod_name, fromlist=[attr or ""])
            src = inspect.getsource(obj)
        else:
            obj = __import__(mod_name, fromlist=["_"])
            src = inspect.getsource(getattr(obj, attr))
        return src
    except (ImportError, AttributeError) as exc:
        return f"[Cannot load source for {mod_name}.{attr}: {exc}]"


# ---------------------------------------------------------------------------
# Tool implementations (one per documentation section)
# ---------------------------------------------------------------------------

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

_server_name = "veo-video-bot-docs"
_server_version = "1.0.0"

server = Server(_server_name, _server_version)


# ---------------------------------------------------------------------------
# list_docs — overview of what is available
# ---------------------------------------------------------------------------

@server.tool()
def list_docs() -> str:
    """List all available documentation tools and what they return."""
    return dedent("""\
        veo_video_bot project — available documentation tools:

        Project structure
        -----------------
        get_project_summary   → high-level overview (structure, tech stack, purpose)
        get_schema()          → SQLAlchemy ORM models (User, Generation)
        get_example_catalog()  → example video catalog with prompts
        get_init_data_auth()  → Telegram initData HMAC-SHA256 validation flow
        get_bot_commands()     → all bot commands with descriptions

        Handlers (bot/handlers/*.py)
        ----------------------------
        get_handler("start")       → /start, /help, /cancel, /balance, /history, /kling, /veo, /seedance, /lipsync
        get_handler("menu")        → inline callback handlers: model pick, main, balance, topup, history
        get_handler("generation")   → full generation wizard FSM (format → mode → duration → sound → image → prompt → confirm)
        get_handler("lipsync")     → lipsync wizard FSM (photo → audio → done)
        get_handler("examples")     → example video carousel with navigation
        get_handler("mini_app")     → /setmenu, /menuoff, /menustatus, /miniapp admin commands

        Services (bot/services/*.py)
        ---------------------------
        get_service("user_service")   → UserService: upsert_user, get_user, spend, refund, add_balance, record_generation, last_generations
        get_service("menu_button")    → set/get/reset Telegram chat menu button via Bot API
        get_service("twa_auth")       → validate_init_data (HMAC-SHA256), TgUser dataclass, extract_user

        API backend (bot/api/app.py)
        ---------------------------
        get_api()  → aiohttp web-app: /api/health, /api/me, /api/generations (GET+POST), /api/topup

        TWA Mini App
        ------------
        get_miniapp_api()   → TWA Mini App REST API spec (all endpoints, auth, request/response shapes)
        get_keyboard_schema() → CallbackData schemas (Action, ModelPick) and keyboard builders

        Config / Text
        -------------
        get_config()   → Config dataclass with all env vars (bot_token, admin_ids, database_url, twa_url, twa_api_host, twa_api_port, twa_allowed_origins, twa_init_data_ttl, twa_static_dir)
        get_texts()     → all locale texts (main_menu_text, model_card_text, format_text, mode_text, confirm_text, done_text, balance_text, history_text, etc.)
        get_wizard_flow() → FSM state flow diagram for generation wizard

        Usage examples
        --------------
        To read a handler source:
            get_handler("generation")    → full generation.py source
            get_handler("start")        → full start.py source
            get_handler("menu")          → full menu.py source
            get_handler("lipsync")       → full lipsync.py source
            get_handler("examples")      → full examples.py source
            get_handler("mini_app")      → full mini_app.py source
        """)


# ---------------------------------------------------------------------------
# Handler sources
# ---------------------------------------------------------------------------

_HANDLERS = {
    "start": "bot.handlers.start",
    "menu": "bot.handlers.menu",
    "generation": "bot.handlers.generation",
    "lipsync": "bot.handlers.lipsync",
    "examples": "bot.handlers.examples",
    "mini_app": "bot.handlers.mini_app",
}


@server.tool()
def get_handler(name: str) -> str:
    """Return the full source code of a handler module.

    name: one of start | menu | generation | lipsync | examples | mini_app
    """
    key = name.strip().lower()
    if key not in _HANDLERS:
        available = ", ".join(sorted(_HANDLERS))
        return f"Unknown handler {name!r}. Available: {available}"
    # Inject project root so imports resolve
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    return _source(_HANDLERS[key])


# ---------------------------------------------------------------------------
# Service sources
# ---------------------------------------------------------------------------

_SERVICES = {
    "user_service": "bot.services.user_service",
    "menu_button": "bot.services.menu_button",
    "twa_auth": "bot.services.twa_auth",
}


@server.tool()
def get_service(name: str) -> str:
    """Return the full source code of a service module.

    name: one of user_service | menu_button | twa_auth
    """
    key = name.strip().lower()
    if key not in _SERVICES:
        available = ", ".join(sorted(_SERVICES))
        return f"Unknown service {name!r}. Available: {available}"
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    return _source(_SERVICES[key])


# ---------------------------------------------------------------------------
# API backend
# ---------------------------------------------------------------------------

@server.tool()
def get_api() -> str:
    """Return the full source of bot/api/app.py — the aiohttp TWA backend."""
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    return _source("bot.api.app")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@server.tool()
def get_config() -> str:
    """Return the full source of bot/config.py — Config dataclass + env loading."""
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    return _source("bot.config")


# ---------------------------------------------------------------------------
# Locale texts
# ---------------------------------------------------------------------------

@server.tool()
def get_texts() -> str:
    """Return the full source of bot/locales/texts.py — all user-facing messages."""
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    return _source("bot.locales.texts")


# ---------------------------------------------------------------------------
# Example catalog
# ---------------------------------------------------------------------------

@server.tool()
def get_example_catalog() -> str:
    """Return the full source of bot/examples/catalog.py — example video URLs and prompts."""
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    return _source("bot.examples.catalog")


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

@server.tool()
def get_schema() -> str:
    """Return the full source of bot/models.py — SQLAlchemy User and Generation ORM models."""
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    return _source("bot.models")


# ---------------------------------------------------------------------------
# FSM wizard flow
# ---------------------------------------------------------------------------

@server.tool()
def get_wizard_flow() -> str:
    """Describe the generation wizard FSM state flow."""
    return dedent("""\
        Generation wizard FSM (bot/handlers/generation.py)
        =================================================

        State: GenerationWizard (FSMContext)

        Steps (linear, one per user message/callback):
        ---------------------------------------------
        1. wait_format   → user picks "vertical" or "horizontal"
        2. wait_mode     → user picks "standard" | "pro" | "4k"
                           (4K blocked for horizontal; 4K forces sound=off)
        3. wait_duration → user picks 5 or 10 seconds
                           (10s adds +1 to base cost)
        4. wait_sound    → user toggles sound on/off
                           (forced off for 4K; shown but non-interactive)
        5. wait_image    → user sends a photo or clicks "skip"
                           (optional; stored as file_id in FSM data)
        6. wait_prompt   → user types a free-text prompt (max 2500 chars)
        7. wait_confirm  → shows cost breakdown + balance impact;
                           user confirms "Сгенерировать" or cancels "Назад"
                           On confirm: deduct balance, record generation,
                           return done_text with demo video URL.

        Back navigation: "← Назад" from any step returns to the previous step.
        Cancel (/cancel): clears FSM, returns to main menu.

        Cost formula (compute_cost):
            base = 1 (standard), 2 (pro), 4 (4k)
            +1 if duration == 10
            (4K always has sound=False regardless of user choice)

        Lipsync wizard (bot/handlers/lipsync.py)
        ======================================
        State: LipsyncWizard
        Steps:
        1. wait_face_photo  → user sends a photo (saved as file_id)
        2. wait_audio       → user sends voice message or audio file
        3. done             → shows lipsync_done_text with demo video

        Cost for lipsync = 1 generation (fixed in generation.py step_confirm).
        """)


# ---------------------------------------------------------------------------
# Keyboard / CallbackData schema
# ---------------------------------------------------------------------------

@server.tool()
def get_keyboard_schema() -> str:
    """Return the full source of bot/keyboards/ — CallbackData + InlineKeyboardMarkup builders."""
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    return _source("bot.keyboards.menus")


# ---------------------------------------------------------------------------
# TWA Mini App REST API spec
# ---------------------------------------------------------------------------

@server.tool()
def get_miniapp_api() -> str:
    """Return the TWA Mini App REST API specification (endpoints, auth, shapes)."""
    return dedent("""\
        TWA Mini App REST API (served by bot/api/app.py on TWA_API_HOST:TWA_API_PORT)
        ==============================================================================

        Base URL: same origin as the Mini App page (e.g. http://127.0.0.1:8080)

        Authentication
        --------------
        Every /api/* endpoint (except /api/health) requires:
            Authorization: tma <initData>
        where initData = window.Telegram.WebApp.initData (URL-encoded query string).

        initData is validated server-side:
          1. Parse as URL-encoded query string (exclude 'hash', 'signature')
          2. Build data_check_string = key=value\\n sorted by key
          3. secret_key = HMAC-SHA256(bot_token, "WebAppData")
          4. computed_hash = HMAC-SHA256(data_check_string, secret_key)
          5. Compare to received hash (constant-time)
          6. Check auth_date freshness (default TTL: 3600s)

        If invalid → HTTP 401 {"error": "init_data invalid: ..."}

        Endpoints
        ---------
        GET /api/health
          Auth: none
          Response: {"ok": true}

        GET /api/me
          Auth: required
          Response 200:
            {
              "id": int,                    # Telegram user ID
              "first_name": str,
              "last_name": str | null,
              "username": str | null,
              "is_premium": bool,
              "photo_url": str | null,
              "balance": int,               # current balance (generations)
              "models": ["kling","veo","seedance","lipsync"]
            }

        GET /api/generations?limit=N (default 20, max 50)
          Auth: required
          Response 200:
            {
              "items": [
                {
                  "id": int,
                  "model": str,             # "kling" | "veo" | "seedance" | "lipsync"
                  "model_name": str,         # human-readable
                  "fmt": str,               # "vertical" | "horizontal"
                  "mode": str,              # "standard" | "pro" | "4k"
                  "duration": int,          # 5 | 10
                  "sound": bool,
                  "prompt": str,
                  "cost": int,
                  "video_url": str | null,
                  "status": str,            # "done" (demo)
                  "created_at": iso str
                }
              ]
            }

        POST /api/generations
          Auth: required
          Body (JSON):
            {
              "model": str,       # required, one of kling|veo|seedance|lipsync
              "fmt": str,         # "vertical" | "horizontal"  (default "vertical")
              "mode": str,        # "standard" | "pro" | "4k"  (default "standard")
              "duration": int,   # 5 | 10  (default 5)
              "sound": bool,      # (default false)
              "prompt": str       # required, max 2500 chars
            }
          Validation: prompt required; 4K+horizontal blocked; 4K forces sound=False
          Response 200:
            {
              "id": int,          # generation ID
              "cost": int,        # deducted amount
              "balance": int,     # new balance
              "video_url": str    # demo placeholder URL
            }
          Response 402: {"error": "insufficient balance: need N, have M"}
          Response 400: validation error

        POST /api/topup
          Auth: required
          Body (JSON): {"amount": int}   # positive integer
          Response 200: {"balance": int, "added": int}
          Response 400: amount must be positive integer

        Static files
        ------------
        GET /              → twa/index.html (Mini App launch page)
        GET /{path}       → twa/{path} (manifest, css, js, icons)
        (aiohttp mounts the TWA static dir on /)
        """)


# ---------------------------------------------------------------------------
# initData auth explanation
# ---------------------------------------------------------------------------

@server.tool()
def get_init_data_auth() -> str:
    """Explain the Telegram initData HMAC-SHA256 validation flow."""
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    src = _source("bot.services.twa_auth")
    return dedent("""\
        Telegram Mini App initData authentication
        =========================================

        Files involved:
          bot/services/twa_auth.py  ← validate_init_data(), TgUser, extract_user()
          bot/api/app.py            ← auth_middleware validates every /api/* request

        Algorithm (bot-token flavour, per Telegram docs):
        -------------------------------------------------
        1. Receive initData string from client (window.Telegram.WebApp.initData).
           It is a URL-encoded query string, e.g.:
             initData=user=%7B%22id%22%3A123...&auth_date=1234567890&hash=abc...

        2. Parse as URL-encoded query string (parse_qs).  Keep all fields EXCEPT
           'hash' and 'signature'.

        3. Build data_check_string:
           - For each remaining key=value pair, sort alphabetically by key
           - Join as "key=value\\n" (one per line, no trailing newline)
           Example result:
             auth_date=1234567890\\n
             user=%7B%22id%22%3A123...%7D

        4. Compute secret_key = HMAC-SHA256(bot_token_bytes, b"WebAppData")

        5. Compute computed_hash = HMAC-SHA256(data_check_string_bytes, secret_key).hexdigest()

        6. Compare computed_hash to received_hash using hmac.compare_digest
           (constant-time to prevent timing attacks).

        7. Freshness check: abs(current_time - auth_date) must be <= ttl_seconds
           (default 3600s).  Set ttl_seconds=0 to disable.

        8. Decode the 'user' field (URL-encoded JSON) into a Python dict and
           construct a TgUser dataclass.

        Security notes:
        - bot_token is the only secret; no extra secrets needed
        - HMAC prevents tampering with any field except hash
        - Freshness check prevents replay of old valid initData
        - hmac.compare_digest prevents timing attacks on the hash comparison

        Usage in the web app (twa/js/app.js):
          - tg.initData is passed as Authorization: tma <initData> header
          - The aiohttp auth_middleware calls validate_init_data()
          - On failure → HTTP 401
        """)


# ---------------------------------------------------------------------------
# Bot commands list
# ---------------------------------------------------------------------------

@server.tool()
def get_bot_commands() -> str:
    """List all bot commands with descriptions."""
    return dedent("""\
        Bot commands and their behavior (bot/handlers/start.py, bot/handlers/mini_app.py)
        ==================================================================================

        User commands (anyone):
        -----------------------
        /start [model]  — main menu.  Optional arg: kling|veo|seedance|lipsync opens that model's card directly.
        /help            — short command reference
        /cancel          — clears FSM state, returns to main menu
        /balance         — shows current balance + topup buttons
        /history         — last 10 generations (model, cost, timestamp, prompt preview)
        /kling           — open Kling 3.0 card + buttons
        /veo             — open VEO 3 card + buttons
        /seedance        — open Seedance 2.0 card + buttons
        /lipsync         — open Lipsync card + buttons
        /examples        — sends a video carousel message with 5 sample videos

        Admin commands (ADMIN_IDS only):
        -------------------------------
        /setmenu   — register/update the Telegram menu button (setChatMenuButton) pointing at TWA_URL
        /menustatus — show current menu button state for this chat
        /menuoff   — reset menu button to default (command list)
        /miniapp   — alias for /setmenu that also re-sends the main menu message
        /setmenu and /miniapp are idempotent; safe to re-run after changing TWA_URL in .env

        Inline callbacks (from inline keyboard buttons):
        ---------------------------------------------
        main            — return to main menu
        examples        — launch the example video carousel
        balance         — show balance card
        history         — show generation history
        topup:<amount>  — add balance (amount: 100 or 500 in demo)
        model:<name>    — pick a model from the menu picker (name: kling|veo|seedance|lipsync)

        Model-specific callbacks (from model card keyboard):
        ---------------------------------------------------
        generate:<model>    — start generation wizard for that model
        lipsync:<model>     — start lipsync wizard for that model
        back:menu           — back to main menu
        back:model:<model>  — back to model card
        back:wizard         — back one step in the wizard FSM
        confirm             — confirm and execute generation (last wizard step)
        skip                — skip optional image step in wizard
        """)


# ---------------------------------------------------------------------------
# Project summary
# ---------------------------------------------------------------------------

@server.tool()
def get_project_summary() -> str:
    """Return a high-level project overview."""
    return dedent(f"""\
        veo_video_bot — Project Summary
        ==============================

        Purpose: Demo Telegram bot + TWA Mini App for AI video generation
                 (Kling, VEO, Seedance, Lipsync models).  Demonstrates a
                 full production-style architecture: FSM wizard, balance system,
                 SQLite persistence, aiohttp REST API, and a JS Mini App.

        Project root: {_ROOT}

        Tech stack
        -----------
        Runtime:     Python 3.10+, aiogram 3.x (Telegram Bot API)
        DB:          SQLAlchemy 2.x + aiosqlite (async SQLite)
        Web API:     aiohttp (single process serves both TWA UI and /api/*)
        Mini App:    Vanilla JS + CSS (twa/index.html, twa/js/app.js)
        MCP:         mcp Python SDK (this server, stdio transport)
        Testing:     pytest + pytest-asyncio

        Architecture
        -------------
        bot.py          — aiogram Dispatcher entry point (polling)
        api.py          — aiohttp entry point (serves TWA + REST API)
        bot/
          config.py      — Config dataclass, all env vars
          database.py    — async SQLAlchemy engine + session_factory
          models.py      — User, Generation ORM models
          handlers/      — aiogram routers (start, menu, generation, lipsync, examples, mini_app)
          services/      — UserService, twa_auth (initData), menu_button (Bot API)
          keyboards/     — CallbackData + InlineKeyboardMarkup builders
          locales/texts.py — all user-facing HTML messages
          api/app.py      — aiohttp web-app (auth middleware + REST endpoints)
          mcp/           — MCP documentation server (this package)
        twa/
          index.html     — Mini App entry point
          js/app.js      — Mini App JS (wizard UI, API client, Telegram SDK wiring)
          css/style.css   — Dark theme styles
          manifest.webmanifest — TWA manifest

        Key flows
        ---------
        - Telegram bot: /start → main menu → model card → generation wizard → demo video
        - Mini App: button in bot opens web_app URL → TWA UI loads → /api/* calls
        - Balance: STARTING_BALANCE=10 on first /start; +100/+500 demo topup; spend on confirm
        - MCP server: stdio transport; tools return full source + docs; no external deps

        Running locally
        ---------------
        Bot:    python bot.py  (BOT_TOKEN required in .env)
        API:    python api.py  (serves http://127.0.0.1:8080 with TWA UI + /api/*)
        MCP:    python -m bot.mcp   OR   mcp run bot.mcp:server
        MCP dev: mcp dev bot.mcp:server   (auto-opens inspector)
        """)


# ---------------------------------------------------------------------------
# Entry-point for `python -m bot.mcp`
# ---------------------------------------------------------------------------

async def main() -> None:
    async with stdio_server(server) as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
