"""Task service."""

from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import Integer, cast, desc, func, select, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import literal_column

from src.db.models import TaskModel
from src.domain import NonTerminalMovieStatus, Progress

_PROGRESS_FIELDS = {
    "scenes_detected",
    "scenes_extracted",
    "scenes_annotated",
    "scenes_embedded",
}


class TaskService:
    """Business operations over task entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        task_id: UUID | None = None,
        movie_id: UUID,
        movie_title: str,
        status: str,
        temporal_workflow_id: str,
        langfuse_trace_id: str,
    ) -> TaskModel:
        task = TaskModel(
            id=task_id,
            movie_id=movie_id,
            movie_title=movie_title,
            status=status,
            temporal_workflow_id=temporal_workflow_id,
            langfuse_trace_id=langfuse_trace_id,
        )
        self.session.add(task)
        await self.session.flush()
        return task

    async def get(self, task_id: UUID) -> TaskModel | None:
        return await self.session.get(TaskModel, task_id)

    async def list(self, *, limit: int = 50, offset: int = 0) -> tuple[list[TaskModel], int]:
        stmt = select(TaskModel).order_by(desc(TaskModel.created_at)).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        items = list(result.scalars())
        total_stmt = select(func.count(TaskModel.id))
        total_result = await self.session.execute(total_stmt)
        total = int(total_result.scalar_one() or 0)
        return items, total

    async def get_active_by_movie_title(self, title: str) -> TaskModel | None:
        stmt = (
            select(TaskModel)
            .where(TaskModel.movie_title == title)
            .where(TaskModel.status.in_([status.value for status in NonTerminalMovieStatus]))
            .order_by(desc(TaskModel.created_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_by_movie_id(self, movie_id: UUID) -> TaskModel | None:
        stmt = select(TaskModel).where(TaskModel.movie_id == movie_id).order_by(desc(TaskModel.created_at)).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active_by_movie_id(self, movie_id: UUID) -> list[TaskModel]:
        stmt = (
            select(TaskModel)
            .where(TaskModel.movie_id == movie_id)
            .where(TaskModel.status.in_([status.value for status in NonTerminalMovieStatus]))
            .order_by(desc(TaskModel.created_at))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars())

    async def update_status(
        self,
        task: TaskModel,
        status: str,
        *,
        error_message: str | None = None,
        error_code: str | None = None,
    ) -> TaskModel:
        task.status = status
        task.error_message = error_message
        task.error_code = error_code
        await self.session.flush()
        return task

    async def set_progress(self, task_id: UUID, progress: Progress) -> None:
        task = await self.get(task_id)
        if task is None:
            return
        task.progress = progress.model_dump(mode="json")
        await self.session.flush()

    async def increment_progress(self, task_id: UUID, field: str) -> None:
        if field not in _PROGRESS_FIELDS:
            raise ValueError(f"Unsupported progress field: {field}")
        default = func.cast(json.dumps({f: 0 for f in _PROGRESS_FIELDS}), JSONB)
        # field is validated against _PROGRESS_FIELDS whitelist above, safe to inline
        path = literal_column(f"'{{{field}}}'")
        current = cast(TaskModel.progress[field].astext, Integer)
        stmt = (
            update(TaskModel)
            .where(TaskModel.id == task_id)
            .values(
                progress=func.jsonb_set(
                    func.coalesce(TaskModel.progress, default),
                    path,
                    func.to_jsonb(func.coalesce(current, 0) + 1),
                    True,
                )
            )
        )
        await self.session.execute(stmt)
