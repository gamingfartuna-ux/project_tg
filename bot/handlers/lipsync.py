"""Lipsync wizard: photo face → voice/audio → done."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.filters import ActionFilter
from bot.keyboards import main_menu_kb
from bot.locales import (
    lipsync_awaiting_audio_text,
    lipsync_done_text,
    lipsync_intro_text,
    insufficient_funds_text,
)
from bot.services import UserService
from bot.states.generation import LipsyncStates

router = Router(name="lipsync")

LIPSYNC_COST = 3  # стоимость одной lipsync-генерации


@router.callback_query(ActionFilter(name="start_lipsync"))
async def on_start_lipsync(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()
    if callback.message is None:
        return
    await state.set_state(LipsyncStates.waiting_photo)
    await callback.message.answer(lipsync_intro_text())


@router.message(LipsyncStates.waiting_photo, F.photo)
async def on_lipsync_photo(
    message: Message,
    state: FSMContext,
) -> None:
    if message.photo is None:
        return
    photo_id = message.photo[-1].file_id
    await state.update_data(lipsync_photo_id=photo_id)
    await state.set_state(LipsyncStates.waiting_audio)
    await message.answer(lipsync_awaiting_audio_text())


@router.message(LipsyncStates.waiting_photo)
async def on_lipsync_photo_other(message: Message) -> None:
    await message.answer(
        "Пожалуйста, отправьте фото лица JPG/PNG.",
        reply_markup=main_menu_kb(),
    )


@router.message(LipsyncStates.waiting_audio, F.voice | F.audio)
async def on_lipsync_audio(
    message: Message,
    state: FSMContext,
    service: UserService,
) -> None:
    if message.from_user is None:
        return
    spent = await service.spend(message.from_user.id, LIPSYNC_COST)
    if not spent:
        await state.clear()
        user = await service.get_user(message.from_user.id)
        available = user.balance if user else 0
        await message.answer(
            insufficient_funds_text(LIPSYNC_COST, available),
            reply_markup=main_menu_kb(),
        )
        return
    data = await state.get_data()
    photo_id = data.get("lipsync_photo_id")
    await state.clear()
    gen_id = await service.record_generation(
        user_id=message.from_user.id,
        model="lipsync",
        fmt="vertical",
        mode="standard",
        duration=5,
        sound=True,
        prompt="lipsync",
        image_file_id=photo_id,
        cost=LIPSYNC_COST,
    )
    await message.answer(
        lipsync_done_text(gen_id, LIPSYNC_COST),
        reply_markup=main_menu_kb(),
    )


@router.message(LipsyncStates.waiting_audio)
async def on_lipsync_audio_other(message: Message) -> None:
    await message.answer(
        "Пожалуйста, отправьте голосовое сообщение или аудиофайл.",
        reply_markup=main_menu_kb(),
    )