"""CDN endpoints."""

from uuid import uuid4

from litestar import post
from litestar.exceptions import ClientException

from src.api.errors import PRESIGN_ERROR
from src.api.schemas.cdn import PresignData, PresignInput, PresignResult
from src.config import (
    PRESIGNED_URL_TTL_SEC,
    SUPPORTED_IMAGE_UPLOAD_TYPES,
    SUPPORTED_VIDEO_UPLOAD_TYPES,
    settings,
)
from src.services.factory import get_storage


@post(
    f"{settings.base_path}/presign",
    tags=["CDN"],
    summary="Create presigned upload URL",
    description="Generate a presigned PUT URL for direct video or poster upload to object storage.",
)
async def presign(data: PresignInput) -> PresignResult:
    if data.content_type in SUPPORTED_VIDEO_UPLOAD_TYPES:
        s3_key = f"uploads/{uuid4()}/original.mp4"
    elif data.content_type in SUPPORTED_IMAGE_UPLOAD_TYPES:
        s3_key = f"uploads/{uuid4()}/poster.webp"
    else:
        raise ClientException(status_code=415, detail=PRESIGN_ERROR[415])

    storage = get_storage()
    upload_url = await storage.generate_presigned_put_url(
        s3_key,
        expires_in=PRESIGNED_URL_TTL_SEC,
        content_type=data.content_type,
    )
    return PresignResult(
        data=PresignData(
            upload_url=upload_url,
            s3_key=s3_key,
            expires_in=PRESIGNED_URL_TTL_SEC,
        ),
    )
