"""Movie endpoints."""

from __future__ import annotations

import math
from uuid import UUID

from litestar import delete, get, head
from litestar.exceptions import NotFoundException
from litestar.response import Response
from sqlalchemy.ext.asyncio import AsyncSession
from temporalio.client import Client

from src.api.controllers._mappers import to_movie, to_scene, to_task, to_transcript_segments
from src.api.errors import (
    DELETE_MOVIE_ERROR,
    MOVIE_AUDIO_ERROR,
    MOVIE_SCENES_ERROR,
    MOVIE_TRANSCRIPT_ERROR,
    MOVIE_VIDEO_ERROR,
    READ_MOVIE_ERROR,
)
from src.api.schemas.movies import ListMovieScenesResult, ListMoviesResult, MovieTranscriptResult, ReadMovieResult
from src.config import PRESIGNED_URL_TTL_SEC, settings
from src.domain import PaginationInfo
from src.services.factory import get_storage
from src.services.movie import MovieService
from src.services.scene import SceneService
from src.services.task import TaskService
from src.workers.workflows import ProcessMovieWorkflow


@get(
    f"{settings.base_path}/movies",
    tags=["Movie"],
    summary="List movies",
    description="List all movies with pagination.",
)
async def list_movies(session: AsyncSession, page: int = 1, per_page: int = 20) -> ListMoviesResult:
    movie_service = MovieService(session)
    task_service = TaskService(session)
    storage = get_storage()

    offset = max(0, page - 1) * per_page
    movies, total = await movie_service.list(limit=per_page, offset=offset)
    items = []
    for movie in movies:
        last_task_model = await task_service.get_latest_by_movie_id(movie.id)
        last_task = to_task(last_task_model) if last_task_model is not None else None
        poster_url = (
            await storage.generate_presigned_get_url(movie.poster_s3_key, expires_in=PRESIGNED_URL_TTL_SEC)
            if movie.poster_s3_key
            else None
        )
        items.append(to_movie(movie, last_task=last_task, poster_url=poster_url))

    total_pages = max(1, math.ceil(total / per_page)) if per_page > 0 else 1
    pagination = PaginationInfo(
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total_items=total,
        has_next=page < total_pages,
        cursor=str(movies[-1].id) if movies else None,
    )
    return ListMoviesResult(data=items, pagination=pagination)


@get(
    f"{settings.base_path}/movies/{{movie_id:uuid}}",
    tags=["Movie"],
    summary="Get movie",
    description="Get movie by identifier.",
)
async def read_movie(session: AsyncSession, movie_id: UUID) -> ReadMovieResult:
    movie_service = MovieService(session)
    task_service = TaskService(session)
    storage = get_storage()

    movie = await movie_service.get(movie_id)
    if movie is None:
        raise NotFoundException(READ_MOVIE_ERROR[404])
    last_task_model = await task_service.get_latest_by_movie_id(movie.id)
    last_task = to_task(last_task_model) if last_task_model is not None else None
    poster_url = (
        await storage.generate_presigned_get_url(movie.poster_s3_key, expires_in=PRESIGNED_URL_TTL_SEC)
        if movie.poster_s3_key
        else None
    )
    return ReadMovieResult(data=to_movie(movie, last_task=last_task, poster_url=poster_url))


@delete(
    f"{settings.base_path}/movies/{{movie_id:uuid}}",
    tags=["Movie"],
    summary="Delete movie",
    description="Delete movie and all derived processing artifacts.",
)
async def delete_movie(session: AsyncSession, temporal_client: Client, movie_id: UUID) -> Response[None]:
    movie_service = MovieService(session)
    task_service = TaskService(session)
    scene_service = SceneService(session)
    storage = get_storage()

    movie = await movie_service.get(movie_id)
    if movie is None:
        raise NotFoundException(DELETE_MOVIE_ERROR[404])

    active_tasks = await task_service.list_active_by_movie_id(movie_id)
    for active_task in active_tasks:
        active_task.status = "cancelled"
        await scene_service.cancel_non_terminal_for_movie(movie_id)
        try:
            handle = temporal_client.get_workflow_handle(active_task.temporal_workflow_id)
            await handle.signal(ProcessMovieWorkflow.cancel_processing)
        except Exception:  # noqa: BLE001
            pass

    await storage.delete_prefix(f"movies/{movie_id}/")
    await movie_service.delete(movie)
    await session.commit()
    return Response(content=None, status_code=204)


async def _movie_video_response(movie_id: UUID, session: AsyncSession) -> Response[None]:
    """Shared logic for GET/HEAD movie video: 302 to presigned URL or 404."""
    movie_service = MovieService(session)
    storage = get_storage()
    movie = await movie_service.get(movie_id)
    if movie is None or not movie.video_s3_key:
        raise NotFoundException(MOVIE_VIDEO_ERROR[404])
    presigned_url = await storage.generate_presigned_get_url(movie.video_s3_key, expires_in=PRESIGNED_URL_TTL_SEC)
    return Response(content=None, status_code=302, headers={"Location": presigned_url})


@get(
    f"{settings.base_path}/movies/{{movie_id:uuid}}/video",
    tags=["Movie"],
    summary="Get movie video",
    description="Redirect to a presigned URL for movie video file.",
)
async def stream_movie_video(session: AsyncSession, movie_id: UUID) -> Response[None]:
    return await _movie_video_response(movie_id, session)


@head(
    f"{settings.base_path}/movies/{{movie_id:uuid}}/video",
    tags=["Movie"],
    summary="Head movie video",
    description="Same as GET but without body; used by clients to check availability.",
)
async def head_movie_video(session: AsyncSession, movie_id: UUID) -> Response[None]:
    return await _movie_video_response(movie_id, session)


@get(
    f"{settings.base_path}/movies/{{movie_id:uuid}}/audio",
    tags=["Movie"],
    summary="Get movie audio",
    description="Redirect to a presigned URL for movie audio file.",
)
async def stream_movie_audio(session: AsyncSession, movie_id: UUID) -> Response[None]:
    movie_service = MovieService(session)
    storage = get_storage()
    movie = await movie_service.get(movie_id)
    if movie is None or movie.audio_s3_key is None:
        raise NotFoundException(MOVIE_AUDIO_ERROR[404])
    presigned_url = await storage.generate_presigned_get_url(movie.audio_s3_key, expires_in=PRESIGNED_URL_TTL_SEC)
    return Response(content=None, status_code=302, headers={"Location": presigned_url})


@get(
    f"{settings.base_path}/movies/{{movie_id:uuid}}/transcript",
    tags=["Movie"],
    summary="Get movie transcript",
    description="Get full transcript segments of the movie.",
)
async def read_movie_transcript(session: AsyncSession, movie_id: UUID) -> MovieTranscriptResult:
    movie_service = MovieService(session)
    movie = await movie_service.get(movie_id)
    if movie is None or movie.transcript is None:
        raise NotFoundException(MOVIE_TRANSCRIPT_ERROR[404])
    return MovieTranscriptResult(data=to_transcript_segments(movie.transcript))


@get(
    f"{settings.base_path}/movies/{{movie_id:uuid}}/scenes",
    tags=["Movie"],
    summary="List movie scenes",
    description="List all scenes of one movie.",
)
async def list_movie_scenes(session: AsyncSession, movie_id: UUID) -> ListMovieScenesResult:
    movie_service = MovieService(session)
    scene_service = SceneService(session)
    movie = await movie_service.get(movie_id)
    if movie is None:
        raise NotFoundException(MOVIE_SCENES_ERROR[404])
    scenes = await scene_service.list_by_movie(movie_id)
    return ListMovieScenesResult(data=[to_scene(scene) for scene in scenes])
