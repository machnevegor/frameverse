"""Movie service."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import MovieModel


class MovieService:
    """Business operations over movie entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        title: str,
        video_s3_key: str,
        year: int | None = None,
        slogan: str | None = None,
        genres: list[str] | None = None,
        description: str | None = None,
        short_description: str | None = None,
        poster_s3_key: str | None = None,
    ) -> MovieModel:
        movie = MovieModel(
            title=title,
            year=year,
            slogan=slogan,
            genres=genres,
            description=description,
            short_description=short_description,
            video_s3_key=video_s3_key,
            poster_s3_key=poster_s3_key,
        )
        self.session.add(movie)
        await self.session.flush()
        return movie

    async def get(self, movie_id: UUID) -> MovieModel | None:
        return await self.session.get(MovieModel, movie_id)

    async def get_by_title(self, title: str) -> MovieModel | None:
        stmt = select(MovieModel).where(MovieModel.title == title).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self, *, limit: int = 50, offset: int = 0) -> tuple[list[MovieModel], int]:
        stmt = select(MovieModel).order_by(desc(MovieModel.created_at)).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        items = list(result.scalars())
        total_stmt = select(func.count(MovieModel.id))
        total_result = await self.session.execute(total_stmt)
        total = int(total_result.scalar_one() or 0)
        return items, total

    async def delete(self, movie: MovieModel) -> None:
        await self.session.delete(movie)
        await self.session.flush()
