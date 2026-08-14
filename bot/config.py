"""Bot + TWA API configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _default_twa_static_dir() -> str:
    """Resolve the TWA static directory relative to the project root.

    ``bot/config.py`` lives at ``<root>/bot/config.py`` — the TWA folder is a
    sibling (``<root>/twa``). We compute it from ``__file__`` so it works
    regardless of the current working directory when ``bot.py`` is launched.
    """
    return str(Path(__file__).resolve().parent.parent / "twa")


@dataclass(frozen=True)
class Config:
    """Bot configuration. All sensitive values come from environment."""

    bot_token: str = ""
    admin_ids: tuple[int, ...] = field(default_factory=tuple)
    database_url: str = "sqlite+aiosqlite:///./veo_video_bot.db"
    twa_url: str = "https://t.me/VideoVeoBot"  # used as fallback if no TWA host

    # TWA API (aiohttp web-app)
    twa_api_host: str = os.getenv("TWA_API_HOST", "127.0.0.1")
    twa_api_port: int = int(os.getenv("PORT", os.getenv("TWA_API_PORT", "8080")))  # Railway injects PORT
    # Comma-separated list of origins allowed to call the TWA API via CORS.
    # By default the API only accepts Authorization: tma *** from any
    # origin (CORS preflight not required for Bearer-style auth). This list is
    # informational and only used to validate X-TWA-Origin header when set.
    twa_allowed_origins: tuple[str, ...] = field(default_factory=tuple)
    # Max age of initData (seconds) — anything older is rejected.
    twa_init_data_ttl: int = 3600
    # Filesystem path to the TWA static folder (``twa/index.html`` etc.).
    # The aiohttp app in ``bot/api/app.py`` mounts it on ``/`` so a single
    # ``python api.py`` process serves both the Mini App UI and ``/api/*``.
    twa_static_dir: str = field(default_factory=_default_twa_static_dir)

    @classmethod
    def from_env(cls) -> "Config":
        token = os.getenv("BOT_TOKEN", "").strip()
        admin_raw = os.getenv("ADMIN_IDS", "").strip()
        admin_ids: tuple[int, ...] = tuple(
            int(x) for x in admin_raw.split(",") if x.strip().isdigit()
        )
        origins_raw = os.getenv("TWA_ALLOWED_ORIGINS", "").strip()
        origins = tuple(
            o.strip() for o in origins_raw.split(",") if o.strip()
        )
        return cls(
            bot_token=token,
            admin_ids=admin_ids,
            database_url=os.getenv("DATABASE_URL", cls.database_url),
            twa_url=os.getenv("TWA_URL", cls.twa_url),
            twa_api_host=os.getenv("TWA_API_HOST", cls.twa_api_host),
            twa_api_port=int(os.getenv("TWA_API_PORT", str(cls.twa_api_port))),
            twa_allowed_origins=origins,
            twa_init_data_ttl=int(
                os.getenv("TWA_INIT_DATA_TTL", str(cls.twa_init_data_ttl))
            ),
            twa_static_dir=os.getenv("TWA_STATIC_DIR", _default_twa_static_dir()),
        )

    @property
    def has_token(self) -> bool:
        return bool(self.bot_token)