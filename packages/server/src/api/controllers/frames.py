"""Frame endpoints."""

from __future__ import annotations

from uuid import UUID

from litestar import get
from litestar.exceptions import NotFoundException
from litestar.response import Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.controllers._mappers import to_frame
from src.api.errors import FRAME_IMAGE_ERROR, READ_FRAME_ERROR
from src.api.schemas.frames import ReadFrameResult
from src.config import settings
from src.services.factory import get_storage
from src.services.frame import FrameService


@get(
    f"{settings.base_path}/frames/{{frame_id:uuid}}",
    tags=["Frame"],
    summary="Get frame",
    description="Get frame metadata by identifier.",
)
async def read_frame(session: AsyncSession, frame_id: UUID) -> ReadFrameResult:
    frame_service = FrameService(session)
    frame = await frame_service.get(frame_id)
    if frame is None:
        raise NotFoundException(READ_FRAME_ERROR[404])
    return ReadFrameResult(data=to_frame(frame))


@get(
    f"{settings.base_path}/frames/{{frame_id:uuid}}/image",
    tags=["Frame"],
    summary="Get frame image",
    description="Download frame image file.",
)
async def read_frame_image(session: AsyncSession, frame_id: UUID) -> Response[bytes]:
    frame_service = FrameService(session)
    storage = get_storage()
    frame = await frame_service.get(frame_id)
    if frame is None:
        raise NotFoundException(FRAME_IMAGE_ERROR[404])
    data = await storage.download(frame.image_s3_key)
    return Response(content=data, media_type="image/jpeg")
