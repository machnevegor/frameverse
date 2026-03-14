"""Task endpoints."""

from __future__ import annotations

import math
from uuid import UUID, uuid4

from litestar import get, post
from litestar.exceptions import ClientException, NotFoundException
from sqlalchemy.ext.asyncio import AsyncSession
from temporalio.client import Client

from src.api.controllers._mappers import to_task
from src.api.errors import CANCEL_TASK_ERROR, CREATE_TASK_ERROR, READ_TASK_ERROR
from src.api.schemas.tasks import CancelTaskResult, CreateTaskInput, CreateTaskResult, ListTasksResult, ReadTaskResult
from src.config import settings
from src.domain import NonTerminalMovieStatus, PaginationInfo
from src.services.factory import get_storage
from src.services.movie import MovieService
from src.services.scene import SceneService
from src.services.task import TaskService
from src.workers.workflows import ProcessMovieWorkflow


@get(
    f"{settings.base_path}/tasks",
    tags=["Task"],
    summary="List tasks",
    description="List all movie processing tasks with pagination.",
)
async def list_tasks(session: AsyncSession, page: int = 1, per_page: int = 20) -> ListTasksResult:
    task_service = TaskService(session)
    offset = max(0, page - 1) * per_page
    tasks, total = await task_service.list(limit=per_page, offset=offset)
    total_pages = max(1, math.ceil(total / per_page)) if per_page > 0 else 1
    pagination = PaginationInfo(
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total_items=total,
        has_next=page < total_pages,
        cursor=str(tasks[-1].id) if tasks else None,
    )
    return ListTasksResult(data=[to_task(task) for task in tasks], pagination=pagination)


@post(
    f"{settings.base_path}/tasks",
    tags=["Task"],
    summary="Create task",
    description="Create a new movie processing task.",
)
async def create_task(
    session: AsyncSession,
    temporal_client: Client,
    data: CreateTaskInput,
) -> CreateTaskResult:
    storage = get_storage()
    task_service = TaskService(session)
    movie_service = MovieService(session)
    scene_service = SceneService(session)

    if not await storage.exists(data.s3_key):
        raise NotFoundException(CREATE_TASK_ERROR[404])

    active_task = await task_service.get_active_by_movie_title(data.title)
    if active_task is not None:
        active_task.status = "cancelled"
        await scene_service.cancel_non_terminal_for_movie(active_task.movie_id)
        try:
            handle = temporal_client.get_workflow_handle(active_task.temporal_workflow_id)
            await handle.signal(ProcessMovieWorkflow.cancel_processing)
        except Exception:  # noqa: BLE001
            pass

    movie = await movie_service.get_by_title(data.title)
    if movie is None:
        movie = await movie_service.create(
            title=data.title,
            year=data.year,
            slogan=data.slogan,
            genres=data.genres,
            description=data.description,
            short_description=data.short_description,
            poster_s3_key=data.poster_s3_key,
            video_s3_key=data.s3_key,
        )
    else:
        movie.year = data.year
        movie.slogan = data.slogan
        movie.genres = data.genres
        movie.description = data.description
        movie.short_description = data.short_description
        movie.poster_s3_key = data.poster_s3_key
        movie.video_s3_key = data.s3_key
        movie.audio_s3_key = None
        movie.duration = None
        movie.transcript = None
        await scene_service.delete_by_movie(movie.id)
        await storage.delete_prefix(f"movies/{movie.id}/scenes/")

    task_id = uuid4()
    task = await task_service.create(
        task_id=task_id,
        movie_id=movie.id,
        movie_title=movie.title,
        status="queued",
        temporal_workflow_id=str(task_id),
        langfuse_trace_id=str(task_id),
    )
    await session.commit()
    await temporal_client.start_workflow(
        ProcessMovieWorkflow.run,
        str(task.id),
        id=str(task.id),
        task_queue=settings.temporal_task_queue,
    )
    await session.refresh(task)
    return CreateTaskResult(data=to_task(task))


@get(
    f"{settings.base_path}/tasks/{{task_id:uuid}}",
    tags=["Task"],
    summary="Get task",
    description="Get task resource by identifier.",
)
async def read_task(session: AsyncSession, task_id: UUID) -> ReadTaskResult:
    task_service = TaskService(session)
    task = await task_service.get(task_id)
    if task is None:
        raise NotFoundException(READ_TASK_ERROR[404])
    return ReadTaskResult(data=to_task(task))


@post(
    f"{settings.base_path}/tasks/{{task_id:uuid}}/cancel",
    tags=["Task"],
    summary="Cancel task",
    description="Cancel a non-terminal movie processing task.",
)
async def cancel_task(session: AsyncSession, temporal_client: Client, task_id: UUID) -> CancelTaskResult:
    task_service = TaskService(session)
    scene_service = SceneService(session)
    task = await task_service.get(task_id)
    if task is None:
        raise NotFoundException(CANCEL_TASK_ERROR[404])
    if task.status not in {status.value for status in NonTerminalMovieStatus}:
        raise ClientException(status_code=409, detail=CANCEL_TASK_ERROR[409])

    task.status = "cancelled"
    await scene_service.cancel_non_terminal_for_movie(task.movie_id)
    await session.commit()

    try:
        handle = temporal_client.get_workflow_handle(task.temporal_workflow_id)
        await handle.signal(ProcessMovieWorkflow.cancel_processing)
    except Exception:  # noqa: BLE001
        pass

    return CancelTaskResult(data=to_task(task))
