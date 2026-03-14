"""Scene and search endpoints."""

from __future__ import annotations

from uuid import UUID

import structlog
from litestar import get, post
from litestar.exceptions import ClientException, NotFoundException
from litestar.response import Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.controllers._mappers import to_frame, to_scene
from src.api.errors import READ_SCENE_ERROR, SCENE_FRAMES_ERROR, SCENE_VIDEO_ERROR, SEARCH_SCENES_ERROR
from src.api.schemas.scenes import (
    ListSceneFramesResult,
    ReadSceneResult,
    SceneSearchHit,
    SearchScenesInput,
    SearchScenesResult,
)
from src.config import PRESIGNED_URL_TTL_SEC, settings
from src.services.factory import get_emb, get_storage
from src.services.frame import FrameService
from src.services.scene import SceneService

logger = structlog.get_logger(__name__)


def _distance_to_score(distance: float | None) -> float | None:
    if distance is None:
        return None
    return max(0.0, min(1.0, 1.0 - (distance / 2.0)))


@post(
    f"{settings.base_path}/search/scenes",
    tags=["Search"],
    summary="Search scenes",
    description="Semantic scene search over transcript, annotation and visual embeddings.",
)
async def search_scenes(session: AsyncSession, data: SearchScenesInput) -> SearchScenesResult:
    if not data.query.strip():
        raise ClientException(status_code=400, detail=SEARCH_SCENES_ERROR[400])

    try:
        emb = get_emb()
        scene_service = SceneService(session)
        vectors = await emb.embed_texts([data.query])
        query_vector = vectors[0]
        results = await scene_service.search(query_vector, movie_id=data.movie_id, limit=data.limit)

        hits = []
        for scene_model, distance, transcript_distance, annotation_distance, image_distance in results:
            scene = to_scene(scene_model)
            score = _distance_to_score(distance)
            if score is None:
                continue
            payload = scene.model_dump(mode="json")
            payload["score"] = score
            payload["transcript_score"] = _distance_to_score(transcript_distance)
            payload["annotation_score"] = _distance_to_score(annotation_distance)
            payload["image_score"] = _distance_to_score(image_distance)
            hits.append(SceneSearchHit.model_validate(payload))
        return SearchScenesResult(data=hits)
    except Exception as exc:
        logger.error(
            "scene search failed",
            query=data.query,
            movie_id=str(data.movie_id) if data.movie_id else None,
            limit=data.limit,
            error=str(exc),
            exc_info=True,
        )
        raise


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


@get(
    f"{settings.base_path}/scenes/{{scene_id:uuid}}/video",
    tags=["Scene"],
    summary="Get scene video",
    description="Redirect to a presigned URL for scene video clip.",
)
async def stream_scene_video(session: AsyncSession, scene_id: UUID) -> Response[None]:
    scene_service = SceneService(session)
    storage = get_storage()
    scene = await scene_service.get(scene_id)
    if scene is None or not scene.video_s3_key:
        raise NotFoundException(SCENE_VIDEO_ERROR[404])
    presigned_url = await storage.generate_presigned_get_url(scene.video_s3_key, expires_in=PRESIGNED_URL_TTL_SEC)
    return Response(content=None, status_code=302, headers={"Location": presigned_url})


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
