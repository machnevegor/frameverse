"""Frame endpoint schemas."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain import Frame


class ReadFrameParams(BaseModel):
    """This object represents the parameters used to read the frame."""

    frame_id: UUID = Field(..., description="Unique frame identifier.")


class ReadFrameResult(BaseModel):
    """This object represents the result when frame is read."""

    data: Frame
    success: Literal[True] = True
