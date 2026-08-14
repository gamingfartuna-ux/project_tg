"""Generation wizard: format → mode → duration → sound → image → prompt → confirm."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InputMediaVideo,
    Message,
)

from bot.filters import ActionFilter
from bot.keyboards import (
    DurationPick,
    FormatPick,
    ModePick,
    SoundPick,
    confirm_kb,
    confirm_with_balance_kb,
    duration_kb,
    format_kb,
    image_kb,
    mode_kb,
    prompt_kb,
    sound_kb,
)
from bot.locales import (
    GenSettings,
    confirm_text,
    done_text,
    duration_text,
    format_text,
    image_text,
    insufficient_funds_text,
    mode_text,
    prompt_text,
    sound_text,
)
from bot.services import UserService
from bot.states.generation import GenerationStates

router = Router(name="generation")


# -------- Entry point --------


@router.callback_query(ActionFilter(name="start_gen"))
async def on_start_gen(
    callback: CallbackQuery,
    callback_data: Action,
    state: FSMContext,
) -> None:
    """Запуск wizard после выбора модели."""
    model = callback_data.payload or "kling"
    await callback.answer()
    if callback.message is None:
        return
    gs = GenSettings(model=model)
    await state.update_data(gs=gs)
    await state.set_state(GenerationStates.choosing_format)
    await callback.message.edit_text(format_text(), reply_markup=format_kb())


@router.callback_query(ActionFilter(name="back_format"))
async def on_back_format(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()
    if callback.message is None:
        return
    await state.set_state(GenerationStates.choosing_format)
    await callback.message.edit_text(format_text(), reply_markup=format_kb())


# -------- Format --------


@router.callback_query(GenerationStates.choosing_format, FormatPick.filter())
async def on_format(
    callback: CallbackQuery,
    callback_data: FormatPick,
    state: FSMContext,
) -> None:
    await callback.answer()
    if callback.message is None:
        return
    raw = await state.get_data()
    gs: GenSettings = raw.get("gs") or GenSettings()
    gs.fmt = callback_data.fmt
    await state.update_data(gs=gs)
    await state.set_state(GenerationStates.choosing_mode)
    await callback.message.edit_text(
        mode_text(gs.fmt),
        reply_markup=mode_kb(gs.fmt),
    )


# -------- Mode --------


@router.callback_query(GenerationStates.choosing_mode, ModePick.filter())
async def on_mode(
    callback: CallbackQuery,
    callback_data: ModePick,
    state: FSMContext,
) -> None:
    await callback.answer()
    if callback.message is None:
        return
    raw = await state.get_data()
    gs: GenSettings = raw.get("gs") or GenSettings()
    gs.mode = callback_data.mode
    if gs.mode == "4k":
        gs.sound = False  # звук в 4K недоступен
    await state.update_data(gs=gs)
    await state.set_state(GenerationStates.choosing_duration)
    await callback.message.edit_text(duration_text(), reply_markup=duration_kb())


@router.callback_query(ActionFilter(name="back_mode"))
async def on_back_mode(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()
    if callback.message is None:
        return
    raw = await state.get_data()
    gs: GenSettings = raw.get("gs") or GenSettings()
    await state.set_state(GenerationStates.choosing_mode)
    await callback.message.edit_text(
        mode_text(gs.fmt),
        reply_markup=mode_kb(gs.fmt),
    )


# -------- Duration --------


@router.callback_query(GenerationStates.choosing_duration, DurationPick.filter())
async def on_duration(
    callback: CallbackQuery,
    callback_data: DurationPick,
    state: FSMContext,
) -> None:
    await callback.answer()
    if callback.message is None:
        return
    raw = await state.get_data()
    gs: GenSettings = raw.get("gs") or GenSettings()
    gs.duration = callback_data.seconds
    await state.update_data(gs=gs)
    await state.set_state(GenerationStates.choosing_sound)
    await callback.message.edit_text(sound_text(gs.sound), reply_markup=sound_kb(gs.sound))


@router.callback_query(ActionFilter(name="back_duration"))
async def on_back_duration(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()
    if callback.message is None:
        return
    await state.set_state(GenerationStates.choosing_duration)
    await callback.message.edit_text(duration_text(), reply_markup=duration_kb())


# -------- Sound --------


@router.callback_query(GenerationStates.choosing_sound, SoundPick.filter())
async def on_sound(
    callback: CallbackQuery,
    callback_data: SoundPick,
    state: FSMContext,
) -> None:
    await callback.answer()
    if callback.message is None:
        return
    raw = await state.get_data()
    gs: GenSettings = raw.get("gs") or GenSettings()
    gs.sound = callback_data.on
    await state.update_data(gs=gs)
    await state.set_state(GenerationStates.waiting_image)
    await callback.message.edit_text(image_text(), reply_markup=image_kb())


@router.callback_query(ActionFilter(name="back_sound"))
async def on_back_sound(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()
    if callback.message is None:
        return
    raw = await state.get_data()
    gs: GenSettings = raw.get("gs") or GenSettings()
    await state.set_state(GenerationStates.choosing_sound)
    await callback.message.edit_text(sound_text(gs.sound), reply_markup=sound_kb(gs.sound))


# -------- Image --------


@router.callback_query(GenerationStates.waiting_image, ActionFilter(name="skip_image"))
async def on_skip_image(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()
    if callback.message is None:
        return
    raw = await state.get_data()
    gs: GenSettings = raw.get("gs") or GenSettings()
    gs.image_attached = False
    await state.update_data(gs=gs)
    await state.set_state(GenerationStates.waiting_prompt)
    await callback.message.edit_text(
        prompt_text(gs.image_attached),
        reply_markup=prompt_kb(),
    )


@router.callback_query(GenerationStates.waiting_image, ActionFilter(name="back_image"))
async def on_back_image(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    # used as "back" from prompt screen → returns to image screen
    await callback.answer()
    if callback.message is None:
        return
    await state.set_state(GenerationStates.waiting_image)
    await callback.message.edit_text(image_text(), reply_markup=image_kb())


@router.message(GenerationStates.waiting_image, F.photo)
async def on_image_photo(
    message: Message,
    state: FSMContext,
) -> None:
    if message.from_user is None or message.photo is None:
        return
    raw = await state.get_data()
    gs: GenSettings = raw.get("gs") or GenSettings()
    gs.image_attached = True
    gs.image_file_id = message.photo[-1].file_id  # максимальное разрешение
    await state.update_data(gs=gs)
    await state.set_state(GenerationStates.waiting_prompt)
    await message.answer(prompt_text(True), reply_markup=prompt_kb())


@router.message(GenerationStates.waiting_image)
async def on_image_other(
    message: Message,
    state: FSMContext,
) -> None:
    """Если прислали не фото — подсказка."""
    await state.set_state(GenerationStates.waiting_image)
    await message.answer(
        "Отправьте JPG/PNG картинку или нажмите «Пропустить изображение».",
        reply_markup=image_kb(),
    )


# -------- Prompt --------


@router.message(GenerationStates.waiting_prompt, F.text)
async def on_prompt(
    message: Message,
    state: FSMContext,
    service: UserService,
) -> None:
    if message.text is None or message.from_user is None:
        return
    text = message.text.strip()
    if not text:
        await message.answer("Промпт пустой — опишите, что должно произойти в видео.")
        return
    raw = await state.get_data()
    gs: GenSettings = raw.get("gs") or GenSettings()
    gs.prompt = text[:2500]
    await state.update_data(gs=gs)
    await state.set_state(GenerationStates.confirming)
    cost = compute_cost(gs)
    user = await service.get_user(message.from_user.id)
    balance = user.balance if user else 0
    await message.answer(
        confirm_text(gs) + "\n\n"
        + (f"💰 Баланс: <b>{balance}</b> генераций" if user else ""),
        reply_markup=confirm_with_balance_kb(balance >= cost, cost),
    )


@router.callback_query(GenerationStates.confirming, ActionFilter(name="edit_prompt"))
async def on_edit_prompt(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()
    if callback.message is None:
        return
    await state.set_state(GenerationStates.waiting_prompt)
    await callback.message.edit_text(prompt_text(False), reply_markup=prompt_kb())


@router.callback_query(GenerationStates.confirming, ActionFilter(name="confirm"))
async def on_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    service: UserService,
) -> None:
    if callback.message is None or callback.from_user is None:
        return
    raw = await state.get_data()
    gs: GenSettings = raw.get("gs") or GenSettings()
    cost = compute_cost(gs)

    spent = await service.spend(callback.from_user.id, cost)
    if not spent:
        await callback.answer("Недостаточно генераций", show_alert=True)
        user = await service.get_user(callback.from_user.id)
        balance = user.balance if user else 0
        await callback.message.edit_text(
            insufficient_funds_text(cost, balance),
            reply_markup=confirm_with_balance_kb(False, cost),
        )
        return

    await callback.answer("Запускаю генерацию…")
    await state.clear()

    # Демо: выбираем placeholder-MP4 соответствующий примеру, если был
    from bot.examples import EXAMPLES

    demo_url = EXAMPLES[0].video_url if EXAMPLES else None
    try:
        gen_id = await service.record_generation(
            user_id=callback.from_user.id,
            model=gs.model,
            fmt=gs.fmt,
            mode=gs.mode,
            duration=gs.duration,
            sound=gs.sound,
            prompt=gs.prompt,
            image_file_id=gs.image_file_id if hasattr(gs, "image_file_id") else None,
            cost=cost,
            video_url=demo_url,
        )
    except Exception:
        gen_id = 0

    from bot.keyboards import reset_kb

    user = await service.get_user(callback.from_user.id)
    new_balance = user.balance if user else 0
    await callback.message.edit_text(
        done_text(gs, gen_id) + f"\n\n💰 Остаток: <b>{new_balance}</b> генераций",
        reply_markup=reset_kb(),
    )


# -------- Examples navigation --------


@router.callback_query(ActionFilter(name="copy_prompt"))
async def on_copy_prompt(
    callback: CallbackQuery,
    callback_data: Action,
) -> None:
    from bot.examples import get_example
    idx = int(callback_data.payload or "0")
    ex = get_example(idx)
    if ex is None:
        await callback.answer("Не найдено", show_alert=True)
        return
    await callback.answer("Промпт показан выше — выделите и скопируйте", show_alert=True)


@router.callback_query(ActionFilter(name="from_example"))
async def on_from_example(
    callback: CallbackQuery,
    callback_data: Action,
    state: FSMContext,
) -> None:
    """Запуск wizard с подставленным промптом из примера."""
    from bot.examples import get_example
    await callback.answer()
    if callback.message is None:
        return
    idx = int(callback_data.payload or "0")
    ex = get_example(idx)
    if ex is None:
        return
    gs = GenSettings(model="kling", prompt=ex.prompt[:2500])
    await state.update_data(gs=gs)
    await state.set_state(GenerationStates.choosing_format)
    try:
        await callback.message.edit_text(format_text(), reply_markup=format_kb())
    except Exception:
        await callback.message.answer(format_text(), reply_markup=format_kb())