"""Callback data factories and keyboards."""

from __future__ import annotations

from urllib.parse import urlparse

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder


def _is_valid_web_app_url(url: str | None) -> bool:
    """Telegram открывает ``web_app``-кнопку только для HTTPS (или localhost
    в dev-режиме). Для остальных схем показывать кнопку бесполезно —
    клиент её проигнорирует, и пользователь увидит «пересылает в браузер».
    """
    if not url:
        return False
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        return False
    host = parsed.hostname or ""
    if parsed.scheme == "https":
        return True
    # http:// допускаем только для localhost / 127.0.0.1 / ::1 в dev.
    return host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


def _append_param(url: str, key: str, value: str) -> str:
    """Append or replace a query param to a URL."""
    from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    qs[key] = [value]
    return urlunparse((
        parsed.scheme, parsed.netloc, parsed.path,
        parsed.params, urlencode(qs, doseq=True), parsed.fragment
    ))


# -------- CallbackData schemas --------


class ModelPick(CallbackData, prefix="m"):
    model: str  # kling | veo | seedance | lipsync


class FormatPick(CallbackData, prefix="fmt"):
    fmt: str  # vertical | horizontal


class ModePick(CallbackData, prefix="mode"):
    mode: str  # standard | pro | 4k


class DurationPick(CallbackData, prefix="dur"):
    seconds: int  # 5 | 10


class SoundPick(CallbackData, prefix="snd"):
    on: bool


class Action(CallbackData, prefix="act"):
    """Generic actions: reset, confirm, skip_image, examples, etc.

    Filtering by ``name`` is done via a dedicated callback-data filter
    (see :func:`bot.filters.action.ActionFilter`) instead of using
    ``CallbackData.filter(name=...)`` — aiogram 3.x does not allow
    matching on schema fields that way.
    """

    name: str
    payload: str = ""


class ExamplePick(CallbackData, prefix="ex"):
    index: int
    direction: str = "stay"  # stay | prev | next | hide


# -------- Menus --------


def main_menu_kb(twa_url: str | None = None) -> InlineKeyboardMarkup:
    """Главное меню — повторяет стиль реального VideoVeoBot."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🔥 Kling 3.0",
            callback_data=ModelPick(model="kling").pack(),
        ),
        InlineKeyboardButton(
            text="🎬 VEO 3",
            callback_data=ModelPick(model="veo").pack(),
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🌀 Seedance",
            callback_data=ModelPick(model="seedance").pack(),
        ),
        InlineKeyboardButton(
            text="👄 Lipsync",
            callback_data=ModelPick(model="lipsync").pack(),
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🎬 Посмотреть примеры",
            callback_data=Action(name="examples").pack(),
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="💰 Баланс",
            callback_data=Action(name="balance").pack(),
        ),
        InlineKeyboardButton(
            text="📜 История",
            callback_data=Action(name="history").pack(),
        ),
    )
    if twa_url and _is_valid_web_app_url(twa_url):
        builder.row(
            InlineKeyboardButton(
                text="📱 Открыть Mini App",
                web_app=WebAppInfo(url=twa_url),
            ),
        )
        # Кнопка «Справка» открывает Mini App сразу на экране help
        help_url = _append_param(twa_url, "screen", "help")
        builder.row(
            InlineKeyboardButton(
                text="❓ Справка по боту",
                web_app=WebAppInfo(url=help_url),
            ),
        )
    return builder.as_markup()


def model_card_kb(model: str) -> InlineKeyboardMarkup:
    """Карточка выбранной модели — кнопки запуска и смены модели."""
    builder = InlineKeyboardBuilder()
    if model == "lipsync":
        builder.row(
            InlineKeyboardButton(
                text="🎬 Запустить Lipsync",
                callback_data=Action(name="start_lipsync").pack(),
            ),
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="🎬 Сгенерировать видео",
                callback_data=Action(name="start_gen", payload=model).pack(),
            ),
        )
    builder.row(
        InlineKeyboardButton(
            text="↩️ Назад к моделям",
            callback_data=Action(name="main").pack(),
        ),
    )
    return builder.as_markup()


def format_kb() -> InlineKeyboardMarkup:
    """Выбор формата видео: вертикальный / горизонтальный."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Вертикальный\n9:16 — Reels / TikTok / Shorts",
            callback_data=FormatPick(fmt="vertical").pack(),
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="Горизонтальный\n16:9 — YouTube / веб",
            callback_data=FormatPick(fmt="horizontal").pack(),
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="↩️ Назад",
            callback_data=Action(name="main").pack(),
        ),
    )
    return builder.as_markup()


def mode_kb(fmt: str) -> InlineKeyboardMarkup:
    """Режим генерации. 4K недоступен при горизонтальном формате (пример)."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Standard\n1 ген / 5 сек",
            callback_data=ModePick(mode="standard").pack(),
        ),
        InlineKeyboardButton(
            text="Pro\n2 ген / 5 сек",
            callback_data=ModePick(mode="pro").pack(),
        ),
    )
    four_k_text = "4K\n4 ген / 5 сек"
    if fmt == "horizontal":
        four_k_text = "4K (недоступен)"
    builder.row(
        InlineKeyboardButton(
            text=four_k_text,
            callback_data=ModePick(mode="4k").pack(),
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="↩️ Назад",
            callback_data=Action(name="back_format").pack(),
        ),
    )
    return builder.as_markup()


def duration_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="5 секунд",
            callback_data=DurationPick(seconds=5).pack(),
        ),
        InlineKeyboardButton(
            text="10 секунд",
            callback_data=DurationPick(seconds=10).pack(),
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="↩️ Назад",
            callback_data=Action(name="back_mode").pack(),
        ),
    )
    return builder.as_markup()


def sound_kb(current: bool) -> InlineKeyboardMarkup:
    label = "🔊 Включён" if current else "🔇 Выключен"
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"Сгенерировать звук — {label}",
            callback_data=SoundPick(on=not current).pack(),
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="↩️ Назад",
            callback_data=Action(name="back_duration").pack(),
        ),
    )
    return builder.as_markup()


def image_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="⏭ Пропустить изображение",
            callback_data=Action(name="skip_image").pack(),
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="↩️ Назад",
            callback_data=Action(name="back_sound").pack(),
        ),
    )
    return builder.as_markup()


def prompt_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="↩️ Назад",
            callback_data=Action(name="back_image").pack(),
        ),
    )
    return builder.as_markup()


def confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Запустить генерацию",
            callback_data=Action(name="confirm").pack(),
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="✏️ Изменить промпт",
            callback_data=Action(name="edit_prompt").pack(),
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="↩️ В начало",
            callback_data=Action(name="main").pack(),
        ),
    )
    return builder.as_markup()


def example_card_kb(index: int, total: int) -> InlineKeyboardMarkup:
    """Карточка примера: prev / next / hide + copy prompt."""
    builder = InlineKeyboardBuilder()
    nav_row: list[InlineKeyboardButton] = []
    if index > 0:
        nav_row.append(
            InlineKeyboardButton(
                text="← Назад",
                callback_data=ExamplePick(index=index, direction="prev").pack(),
            )
        )
    nav_row.append(
        InlineKeyboardButton(
            text=f"{index + 1}/{total}",
            callback_data=ExamplePick(index=index, direction="stay").pack(),
        )
    )
    if index < total - 1:
        nav_row.append(
            InlineKeyboardButton(
                text="Далее →",
                callback_data=ExamplePick(index=index, direction="next").pack(),
            )
        )
    builder.row(*nav_row)
    builder.row(
        InlineKeyboardButton(
            text="📋 Скопировать промпт",
            callback_data=Action(name="copy_prompt", payload=str(index)).pack(),
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🎬 Сгенерировать похожее",
            callback_data=Action(name="from_example", payload=str(index)).pack(),
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="Скрыть",
            callback_data=ExamplePick(index=index, direction="hide").pack(),
        ),
    )
    return builder.as_markup()


def reset_kb() -> InlineKeyboardMarkup:
    """Кнопка возврата в главное меню после ошибки."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="↩️ В главное меню",
            callback_data=Action(name="main").pack(),
        ),
    )
    return builder.as_markup()


def balance_kb(current_balance: int) -> InlineKeyboardMarkup:
    """Карточка баланса: +100 (демо-пополнение), история, назад."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="+ 100 генераций (демо)",
            callback_data=Action(name="topup", payload=str(100)).pack(),
        ),
        InlineKeyboardButton(
            text="+ 500 генераций",
            callback_data=Action(name="topup", payload=str(500)).pack(),
        ),
    )
    if current_balance == 0:
        builder.row(
            InlineKeyboardButton(
                text="🚨 Баланс 0 — пополнить 50",
                callback_data=Action(name="topup", payload=str(50)).pack(),
            ),
        )
    builder.row(
        InlineKeyboardButton(
            text="📜 Открыть историю",
            callback_data=Action(name="history").pack(),
        ),
        InlineKeyboardButton(
            text="🎬 К моделям",
            callback_data=Action(name="main").pack(),
        ),
    )
    return builder.as_markup()


def history_kb(has_items: bool) -> InlineKeyboardMarkup:
    """Кнопки под историей генераций."""
    builder = InlineKeyboardBuilder()
    if has_items:
        builder.row(
            InlineKeyboardButton(
                text="🔄 Сгенерировать ещё",
                callback_data=Action(name="main").pack(),
            ),
        )
    builder.row(
        InlineKeyboardButton(
            text="💰 Баланс",
            callback_data=Action(name="balance").pack(),
        ),
        InlineKeyboardButton(
            text="↩️ В главное меню",
            callback_data=Action(name="main").pack(),
        ),
    )
    return builder.as_markup()


def confirm_with_balance_kb(can_afford: bool, cost: int) -> InlineKeyboardMarkup:
    """Подтверждение генерации с учётом баланса."""
    builder = InlineKeyboardBuilder()
    if can_afford:
        builder.row(
            InlineKeyboardButton(
                text=f"✅ Списать {cost} и запустить",
                callback_data=Action(name="confirm").pack(),
            ),
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text=f"💰 Пополнить баланс ({cost} нужно)",
                callback_data=Action(name="balance").pack(),
            ),
        )
    builder.row(
        InlineKeyboardButton(
            text="✏️ Изменить промпт",
            callback_data=Action(name="edit_prompt").pack(),
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="↩️ В начало",
            callback_data=Action(name="main").pack(),
        ),
    )
    return builder.as_markup()