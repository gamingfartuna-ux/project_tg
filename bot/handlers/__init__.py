"""Public handlers exports."""
from aiogram import Router

from bot.handlers import examples, generation, lipsync, menu, mini_app, start


def build_root_router() -> Router:
    """Aggregate all sub-routers in the correct order.

    Order matters:
    * ``start`` — /start etc. (must catch deep links like ``/start kling``)
    * ``mini_app`` — /setmenu, /menuoff, /menustatus, /miniapp (admin)
    * ``menu`` — generic Action callbacks (main, balance, topup, history…)
    * ``generation`` — generation wizard callbacks/messages
    * ``lipsync`` — lipsync FSM (photo → audio)
    * ``examples`` — example carousel

    ``mini_app`` is registered right after ``start`` so admin commands
    resolve before any generic Action callbacks (none of them collide,
    but the explicit ordering is easier to audit later).
    """
    root = Router(name="root")
    root.include_router(start.router)
    root.include_router(mini_app.router)
    root.include_router(menu.router)
    root.include_router(generation.router)
    root.include_router(lipsync.router)
    root.include_router(examples.router)
    return root


__all__ = ["build_root_router"]