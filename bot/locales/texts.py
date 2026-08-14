"""Render text messages in the style of the real VideoVeoBot."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GenSettings:
    model: str = "kling"
    fmt: str = "vertical"
    mode: str = "standard"
    duration: int = 5
    sound: bool = False
    prompt: str = ""
    image_attached: bool = False


MODEL_NAMES = {
    "kling": "Kling 3.0",
    "veo": "VEO 3",
    "seedance": "Seedance 2.0",
    "lipsync": "Lipsync",
}

MODEL_DESCRIPTIONS = {
    "kling": "[модель от Kling AI: нативный звук, мультикадровое повествование, до 15 секунд видео]",
    "veo": "[модель от Google DeepMind VEO 3: нативный звук, реалистичная физика, до 8 секунд видео]",
    "seedance": "[модель от ByteDance: реалистичное видео с людьми, нативный звук, разрешение до 1080p]",
    "lipsync": "[оживление фото: фото лица + аудио речи → говорящее видео с синхронизацией губ]",
}


def main_menu_text() -> str:
    """Текст главного меню — повторяет стиль реального бота."""
    return (
        "⭐ <b>Главное меню:</b>\n\n"
        f"🔥 <b>Kling 3.0</b> → /kling\n"
        f"<i>{MODEL_DESCRIPTIONS['kling']}</i>\n\n"
        f"📖 Рекомендации Kling <i>[минута чтения]</i>\n\n"
        f"🌀 <b>Seedance 2.0</b> → /seedance\n"
        f"<i>{MODEL_DESCRIPTIONS['seedance']}</i>\n\n"
        f"👄 <b>Lipsync</b> → /lipsync\n"
        f"<i>{MODEL_DESCRIPTIONS['lipsync']}</i>\n\n"
        "💡 Можно пользоваться через Mini App или прямо здесь — "
        "просто отправьте текст."
    )


def model_card_text(model: str) -> str:
    name = MODEL_NAMES.get(model, model.title())
    desc = MODEL_DESCRIPTIONS.get(model, "")
    return f"<b>{name}</b>\n<i>{desc}</i>"


def format_text() -> str:
    return "📐 <b>Формат видео</b>\n\nВыберите соотношение сторон:"


def mode_text(fmt: str) -> str:
    note = ""
    if fmt == "horizontal":
        note = "\n\n<i>В горизонтальном формате 4K недоступен.</i>"
    return f"⚙️ <b>Режим</b>{note}\n\nВыберите режим генерации:"


def duration_text() -> str:
    return "⏱ <b>Длительность</b>\n\nВыберите длительность ролика:"


def sound_text(current: bool) -> str:
    label = "включён" if current else "выключен"
    return (
        "🔊 <b>Звук</b>\n\n"
        f"Сгенерировать звук — <i>{label}</i>\n\n"
        "<i>В режиме 4K звук недоступен.</i>"
    )


def image_text() -> str:
    return (
        "🖼 <b>Изображение</b>\n\n"
        "<b>Изображение</b> (необязательно)\n"
        "<i>Только одно изображение. JPG/PNG</i>\n\n"
        "Отправьте картинку или нажмите «Пропустить»."
    )


def prompt_text(attached: bool) -> str:
    base = "✍️ <b>Промпт</b>\n\nОпишите, как фото должно ожить в видео: движение камеры, окружение, стиль, длительность..."
    if attached:
        base += "\n\n<i>📎 Изображение прикреплено.</i>"
    return base


def confirm_text(s: GenSettings) -> str:
    cost = compute_cost(s)
    model_label = MODEL_NAMES.get(s.model, s.model.title())
    fmt_label = "вертикальный" if s.fmt == "vertical" else "горизонтальный"
    mode_label = {"standard": "Standard", "pro": "Pro", "4k": "4K"}[s.mode]
    sound_label = "🔊 вкл" if s.sound else "🔇 выкл"
    return (
        f"🟣 <b>СТОИМОСТЬ ГЕНЕРАЦИИ</b>\n\n"
        f"<b>Модель:</b> {model_label}\n"
        f"<b>Формат:</b> {fmt_label}\n"
        f"<b>Режим:</b> {mode_label}\n"
        f"<b>Длительность:</b> {s.duration} сек\n"
        f"<b>Звук:</b> {sound_label}\n"
        f"<b>Изображение:</b> {'да' if s.image_attached else 'нет'}\n\n"
        f"<b>Промпт:</b>\n<i>{(s.prompt or '—').strip()[:300]}</i>\n\n"
        f"💎 <b>Цена:</b> <code>{cost} генераций</code>"
    )


def done_text(s: GenSettings, generation_id: int) -> str:
    cost = compute_cost(s)
    return (
        f"✅ <b>Готово!</b>\n\n"
        f"Генерация №<code>{generation_id}</code> завершена.\n"
        f"Списано: <b>{cost}</b> генераций.\n\n"
        "Это демо-режим: реальная модель не вызывалась. "
        "В рабочей версии здесь будет ссылка на готовое видео."
    )


def compute_cost(s: GenSettings) -> int:
    """Цена в «генерациях» — копия логики скриншотов: 1/2/4 за Standard/Pro/4K."""
    base = {"standard": 1, "pro": 2, "4k": 4}.get(s.mode, 1)
    # 10 сек дороже 5 сек
    if s.duration >= 10:
        base += 1
    return base


def example_card_text(index: int, title: str, prompt: str) -> str:
    return f"<b>{title}</b>\n\n<code>{prompt}</code>"


def balance_text(balance: int) -> str:
    """Карточка баланса пользователя."""
    bar_filled = min(10, max(0, balance))
    bar = "▓" * bar_filled + "░" * (10 - bar_filled)
    return (
        f"💰 <b>Ваш баланс</b>\n\n"
        f"<code>{bar}</code>\n\n"
        f"Доступно: <b>{balance}</b> генераций\n\n"
        "<i>В демо-режиме баланс можно пополнить кнопками ниже.</i>"
    )


def topup_text(new_balance: int, added: int) -> str:
    return (
        f"✅ <b>Баланс пополнен</b>\n\n"
        f"Зачислено: +<b>{added}</b> генераций\n"
        f"Текущий баланс: <b>{new_balance}</b>"
    )


def history_text(rows) -> str:
    """rows — Sequence[Generation]."""
    if not rows:
        return (
            "📜 <b>История генераций</b>\n\n"
            "<i>Пока пусто. Сгенерируйте первое видео через "
            "главное меню — оно появится здесь.</i>"
        )
    lines = ["📜 <b>История генераций</b>\n"]
    for i, r in enumerate(rows, start=1):
        model = MODEL_NAMES.get(r.model, r.model)
        ts = r.created_at.strftime("%d.%m %H:%M") if r.created_at else "—"
        prompt_short = (r.prompt or "(без промпта)")[:60]
        if len(r.prompt or "") > 60:
            prompt_short += "…"
        lines.append(
            f"{i}. <b>{model}</b> · <code>{r.cost}</code> · {ts}\n"
            f"   <i>{prompt_short}</i>"
        )
    return "\n\n".join(lines)


def lipsync_intro_text() -> str:
    return (
        "👄 <b>Lipsync</b>\n\n"
        "<i>Оживление фото: фото лица + аудио речи → "
        "говорящее видео с синхронизацией губ.</i>\n\n"
        "Отправьте <b>фото лица</b> (JPG/PNG):"
    )


def lipsync_awaiting_audio_text() -> str:
    return (
        "👄 <b>Шаг 2 из 2 — аудио</b>\n\n"
        "Отправьте <b>голосовое сообщение</b> или <b>аудиофайл</b> — "
        "произнесите фразу, которую должен сказать человек на фото."
    )


def lipsync_done_text(generation_id: int, cost: int) -> str:
    return (
        f"✅ <b>Lipsync готов!</b>\n\n"
        f"Генерация №<code>{generation_id}</code> завершена.\n"
        f"Списано: <b>{cost}</b> генераций.\n\n"
        "<i>Это демо: реальная синхронизация губ не выполнялась. "
        "В рабочей версии здесь будет видео-результат.</i>"
    )


def insufficient_funds_text(needed: int, available: int) -> str:
    return (
        f"🚨 <b>Недостаточно генераций</b>\n\n"
        f"Нужно: <b>{needed}</b>\n"
        f"Доступно: <b>{available}</b>\n\n"
        "Пополните баланс через 💰 Баланс в главном меню."
    )