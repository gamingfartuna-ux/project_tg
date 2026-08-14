"""Start, help and main menu handlers."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.config import Config
from bot.keyboards import main_menu_kb
from bot.locales import main_menu_text, model_card_text, MODEL_NAMES, MODEL_DESCRIPTIONS
from bot.services import UserService

router = Router(name="start")


@router.message(Command("start"))
async def cmd_start(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    config: Config,
    service: UserService,
) -> None:
    await state.clear()
    if message.from_user is None:
        return
    await service.upsert_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    # deep-link: /start kling → сразу карточка модели
    args = (command.args or "").strip().lower()
    if args in {"kling", "veo", "seedance", "lipsync"}:
        from bot.keyboards import model_card_kb
        await message.answer(
            model_card_text(args),
            reply_markup=model_card_kb(args),
        )
        return
    await message.answer(
        main_menu_text(),
        reply_markup=main_menu_kb(twa_url=config.twa_url),
    )


@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "🤖 <b>VideoVeoBot — демо</b>\n\n"
        "/start — главное меню\n"
        "/kling, /veo, /seedance, /lipsync — открыть модель\n"
        "/examples — посмотреть примеры генераций\n"
        "/balance — текущий баланс и пополнить\n"
        "/history — последние 10 генераций\n"
        "/cancel — прервать текущую настройку"
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Окей, сбросил. Возвращаюсь в главное меню.",
                         reply_markup=main_menu_kb())


@router.message(Command("balance"))
async def cmd_balance(
    message: Message,
    state: FSMContext,
    service: UserService,
) -> None:
    await state.clear()
    if message.from_user is None:
        return
    from bot.keyboards import balance_kb
    from bot.locales import balance_text

    user = await service.upsert_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    await message.answer(
        balance_text(user.balance),
        reply_markup=balance_kb(user.balance),
    )


@router.message(Command("history"))
async def cmd_history(
    message: Message,
    state: FSMContext,
    service: UserService,
) -> None:
    await state.clear()
    if message.from_user is None:
        return
    from bot.keyboards import history_kb
    from bot.locales import history_text

    rows = await service.last_generations(message.from_user.id, limit=10)
    await message.answer(
        history_text(list(rows)),
        reply_markup=history_kb(bool(rows)),
    )


# Shortcut commands for models
async def _open_model(message: Message, model: str) -> None:
    from bot.keyboards import model_card_kb
    if model not in MODEL_NAMES:
        await message.answer("Неизвестная модель.")
        return
    await message.answer(model_card_text(model), reply_markup=model_card_kb(model))


@router.message(Command("kling"))
async def cmd_kling(message: Message) -> None:
    await _open_model(message, "kling")


@router.message(Command("veo"))
async def cmd_veo(message: Message) -> None:
    await _open_model(message, "veo")


@router.message(Command("seedance"))
async def cmd_seedance(message: Message) -> None:
    await _open_model(message, "seedance")


@router.message(Command("lipsync"))
async def cmd_lipsync(message: Message) -> None:
    await _open_model(message, "lipsync")