"""FSM states for generation wizard."""

from aiogram.fsm.state import State, StatesGroup


class GenerationStates(StatesGroup):
    """State machine for the generation wizard."""

    choosing_format = State()      # vertical / horizontal
    choosing_mode = State()        # standard / pro / 4k
    choosing_duration = State()    # 5 / 10
    choosing_sound = State()       # on / off
    waiting_image = State()        # optional photo upload
    waiting_prompt = State()       # text prompt
    confirming = State()           # confirm + cost


class LipsyncStates(StatesGroup):
    """Шаги Lipsync wizard: фото лица → аудио."""

    waiting_photo = State()
    waiting_audio = State()