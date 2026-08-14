"""ORM models for users, generations and examples."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, Text, Integer, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column

from bot.database import Base


class User(Base):
    """Telegram user who has interacted with the bot."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    balance: Mapped[int] = mapped_column(Integer, default=10)  # демо-стартовый баланс


class Generation(Base):
    """A single video generation request (demo)."""

    __tablename__ = "generations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    model: Mapped[str] = mapped_column(String(32))  # kling | veo | seedance | lipsync
    fmt: Mapped[str] = mapped_column(String(16), default="vertical")  # vertical|horizontal
    mode: Mapped[str] = mapped_column(String(16), default="standard")  # standard|pro|4k
    duration: Mapped[int] = mapped_column(Integer, default=5)  # 5|10 seconds
    sound: Mapped[bool] = mapped_column(Boolean, default=False)
    prompt: Mapped[str] = mapped_column(Text, default="")
    image_file_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    # pending -> processing -> done | failed
    cost: Mapped[int] = mapped_column(Integer, default=1)
    video_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())