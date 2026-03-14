"""Scene service."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import SceneModel
from src.domain import NonTerminalSceneStatus


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

    async def search(
        self,
        query_vector: list[float],
        *,
        movie_id: UUID | None = None,
        limit: int = 10,
    ) -> list[tuple[SceneModel, float]]:
        vec_str = f"[{','.join(str(v) for v in query_vector)}]"
        movie_filter = "AND s.movie_id = :movie_id" if movie_id is not None else ""

        raw = text(
            f"""
            WITH frame_scores AS (
                SELECT scene_id, MIN(image_embedding <=> CAST(:vec AS vector)) AS best_img_dist
                FROM frames
                WHERE image_embedding IS NOT NULL
                GROUP BY scene_id
            )
            SELECT s.id, (
                COALESCE(s.annotation_embedding <=> CAST(:vec AS vector), 0) +
                COALESCE(s.transcript_embedding <=> CAST(:vec AS vector), 0) +
                COALESCE(fs.best_img_dist, 0)
            ) / NULLIF(
                (s.annotation_embedding IS NOT NULL)::int +
                (s.transcript_embedding IS NOT NULL)::int +
                (fs.best_img_dist IS NOT NULL)::int,
                0
            ) AS distance
            FROM scenes s
            LEFT JOIN frame_scores fs ON fs.scene_id = s.id
            WHERE (
                s.annotation_embedding IS NOT NULL
                OR s.transcript_embedding IS NOT NULL
                OR fs.best_img_dist IS NOT NULL
            )
            {movie_filter}
            ORDER BY distance
            LIMIT :limit
            """,
        )
        params: dict[str, str | int] = {"vec": vec_str, "limit": limit}
        if movie_id is not None:
            params["movie_id"] = str(movie_id)

        rows_result = await self.session.execute(raw, params)
        rows = rows_result.fetchall()
        if not rows:
            return []

        scene_distances = {str(row[0]): float(row[1]) for row in rows}
        ordered_ids = [row[0] for row in rows]
        scenes_result = await self.session.execute(select(SceneModel).where(SceneModel.id.in_(ordered_ids)))
        scenes_by_id = {str(scene.id): scene for scene in scenes_result.scalars()}
        return [(scenes_by_id[str(scene_id)], scene_distances[str(scene_id)]) for scene_id in ordered_ids]
