"""CDN endpoint schemas."""

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

from src.config import SUPPORTED_IMAGE_UPLOAD_TYPES, SUPPORTED_VIDEO_UPLOAD_TYPES

_SUPPORTED_UPLOAD_TYPES = ", ".join([*SUPPORTED_VIDEO_UPLOAD_TYPES, *SUPPORTED_IMAGE_UPLOAD_TYPES])


class PresignInput(BaseModel):
    """This object represents the input for generating a presigned upload URL."""

    content_type: str = Field(
        default="video/mp4",
        description=f"MIME type of the file to upload. Supported: {_SUPPORTED_UPLOAD_TYPES}.",
    )


class PresignData(BaseModel):
    """This object represents generated presigned upload metadata."""

    upload_url: HttpUrl = Field(..., description="Presigned PUT URL for direct upload.")
    s3_key: str = Field(..., description="Object key in S3 bucket.")
    expires_in: int = Field(..., description="URL expiration time in seconds.")


class PresignResult(BaseModel):
    """This object represents the result of generating a presigned upload URL."""

    data: PresignData
    success: Literal[True] = True
