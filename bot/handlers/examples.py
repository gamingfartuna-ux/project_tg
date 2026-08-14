"""Example carousel: /examples command and inline navigation."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.examples import EXAMPLES, example_count, get_example
from bot.keyboards import ExamplePick, example_card_kb
from bot.locales import example_card_text

router = Router(name="examples")


@router.message(Command("examples"))
async def cmd_examples(message: Message) -> None:
    if not EXAMPLES:
        await message.answer("Примеры скоро появятся.")
        return
    ex = get_example(0)
    assert ex is not None
    await message.answer_video(
        video=ex.video_url,
        caption=example_card_text(0, ex.title, ex.prompt),
        reply_markup=example_card_kb(0, example_count()),
    )


@router.callback_query(ExamplePick.filter())
async def on_example_nav(
    callback: CallbackQuery,
    callback_data: ExamplePick,
) -> None:
    await callback.answer()
    if callback.message is None:
        return
    idx = callback_data.index
    direction = callback_data.direction
    total = example_count()
    if direction == "hide":
        try:
            await callback.message.delete()
        except Exception:
            pass
        return
    if direction == "next" and idx < total - 1:
        idx += 1
    elif direction == "prev" and idx > 0:
        idx -= 1
    ex = get_example(idx)
    if ex is None:
        return
    try:
        await callback.message.edit_media(
            media=InputMediaVideo(media=ex.video_url, caption=ex.prompt[:1024]),
            reply_markup=example_card_kb(idx, total),
        )
    except Exception:
        # fallback: send new
        await callback.message.answer_video(
            video=ex.video_url,
            caption=example_card_text(idx, ex.title, ex.prompt),
            reply_markup=example_card_kb(idx, total),
        )