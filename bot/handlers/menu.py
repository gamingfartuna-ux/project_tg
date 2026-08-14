"""Inline-callback handlers for menu, model picker and back-navigation."""

from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.config import Config
from bot.filters import ActionFilter
from bot.keyboards import (
    Action,
    ModelPick,
    balance_kb,
    history_kb,
    main_menu_kb,
    model_card_kb,
)
from bot.locales import (
    balance_text,
    history_text,
    main_menu_text,
    model_card_text,
    topup_text,
)
from bot.services import UserService

router = Router(name="menu")


@router.callback_query(ModelPick.filter())
async def on_model_pick(
    callback: CallbackQuery,
    callback_data: ModelPick,
) -> None:
    await callback.answer()
    if callback.message is None:
        return
    await callback.message.edit_text(
        model_card_text(callback_data.model),
        reply_markup=model_card_kb(callback_data.model),
    )


@router.callback_query(ActionFilter(name="main"))
async def on_main(
    callback: CallbackQuery,
    state: FSMContext,
    config: Config,
) -> None:
    await state.clear()
    await callback.answer()
    if callback.message is None:
        return
    try:
        await callback.message.edit_text(
            main_menu_text(),
            reply_markup=main_menu_kb(twa_url=config.twa_url),
        )
    except Exception:
        # если сообщение не наше (например, после фото) — отправим новое
        await callback.message.answer(
            main_menu_text(),
            reply_markup=main_menu_kb(twa_url=config.twa_url),
        )


@router.callback_query(ActionFilter(name="examples"))
async def on_examples(
    callback: CallbackQuery,
) -> None:
    from bot.examples import example_count, get_example
    from bot.keyboards import example_card_kb
    from bot.locales import example_card_text

    await callback.answer()
    if callback.message is None:
        return
    ex = get_example(0)
    if ex is None:
        await callback.message.edit_text("Примеры скоро появятся.")
        return
    total = example_count()
    await callback.message.answer_video(
        video=ex.video_url,
        caption=example_card_text(0, ex.title, ex.prompt),
        reply_markup=example_card_kb(0, total),
    )


@router.callback_query(ActionFilter(name="balance"))
async def on_balance(
    callback: CallbackQuery,
    service: UserService,
) -> None:
    await callback.answer()
    if callback.message is None or callback.from_user is None:
        return
    user = await service.get_user(callback.from_user.id)
    balance = user.balance if user else 0
    try:
        await callback.message.edit_text(
            balance_text(balance),
            reply_markup=balance_kb(balance),
        )
    except Exception:
        await callback.message.answer(
            balance_text(balance),
            reply_markup=balance_kb(balance),
        )


@router.callback_query(ActionFilter(name="topup"))
async def on_topup(
    callback: CallbackQuery,
    callback_data: Action,
    service: UserService,
) -> None:
    await callback.answer()
    if callback.message is None or callback.from_user is None:
        return
    try:
        amount = int(callback_data.payload or "0")
    except ValueError:
        amount = 0
    if amount <= 0:
        await callback.answer("Некорректная сумма", show_alert=True)
        return
    try:
        new_balance = await service.add_balance(callback.from_user.id, amount)
    except ValueError:
        # пользователь ещё не нажал /start
        await callback.message.answer(
            "Сначала нажмите /start",
            reply_markup=main_menu_kb(),
        )
        return
    await callback.message.edit_text(
        topup_text(new_balance, amount),
        reply_markup=balance_kb(new_balance),
    )


@router.callback_query(ActionFilter(name="history"))
async def on_history(
    callback: CallbackQuery,
    service: UserService,
) -> None:
    await callback.answer()
    if callback.message is None or callback.from_user is None:
        return
    rows = await service.last_generations(callback.from_user.id, limit=10)
    text = history_text(list(rows))
    has_items = bool(rows)
    try:
        await callback.message.edit_text(
            text,
            reply_markup=history_kb(has_items),
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=history_kb(has_items),
        )