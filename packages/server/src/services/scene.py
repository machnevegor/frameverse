"""Scene service."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import EMB_IMG_DIMENSIONS, EMB_TXT_DIMENSIONS
from src.db.models import SceneModel
from src.domain import NonTerminalSceneStatus


@dataclass(slots=True)
class ChannelSearchHit:
    scene_id: UUID
    distance: float


class SceneService:
    """Business operations over scene entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        movie_id: UUID,
        position: int,
        start: float,
        end: float,
        duration: float,
        status: str,
        transcript: dict,
        video_s3_key: str | None,
    ) -> SceneModel:
        scene = SceneModel(
            movie_id=movie_id,
            position=position,
            start=start,
            end=end,
            duration=duration,
            status=status,
            transcript=transcript,
            video_s3_key=video_s3_key,
        )
        self.session.add(scene)
        await self.session.flush()
        return scene

    async def get(self, scene_id: UUID) -> SceneModel | None:
        return await self.session.get(SceneModel, scene_id)

    async def list_by_movie(self, movie_id: UUID) -> list[SceneModel]:
        stmt = select(SceneModel).where(SceneModel.movie_id == movie_id).order_by(SceneModel.position.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars())

    async def set_status(self, scene: SceneModel, status: str) -> SceneModel:
        scene.status = status
        await self.session.flush()
        return scene

    async def cancel_non_terminal_for_movie(self, movie_id: UUID) -> None:
        stmt = (
            update(SceneModel)
            .where(SceneModel.movie_id == movie_id)
            .where(SceneModel.status.in_([status.value for status in NonTerminalSceneStatus]))
            .values(status="cancelled")
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def delete_by_movie(self, movie_id: UUID) -> None:
        stmt = delete(SceneModel).where(SceneModel.movie_id == movie_id)
        await self.session.execute(stmt)
        await self.session.flush()

    async def search_by_transcript(
        self,
        query_vector: list[float],
        *,
        movie_id: UUID | None = None,
        limit: int = 10,
    ) -> list[ChannelSearchHit]:
        movie_filter = "AND movie_id = :movie_id" if movie_id is not None else ""
        raw = text(
            f"""
            SELECT id, transcript_embedding <=> CAST(:vec AS vector({EMB_TXT_DIMENSIONS})) AS dist
            FROM scenes
            WHERE transcript_embedding IS NOT NULL
            {movie_filter}
            ORDER BY dist
            LIMIT :limit
            """,
        )
        params: dict = {"vec": self._vector_literal(query_vector), "limit": limit}
        if movie_id is not None:
            params["movie_id"] = str(movie_id)
        rows = (await self.session.execute(raw, params)).fetchall()
        return [ChannelSearchHit(scene_id=UUID(str(row[0])), distance=float(row[1])) for row in rows]

    async def search_by_annotation(
        self,
        query_vector: list[float],
        *,
        movie_id: UUID | None = None,
        limit: int = 10,
    ) -> list[ChannelSearchHit]:
        movie_filter = "AND movie_id = :movie_id" if movie_id is not None else ""
        raw = text(
            f"""
            SELECT id, annotation_embedding <=> CAST(:vec AS vector({EMB_TXT_DIMENSIONS})) AS dist
            FROM scenes
            WHERE annotation_embedding IS NOT NULL
            {movie_filter}
            ORDER BY dist
            LIMIT :limit
            """,
        )
        params: dict = {"vec": self._vector_literal(query_vector), "limit": limit}
        if movie_id is not None:
            params["movie_id"] = str(movie_id)
        rows = (await self.session.execute(raw, params)).fetchall()
        return [ChannelSearchHit(scene_id=UUID(str(row[0])), distance=float(row[1])) for row in rows]

    async def search_by_image(
        self,
        query_vector: list[float],
        *,
        movie_id: UUID | None = None,
        limit: int = 10,
    ) -> list[ChannelSearchHit]:
        # join to scenes only needed for the movie_id filter; MIN aggregates per scene
        movie_filter = "AND f.movie_id = :movie_id" if movie_id is not None else ""
        raw = text(
            f"""
            SELECT f.scene_id, MIN(f.image_embedding <=> CAST(:vec AS halfvec({EMB_IMG_DIMENSIONS}))) AS dist
            FROM frames f
            WHERE f.image_embedding IS NOT NULL
            {movie_filter}
            GROUP BY f.scene_id
            ORDER BY dist
            LIMIT :limit
            """,
        )
        params: dict = {"vec": self._vector_literal(query_vector), "limit": limit}
        if movie_id is not None:
            params["movie_id"] = str(movie_id)
        rows = (await self.session.execute(raw, params)).fetchall()
        return [ChannelSearchHit(scene_id=UUID(str(row[0])), distance=float(row[1])) for row in rows]

    @staticmethod
    def _vector_literal(values: list[float]) -> str:
        return f"[{','.join(str(value) for value in values)}]"
