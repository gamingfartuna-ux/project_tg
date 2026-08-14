"""Async SQLAlchemy database setup."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for ORM models."""


engine: AsyncEngine | None = None
session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_database(url: str) -> None:
    """Create engine, session factory and tables."""
    global engine, session_factory
    engine = create_async_engine(url, echo=False, future=True)
    session_factory = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    # Import models so they are registered with Base.metadata
    from bot import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_database() -> None:
    """Dispose engine."""
    global engine, session_factory
    if engine is not None:
        await engine.dispose()
    engine = None
    session_factory = None