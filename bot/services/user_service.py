"""Service layer for users, balance and generation history."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models import User, Generation


STARTING_BALANCE = 10  # демо-стартовый баланс при первом /start


@dataclass
class UserService:
    """High-level DB operations."""

    session_factory: object

    # -------- Users --------

    async def upsert_user(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
    ) -> User:
        assert self.session_factory is not None
        async with self.session_factory() as session:  # type: ignore[call-arg]
            existing = await session.scalar(
                select(User).where(User.telegram_id == telegram_id)
            )
            if existing is None:
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    balance=STARTING_BALANCE,
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
                return user
            existing.username = username
            existing.first_name = first_name
            await session.commit()
            await session.refresh(existing)
            return existing

    async def get_user(self, telegram_id: int) -> User | None:
        assert self.session_factory is not None
        async with self.session_factory() as session:  # type: ignore[call-arg]
            return await session.scalar(
                select(User).where(User.telegram_id == telegram_id)
            )

    async def refund(self, telegram_id: int, amount: int) -> int | None:
        """Возвращает amount на баланс (для отката при сбое генерации).

        Возвращает новый баланс или None если пользователь не найден.
        """
        assert self.session_factory is not None
        async with self.session_factory() as session:  # type: ignore[call-arg]
            user = await session.scalar(
                select(User).where(User.telegram_id == telegram_id).with_for_update()
            )
            if user is None:
                return None
            user.balance = max(0, user.balance + amount)
            await session.commit()
            await session.refresh(user)
            return user.balance

    async def add_balance(self, telegram_id: int, amount: int) -> int:
        """Пополняет баланс пользователя на amount. Возвращает новый баланс."""
        assert self.session_factory is not None
        async with self.session_factory() as session:  # type: ignore[call-arg]
            user = await session.scalar(
                select(User).where(User.telegram_id == telegram_id)
            )
            if user is None:
                raise ValueError(f"user {telegram_id} not found")
            user.balance = max(0, user.balance + amount)
            await session.commit()
            return user.balance

    async def spend(self, telegram_id: int, amount: int) -> bool:
        """Списывает amount. Возвращает True если хватило, иначе False."""
        assert self.session_factory is not None
        async with self.session_factory() as session:  # type: ignore[call-arg]
            user = await session.scalar(
                select(User).where(User.telegram_id == telegram_id).with_for_update()
            )
            if user is None or user.balance < amount:
                return False
            user.balance -= amount
            await session.commit()
            return True

    # -------- Generations --------

    async def record_generation(
        self,
        user_id: int,
        model: str,
        fmt: str,
        mode: str,
        duration: int,
        sound: bool,
        prompt: str,
        image_file_id: str | None,
        cost: int = 1,
        video_url: str | None = None,
    ) -> int:
        assert self.session_factory is not None
        async with self.session_factory() as session:  # type: ignore[call-arg]
            row = Generation(
                user_id=user_id,
                model=model,
                fmt=fmt,
                mode=mode,
                duration=duration,
                sound=sound,
                prompt=prompt,
                image_file_id=image_file_id,
                cost=cost,
                video_url=video_url,
                status="done",  # demo: instantly "done"
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row.id

    async def last_generations(
        self, user_id: int, limit: int = 10
    ) -> Sequence[Generation]:
        assert self.session_factory is not None
        async with self.session_factory() as session:  # type: ignore[call-arg]
            stmt = (
                select(Generation)
                .where(Generation.user_id == user_id)
                .order_by(Generation.created_at.desc())
                .limit(limit)
            )
            rows = await session.scalars(stmt)
            return rows.all()

    async def get_generation(self, gen_id: int) -> Generation | None:
        assert self.session_factory is not None
        async with self.session_factory() as session:  # type: ignore[call-arg]
            return await session.scalar(
                select(Generation).where(Generation.id == gen_id)
            )