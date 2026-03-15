"""Litestar application factory."""

from __future__ import annotations

from litestar import Litestar
from litestar.di import Provide
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import ScalarRenderPlugin
from temporalio.client import Client

from src.api.controllers.cdn import presign
from src.api.controllers.frames import read_frame, read_frame_image
from src.api.controllers.movies import (
    delete_movie,
    head_movie_video,
    list_movie_scenes,
    list_movies,
    read_movie,
    read_movie_transcript,
    stream_movie_audio,
    stream_movie_video,
)
from src.api.controllers.scenes import (
    head_scene_video,
    list_scene_frames,
    read_scene,
    search_scenes,
    stream_scene_video,
)
from src.api.controllers.tasks import cancel_task, create_task, list_tasks, read_task
from src.config import settings
from src.db.session import get_session, init_db
from src.services.factory import get_storage


async def provide_temporal_client() -> Client:
    """Provide Temporal client bound to configured namespace."""

    return await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)


async def startup() -> None:
    """Initialize DB metadata and object storage bucket."""

    await init_db()
    await get_storage().ensure_bucket()


def create_app() -> Litestar:
    """Create configured Litestar application."""

    return Litestar(
        request_max_body_size=None,
        route_handlers=[
            presign,
            list_tasks,
            create_task,
            read_task,
            cancel_task,
            list_movies,
            read_movie,
            delete_movie,
            stream_movie_video,
            head_movie_video,
            stream_movie_audio,
            read_movie_transcript,
            list_movie_scenes,
            search_scenes,
            read_scene,
            stream_scene_video,
            head_scene_video,
            list_scene_frames,
            read_frame,
            read_frame_image,
        ],
        dependencies={
            "session": Provide(get_session),
            "temporal_client": Provide(provide_temporal_client),
        },
        on_startup=[startup],
        openapi_config=OpenAPIConfig(
            title="Frameverse API",
            version="0.1.0",
            description="Frameverse movie preprocessing and semantic search API.",
            path=f"{settings.base_path}/schema",
            render_plugins=[ScalarRenderPlugin()],
        ),
    )
