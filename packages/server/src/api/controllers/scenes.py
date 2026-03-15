"""Scene and search endpoints."""

from __future__ import annotations

from uuid import UUID

from litestar import get, head
from litestar.exceptions import NotFoundException
from litestar.params import Parameter
from litestar.response import Response, ServerSentEvent
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.controllers._mappers import to_frame, to_scene
from src.api.errors import READ_SCENE_ERROR, SCENE_FRAMES_ERROR, SCENE_VIDEO_ERROR
from src.api.schemas.scenes import ListSceneFramesResult, ReadSceneResult
from src.config import PRESIGNED_URL_TTL_SEC, settings
from src.services.factory import get_openrouter, get_storage
from src.services.frame import FrameService
from src.services.scene import SceneService
from src.services.search import SearchService


@get(
    f"{settings.base_path}/search/scenes",
    tags=["Search"],
    summary="Search scenes (SSE)",
    description=(
        "Server-Sent Events stream for semantic scene search with LLM re-ranking.\n\n"
        "## SSE Event Types\n\n"
        "- **search_started** — search initiated (SearchStartedPayload)\n"
        "- **thinking** — LLM reasoning step (ThinkingPayload)\n"
        "- **searching** — executing vector search (SearchingPayload)\n"
        "- **results_found** — total unique candidates found so far (ResultsFoundPayload)\n"
        "- **conclusion** — final grouped result (ConclusionPayload)\n"
        "- **error** — unrecoverable error (ErrorPayload)\n\n"
        "All events carry JSON in the `data` field. "
        "Payload schemas: `SearchStartedPayload`, `ThinkingPayload`, `SearchingPayload`, "
        "`ResultsFoundPayload`, `ConclusionPayload`, `ErrorPayload`."
    ),
    media_type="text/event-stream",
)
async def search_scenes_stream(
    session: AsyncSession,
    query: str = Parameter(min_length=1, description="Natural language search query."),
    movie_id: UUID | None = Parameter(default=None, required=False, description="Restrict search to one movie."),
) -> ServerSentEvent:
    service = SearchService(session, get_openrouter(), get_storage())
    return ServerSentEvent(service.search(query, movie_id))


@get(
    f"{settings.base_path}/scenes/{{scene_id:uuid}}",
    tags=["Scene"],
    summary="Get scene",
    description="Get scene by identifier.",
)
async def read_scene(session: AsyncSession, scene_id: UUID) -> ReadSceneResult:
    scene_service = SceneService(session)
    scene = await scene_service.get(scene_id)
    if scene is None:
        raise NotFoundException(READ_SCENE_ERROR[404])
    return ReadSceneResult(data=to_scene(scene))


async def _scene_video_response(scene_id: UUID, session: AsyncSession) -> Response[None]:
    """Shared logic for GET/HEAD scene video: 302 to presigned URL or 404."""
    scene_service = SceneService(session)
    storage = get_storage()
    scene = await scene_service.get(scene_id)
    if scene is None or not scene.video_s3_key:
        raise NotFoundException(SCENE_VIDEO_ERROR[404])
    presigned_url = await storage.generate_presigned_get_url(scene.video_s3_key, expires_in=PRESIGNED_URL_TTL_SEC)
    return Response(content=None, status_code=302, headers={"Location": presigned_url})


@get(
    f"{settings.base_path}/scenes/{{scene_id:uuid}}/video",
    tags=["Scene"],
    summary="Get scene video",
    description="Redirect to a presigned URL for scene video clip.",
)
async def stream_scene_video(session: AsyncSession, scene_id: UUID) -> Response[None]:
    return await _scene_video_response(scene_id, session)


@head(
    f"{settings.base_path}/scenes/{{scene_id:uuid}}/video",
    tags=["Scene"],
    summary="Head scene video",
    description="Same as GET but without body; used by clients to check availability.",
)
async def head_scene_video(session: AsyncSession, scene_id: UUID) -> Response[None]:
    return await _scene_video_response(scene_id, session)


@get(
    f"{settings.base_path}/scenes/{{scene_id:uuid}}/frames",
    tags=["Scene"],
    summary="List scene frames",
    description="List all keyframes of a scene.",
)
async def list_scene_frames(session: AsyncSession, scene_id: UUID) -> ListSceneFramesResult:
    scene_service = SceneService(session)
    frame_service = FrameService(session)
    scene = await scene_service.get(scene_id)
    if scene is None:
        raise NotFoundException(SCENE_FRAMES_ERROR[404])
    frames = await frame_service.list_by_scene(scene_id)
    return ListSceneFramesResult(data=[to_frame(frame) for frame in frames])
