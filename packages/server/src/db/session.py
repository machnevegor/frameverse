"""Database engine and session factories."""

from collections.abc import AsyncGenerator

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import settings
from src.db import models  # noqa: F401

engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    # Ensure all table metadata has been imported before create_all.
    async with engine.begin() as conn:
        await conn.run_sync(UUIDAuditBase.metadata.create_all)
