"""Database engine and session factories."""

from collections.abc import AsyncGenerator

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import text
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
        # Keep existing deployments aligned with model nullability for scene video key.
        await conn.execute(text("ALTER TABLE scenes ALTER COLUMN video_s3_key DROP NOT NULL"))
        # Migrate frames.image_embedding from vector(1024) to halfvec(2048) if needed.
        await conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF (
                        SELECT udt_name
                        FROM information_schema.columns
                        WHERE table_name = 'frames' AND column_name = 'image_embedding'
                    ) != 'halfvec' THEN
                        ALTER TABLE frames
                        ALTER COLUMN image_embedding TYPE halfvec(2048)
                        USING CASE WHEN image_embedding IS NULL THEN NULL
                                   ELSE image_embedding::halfvec(2048) END;
                    END IF;
                END $$;
                """
            )
        )
