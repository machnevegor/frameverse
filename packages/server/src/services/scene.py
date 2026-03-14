"""Scene service."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import (
    EMB_IMG_DIMENSIONS,
    EMB_TXT_DIMENSIONS,
    SEARCH_SCENES_ANNOTATION_WEIGHT,
    SEARCH_SCENES_IMAGE_WEIGHT,
    SEARCH_SCENES_TRANSCRIPT_WEIGHT,
)
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
    ) -> list[tuple[SceneModel, float, float | None, float | None, float | None]]:
        if (
            SEARCH_SCENES_ANNOTATION_WEIGHT <= 0
            and SEARCH_SCENES_TRANSCRIPT_WEIGHT <= 0
            and SEARCH_SCENES_IMAGE_WEIGHT <= 0
        ):
            raise ValueError("At least one SEARCH_SCENES_* weight must be greater than zero")

        vec_str = f"[{','.join(str(v) for v in query_vector)}]"
        movie_filter = "AND s.movie_id = :movie_id" if movie_id is not None else ""

        raw = text(
            f"""
            WITH frame_scores AS (
                SELECT scene_id, MIN(image_embedding <=> CAST(:img_vec AS halfvec({EMB_IMG_DIMENSIONS}))) AS best_img_dist
                FROM frames
                WHERE image_embedding IS NOT NULL
                GROUP BY scene_id
            ),
            scored AS (
                SELECT
                    s.id,
                    s.annotation_embedding <=> CAST(:txt_vec AS vector({EMB_TXT_DIMENSIONS})) AS annotation_distance,
                    s.transcript_embedding <=> CAST(:txt_vec AS vector({EMB_TXT_DIMENSIONS})) AS transcript_distance,
                    fs.best_img_dist AS image_distance
                FROM scenes s
                LEFT JOIN frame_scores fs ON fs.scene_id = s.id
                WHERE true
                {movie_filter}
            ),
            weighted AS (
                SELECT
                    id,
                    annotation_distance,
                    transcript_distance,
                    image_distance,
                    (
                        COALESCE(annotation_distance * CAST(:annotation_weight AS double precision), 0) +
                        COALESCE(transcript_distance * CAST(:transcript_weight AS double precision), 0) +
                        COALESCE(image_distance * CAST(:image_weight AS double precision), 0)
                    ) AS weighted_distance_sum,
                    (
                        ((annotation_distance IS NOT NULL)::int * CAST(:annotation_weight AS double precision)) +
                        ((transcript_distance IS NOT NULL)::int * CAST(:transcript_weight AS double precision)) +
                        ((image_distance IS NOT NULL)::int * CAST(:image_weight AS double precision))
                    ) AS total_weight
                FROM scored
                WHERE (
                    annotation_distance IS NOT NULL
                    OR transcript_distance IS NOT NULL
                    OR image_distance IS NOT NULL
                )
            )
            SELECT
                id,
                annotation_distance,
                transcript_distance,
                image_distance,
                weighted_distance_sum / total_weight AS distance
            FROM weighted
            WHERE total_weight > 0
            ORDER BY distance
            LIMIT :limit
            """,
        )
        params: dict[str, str | int | float] = {
            "txt_vec": vec_str,
            "img_vec": vec_str,
            "limit": limit,
            "annotation_weight": SEARCH_SCENES_ANNOTATION_WEIGHT,
            "transcript_weight": SEARCH_SCENES_TRANSCRIPT_WEIGHT,
            "image_weight": SEARCH_SCENES_IMAGE_WEIGHT,
        }
        if movie_id is not None:
            params["movie_id"] = str(movie_id)

        rows_result = await self.session.execute(raw, params)
        rows = rows_result.fetchall()
        if not rows:
            return []

        scene_metrics = {
            str(row[0]): {
                "annotation_distance": float(row[1]) if row[1] is not None else None,
                "transcript_distance": float(row[2]) if row[2] is not None else None,
                "image_distance": float(row[3]) if row[3] is not None else None,
                "distance": float(row[4]),
            }
            for row in rows
        }
        ordered_ids = [row[0] for row in rows]
        scenes_result = await self.session.execute(select(SceneModel).where(SceneModel.id.in_(ordered_ids)))
        scenes_by_id = {str(scene.id): scene for scene in scenes_result.scalars()}
        return [
            (
                scenes_by_id[str(scene_id)],
                scene_metrics[str(scene_id)]["distance"],
                scene_metrics[str(scene_id)]["transcript_distance"],
                scene_metrics[str(scene_id)]["annotation_distance"],
                scene_metrics[str(scene_id)]["image_distance"],
            )
            for scene_id in ordered_ids
        ]
