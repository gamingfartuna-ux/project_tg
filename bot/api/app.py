"""aiohttp web-app that backs the Telegram Mini App.

Endpoints
---------
GET  /api/health           health check (no auth).
GET  /api/me               current user profile + balance (auth).
GET  /api/generations      last N generations of the current user (auth).
POST /api/generations      create a generation, charges ``cost`` from balance.
POST /api/topup            demo top-up, returns new balance.

GET  /api/docs                     doc index (no auth).
GET  /api/docs/handlers/<name>     handler source (no auth).
GET  /api/docs/services/<name>      service source (no auth).
GET  /api/docs/config              config.py source (no auth).
GET  /api/docs/texts               texts.py source (no auth).
GET  /api/docs/wizard-flow         FSM wizard flow (no auth).
GET  /api/docs/miniapp-api         TWA API spec (no auth).
GET  /api/docs/init-data-auth      initData auth explanation (no auth).
GET  /api/docs/bot-commands        bot commands list (no auth).

Authentication: ``Authorization: tma *** header on every non-health
endpoint. ``init_data`` is verified against ``Config.bot_token`` via HMAC-SHA256
(see :mod:`bot.services.twa_auth`).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from aiohttp import web

from bot.config import Config
from bot.locales.texts import MODEL_NAMES, compute_cost
from bot.services import (
    InitDataError,
    TgUser,
    UserService,
    extract_user,
    validate_init_data,
)

log = logging.getLogger(__name__)


# -------- Helpers --------


def _json(data: Any, *, status: int = 200) -> web.Response:
    return web.json_response(data, status=status, dumps=lambda x: json.dumps(x, ensure_ascii=False))


def _error(status: int, message: str) -> web.Response:
    return _json({"error": message}, status=status)


# -------- Middleware --------


@web.middleware
async def auth_middleware(
    request: web.Request,
    handler,
) -> web.StreamResponse:
    """Validate ``Authorization: tma *** and attach ``tg_user`` to request.

    Public endpoints (no auth required):
    - ``/api/health`` — health check;
    - ``/api/docs/*`` — project documentation (static text, no user data);
    - anything that doesn't start with ``/api/`` — static Mini App files
      served from ``twa/`` (the aiohttp app mounts them on ``/``).
    """
    path = request.path
    if path == "/api/health" or path.startswith("/api/docs") or not path.startswith("/api/"):
        return await handler(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("tma "):
        return _error(401, "missing or invalid Authorization header")
    init_data = auth_header[4:].strip()

    config: Config = request.app["config"]
    try:
        parsed = validate_init_data(
            init_data, config.bot_token, ttl_seconds=config.twa_init_data_ttl
        )
        tg_user: TgUser = extract_user(parsed)
    except InitDataError as exc:
        return _error(401, f"init_data invalid: {exc}")

    request["tg_user"] = tg_user
    return await handler(request)


# -------- Handlers --------


async def health(_request: web.Request) -> web.Response:
    return _json({"ok": True})


async def get_me(request: web.Request) -> web.Response:
    tg_user: TgUser = request["tg_user"]
    service: UserService = request.app["service"]

    user = await service.upsert_user(
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
    )
    return _json(
        {
            "id": tg_user.id,
            "first_name": tg_user.first_name,
            "last_name": tg_user.last_name,
            "username": tg_user.username,
            "is_premium": tg_user.is_premium,
            "photo_url": tg_user.photo_url,
            "balance": user.balance,
            "models": MODEL_NAMES,
        }
    )


async def list_generations(request: web.Request) -> web.Response:
    tg_user: TgUser = request["tg_user"]
    service: UserService = request.app["service"]
    try:
        limit = int(request.query.get("limit", "20"))
    except ValueError:
        limit = 20
    limit = max(1, min(limit, 50))

    rows = await service.last_generations(tg_user.id, limit=limit)
    return _json(
        {
            "items": [
                {
                    "id": r.id,
                    "model": r.model,
                    "model_name": MODEL_NAMES.get(r.model, r.model),
                    "fmt": r.fmt,
                    "mode": r.mode,
                    "duration": r.duration,
                    "sound": r.sound,
                    "prompt": r.prompt or "",
                    "cost": r.cost,
                    "video_url": r.video_url,
                    "status": r.status,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]
        }
    )


async def create_generation(request: web.Request) -> web.Response:
    tg_user: TgUser = request["tg_user"]
    service: UserService = request.app["service"]

    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return _error(400, "body is not valid JSON")

    if not isinstance(payload, dict):
        return _error(400, "body must be a JSON object")

    # Validate the generation settings before charging anything.
    model = str(payload.get("model") or "").strip()
    if model not in MODEL_NAMES:
        return _error(400, f"unknown model: {model!r}")
    fmt = str(payload.get("fmt") or "vertical")
    if fmt not in {"vertical", "horizontal"}:
        return _error(400, f"unknown fmt: {fmt!r}")
    mode = str(payload.get("mode") or "standard")
    if mode not in {"standard", "pro", "4k"}:
        return _error(400, f"unknown mode: {mode!r}")
    if mode == "4k" and fmt == "horizontal":
        return _error(400, "4K not available for horizontal format")
    try:
        duration = int(payload.get("duration") or 5)
    except (TypeError, ValueError):
        return _error(400, "duration must be an integer")
    if duration not in {5, 10}:
        return _error(400, "duration must be 5 or 10")
    sound = bool(payload.get("sound") or False)
    if mode == "4k":
        sound = False
    prompt = str(payload.get("prompt") or "").strip()[:2500]
    if not prompt:
        return _error(400, "prompt is required")

    from bot.locales.texts import GenSettings  # local import avoids cycle at module load

    gs = GenSettings(
        model=model,
        fmt=fmt,
        mode=mode,
        duration=duration,
        sound=sound,
        prompt=prompt,
    )
    cost = compute_cost(gs)

    # Make sure the user exists (initData alone doesn't upsert).
    await service.upsert_user(
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
    )

    spent = await service.spend(tg_user.id, cost)
    if not spent:
        user = await service.get_user(tg_user.id)
        available = user.balance if user else 0
        return _error(
            402,
            f"insufficient balance: need {cost}, have {available}",
        )

    # Demo: pick a placeholder video URL the same way the bot wizard does.
    from bot.examples import EXAMPLES

    demo_url = EXAMPLES[0].video_url if EXAMPLES else None

    try:
        gen_id = await service.record_generation(
            user_id=tg_user.id,
            model=gs.model,
            fmt=gs.fmt,
            mode=gs.mode,
            duration=gs.duration,
            sound=gs.sound,
            prompt=gs.prompt,
            image_file_id=None,
            cost=cost,
            video_url=demo_url,
        )
    except Exception as exc:  # pragma: no cover — defensive rollback
        log.exception("record_generation failed: %s", exc)
        await service.refund(tg_user.id, cost)
        return _error(500, "failed to record generation; balance refunded")

    user = await service.get_user(tg_user.id)
    balance = user.balance if user else 0
    return _json(
        {
            "id": gen_id,
            "cost": cost,
            "balance": balance,
            "video_url": demo_url,
        }
    )


async def topup(request: web.Request) -> web.Response:
    tg_user: TgUser = request["tg_user"]
    service: UserService = request.app["service"]

    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return _error(400, "body is not valid JSON")
    if not isinstance(payload, dict):
        return _error(400, "body must be a JSON object")
    try:
        amount = int(payload.get("amount") or 0)
    except (TypeError, ValueError):
        return _error(400, "amount must be an integer")
    if amount <= 0:
        return _error(400, "amount must be positive")

    await service.upsert_user(
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
    )
    try:
        new_balance = await service.add_balance(tg_user.id, amount)
    except ValueError:
        return _error(404, "user not found")
    return _json({"balance": new_balance, "added": amount})


# -------- Documentation endpoints (no auth) --------
# Replicates the core logic from bot.mcp.server without importing the MCP SDK
# (which pulls pywintypes on Windows and is not needed here — all tools are
# plain sync functions returning strings).

import inspect
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent


def _source(mod_name: str, attr: str | None = None) -> str:
    """Return the source code for a module or a named attribute within it."""
    try:
        if str(_ROOT) not in sys.path:
            sys.path.insert(0, str(_ROOT))
        if attr is None:
            obj = __import__(mod_name, fromlist=[""])
            return inspect.getsource(obj)
        obj = __import__(mod_name, fromlist=["_"])
        return inspect.getsource(getattr(obj, attr))
    except (ImportError, AttributeError) as exc:
        return f"[Cannot load source for {mod_name}.{attr}: {exc}]"


_HANDLERS = {
    "start": "bot.handlers.start",
    "menu": "bot.handlers.menu",
    "generation": "bot.handlers.generation",
    "lipsync": "bot.handlers.lipsync",
    "examples": "bot.handlers.examples",
    "mini_app": "bot.handlers.mini_app",
}

_SERVICES = {
    "user_service": "bot.services.user_service",
    "menu_button": "bot.services.menu_button",
    "twa_auth": "bot.services.twa_auth",
}


async def doc_index(_request: web.Request) -> web.Response:
    return _json({"tools": [
        "list_docs", "get_handler", "get_service", "get_config",
        "get_texts", "get_wizard_flow", "get_miniapp_api",
        "get_init_data_auth", "get_bot_commands",
    ]})


async def doc_handler(request: web.Request) -> web.Response:
    name = request.match_info["name"]
    key = name.strip().lower()
    if key not in _HANDLERS:
        return _error(400, f"Unknown handler {name!r}. Available: {', '.join(sorted(_HANDLERS))}")
    return _json({"name": name, "source": _source(_HANDLERS[key])})


async def doc_service(request: web.Request) -> web.Response:
    name = request.match_info["name"]
    key = name.strip().lower()
    if key not in _SERVICES:
        return _error(400, f"Unknown service {name!r}. Available: {', '.join(sorted(_SERVICES))}")
    return _json({"name": name, "source": _source(_SERVICES[key])})


async def doc_config(_request: web.Request) -> web.Response:
    return _json({"source": _source("bot.config")})


async def doc_texts(_request: web.Request) -> web.Response:
    return _json({"source": _source("bot.locales.texts")})


async def doc_wizard_flow(_request: web.Request) -> web.Response:
    text = """\
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
=====================================
State: LipsyncWizard
Steps:
1. wait_face_photo  → user sends a photo (saved as file_id)
2. wait_audio       → user sends voice message or audio file
3. done             → shows lipsync_done_text with demo video

Cost for lipsync = 1 generation (fixed in generation.py step_confirm).
"""
    return _json({"source": text})


async def doc_miniapp_api(_request: web.Request) -> web.Response:
    text = """\
TWA Mini App REST API (served by bot/api/app.py on TWA_API_HOST:TWA_API_PORT)
==============================================================================

Base URL: same origin as the Mini App page (e.g. http://127.0.0.1:8080)

Authentication
--------------
Every /api/* endpoint (except /api/health and /api/docs/*) requires:
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
    {id, first_name, last_name, username, is_premium, photo_url, balance, models}

GET /api/generations?limit=N (default 20, max 50)
  Auth: required
  Response 200: {items: [{id, model, model_name, fmt, mode, duration, sound, prompt, cost, video_url, status, created_at}]}

POST /api/generations
  Auth: required
  Body: {model, fmt, mode, duration, sound, prompt}
  Response 200: {id, cost, balance, video_url}
  Response 402: {"error": "insufficient balance: need N, have M"}

POST /api/topup
  Auth: required
  Body: {amount: int}
  Response 200: {balance, added}

GET /api/docs/* — documentation endpoints (no auth)

Static files: GET / → twa/index.html, GET /<path> → twa/<path>
"""
    return _json({"source": text})


async def doc_init_data_auth(_request: web.Request) -> web.Response:
    return _json({"source": _source("bot.services.twa_auth")})


async def doc_bot_commands(_request: web.Request) -> web.Response:
    text = """\
Bot commands and their behavior
===============================

User commands (anyone):
/start           — greet + main menu with model buttons
/help            — same as /start
/kling           — shortcut: select Kling 3.0 and open generation wizard
/veo             — shortcut: select VEO 3 and open generation wizard
/seedance        — shortcut: select Seedance 2.0 and open generation wizard
/lipsync         — shortcut: start Lipsync wizard (photo → audio)
/examples        — show example video carousel
/balance         — show current balance card
/history         — show last 10 generations
/cancel          — cancel FSM and return to main menu

Admin commands (ADMIN_IDS only):
/setmenu         — register/update the Mini App menu button
/miniapp         — same as /setmenu + re-render main menu
/menustatus      — show current menu button state
/menuoff         — reset menu button to default commands list
"""
    return _json({"source": text})


# -------- App factory --------


def build_app(config: Config, service: UserService) -> web.Application:
    app = web.Application(middlewares=[auth_middleware])
    app["config"] = config
    app["service"] = service

    app.router.add_get("/api/health", health)
    app.router.add_get("/api/me", get_me)
    app.router.add_get("/api/generations", list_generations)
    app.router.add_post("/api/generations", create_generation)
    app.router.add_post("/api/topup", topup)

    # Documentation endpoints (no auth)
    app.router.add_get("/api/docs", doc_index)
    app.router.add_get("/api/docs/handlers/{name}", doc_handler)
    app.router.add_get("/api/docs/services/{name}", doc_service)
    app.router.add_get("/api/docs/config", doc_config)
    app.router.add_get("/api/docs/texts", doc_texts)
    app.router.add_get("/api/docs/wizard-flow", doc_wizard_flow)
    app.router.add_get("/api/docs/miniapp-api", doc_miniapp_api)
    app.router.add_get("/api/docs/init-data-auth", doc_init_data_auth)
    app.router.add_get("/api/docs/bot-commands", doc_bot_commands)

    # ---- Mini App static files ----
    # Один процесс ``python api.py`` отдаёт и TWA-UI, и API. Без этого
    # пришлось бы держать параллельно ``python -m http.server 8080`` для
    # фронта — а это конфликт портов с API.
    static_dir = Path(config.twa_static_dir)
    if static_dir.is_dir():
        # Корень: ``GET /`` → twa/index.html (Mini App launch URL).
        index_path = static_dir / "index.html"
        if index_path.is_file():
            app.router.add_get("/", _serve_index_factory(str(index_path)))
            # Совместимость со старым ``TWA_URL=.../index.html``.
            app.router.add_get("/index.html", _serve_index_factory(str(index_path)))

        # ``GET /<sub>`` → twa/<sub> (manifest, css, js, icons).
        async def _serve_static(request: web.Request) -> web.StreamResponse:
            rel = request.match_info["path"]
            # aiohttp нормализует, но всё равно блокируем выход за пределы
            # static_dir через resolve + is_relative_to.
            target = (static_dir / rel).resolve()
            if not target.is_file() or not target.is_relative_to(static_dir.resolve()):
                raise web.HTTPNotFound()
            return web.FileResponse(target)

        app.router.add_get("/{path:.*}", _serve_static)
        log.info("TWA static files served from %s", static_dir)
    else:
        log.warning(
            "TWA static dir %s does not exist — Mini App UI will 404. "
            "Set TWA_STATIC_DIR or keep the default ./twa directory.",
            static_dir,
        )

    return app


def _serve_index_factory(index_path: str):
    """Return a request handler that streams ``index.html``.

    Using a closure keeps the file path captured without needing to parse
    ``config`` inside the handler — simpler than threading ``request.app[...]``
    through.
    """

    async def _handler(_request: web.Request) -> web.FileResponse:
        return web.FileResponse(index_path)

    return _handler