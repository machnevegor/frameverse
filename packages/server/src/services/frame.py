"""Frame service."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import FrameModel


class FrameService:
    """Business operations over frame entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        movie_id: UUID,
        scene_id: UUID,
        position: int,
        timestamp: float,
        score: float,
        image_s3_key: str,
    ) -> FrameModel:
        frame = FrameModel(
            movie_id=movie_id,
            scene_id=scene_id,
            position=position,
            timestamp=timestamp,
            score=score,
            image_s3_key=image_s3_key,
        )
        self.session.add(frame)
        await self.session.flush()
        return frame

    async def get(self, frame_id: UUID) -> FrameModel | None:
        return await self.session.get(FrameModel, frame_id)

    async def list_by_scene(self, scene_id: UUID) -> list[FrameModel]:
        stmt = select(FrameModel).where(FrameModel.scene_id == scene_id).order_by(FrameModel.position.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars())

    async def delete_by_scene(self, scene_id: UUID) -> None:
        stmt = delete(FrameModel).where(FrameModel.scene_id == scene_id)
        await self.session.execute(stmt)
        await self.session.flush()
