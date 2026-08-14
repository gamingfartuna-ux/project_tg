"""Catalog of example clips used by /examples and the TWA carousel.

The clip URLs point to public sample MP4s widely used on the web for
HTML5 video demos (Google sample videos, W3Schools samples). They are
short, royalty-free and serve as placeholders for AI-generated footage
in this demo bot.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Example:
    title: str
    prompt: str
    video_url: str
    duration_label: str = "0:08"


# Public sample MP4s — short, royalty-free placeholders.
EXAMPLES: tuple[Example, ...] = (
    Example(
        title="Ведущий и бабушка",
        prompt=(
            "Ведущий с микрофоном спрашивает у бабушки на улицах на русском языке. "
            "(оператор) - \"вы понимаете, что вы нейросеть?\" (бабушка) - \"да, "
            "внучок, ты ведь тоже нейронка, ахаха\" (смеётся). Бабушка прыгает вверх."
        ),
        video_url="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
    ),
    Example(
        title="Эпическое уклонение",
        prompt=(
            "Мужчина в чёрном плаще эпически уклоняется от пули, словно в замедленной "
            "съёмке. Видео начинается с близкого плана на лицо мужчины, он в чёрных "
            "узких очках. Далее — замедленная съёмка: мужчина наклоняется назад, его "
            "тело изгибается в воздухе. Вокруг летят частицы пыли, искры и обломки. "
            "Сцена кинематографична, в тёмных тонах, глубоких зелёных и чёрных."
        ),
        video_url="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
    ),
    Example(
        title="Утренний кофе",
        prompt=(
            "Девушка в уютной кухне наливает кофе в чашку. Мягкий утренний свет, "
            "крупный план, замедленная съёмка пара. Стиль — lifestyle, тёплые тона, "
            "уютная атмосфера."
        ),
        video_url="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4",
    ),
    Example(
        title="Город ночью",
        prompt=(
            "Ночной мегаполис, неоновые вывески, отражения в мокром асфальте. "
            "Камера медленно скользит между зданий. Киберпанк-стиль, фиолетовые и "
            "голубые тона, лёгкий дождь."
        ),
        video_url="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4",
    ),
    Example(
        title="Собака на прогулке",
        prompt=(
            "Золотистый ретривер бежит по осеннему парку, листья под ногами, "
            "счастливая морда крупным планом. Тёплый дневной свет, лёгкая "
            "замедленная съёмка."
        ),
        video_url="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerMeltdowns.mp4",
    ),
)


def get_example(index: int) -> Example | None:
    if 0 <= index < len(EXAMPLES):
        return EXAMPLES[index]
    return None


def example_count() -> int:
    return len(EXAMPLES)