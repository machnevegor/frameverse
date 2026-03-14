"""CDN endpoint schemas."""

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class PresignInput(BaseModel):
    """This object represents the input for generating a presigned upload URL."""

    content_type: str = Field(default="video/mp4", description="MIME type of the video file.")


class PresignData(BaseModel):
    """This object represents generated presigned upload metadata."""

    upload_url: HttpUrl = Field(..., description="Presigned PUT URL for direct upload.")
    s3_key: str = Field(..., description="Object key in S3 bucket.")
    expires_in: int = Field(..., description="URL expiration time in seconds.")


class PresignResult(BaseModel):
    """This object represents the result of generating a presigned upload URL."""

    data: PresignData
    success: Literal[True] = True
