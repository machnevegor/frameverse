from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class Frame(BaseModel):
    """This object represents a movie frame."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(..., description="Unique frame identifier.")
    updated_at: datetime = Field(..., description="Date and time of last frame update.")
    created_at: datetime = Field(..., description="Date and time of frame creation.")

    movie_id: UUID = Field(..., description="Unique movie identifier.")
    scene_id: UUID = Field(..., description="Unique scene identifier.")
    position: int = Field(..., description="Frame position within the scene (0-based).")

    timestamp: float = Field(..., description="Time of the frame in seconds from scene start.", ge=0)
    score: float = Field(..., description="Frame ranking score used for keyframe selection.", ge=0, le=1)

    image_url: HttpUrl = Field(..., description="URL of the frame image.")
