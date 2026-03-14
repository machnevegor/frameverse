from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from src.domain.annotation import SceneAnnotation
from src.domain.status import SceneStatus
from src.domain.transcript import SceneTranscript


class Scene(BaseModel):
    """This object represents a movie scene."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(..., description="Unique scene identifier.")
    updated_at: datetime = Field(..., description="Date and time of last scene update.")
    created_at: datetime = Field(..., description="Date and time of scene creation.")

    status: SceneStatus = Field(..., description="Scene status.")

    movie_id: UUID = Field(..., description="Unique movie identifier.")
    position: int = Field(..., description="Scene position within the movie (0-based).")

    start: float = Field(..., description="Start time of the scene in seconds.", ge=0)
    end: float = Field(..., description="End time of the scene in seconds.", ge=0)
    duration: float = Field(..., description="Duration of the scene in seconds.", ge=0)

    transcript: SceneTranscript = Field(..., description="Transcript context for the scene.")
    annotation: SceneAnnotation | None = Field(None, description="_Optional_. Annotation for the scene.")

    video_url: HttpUrl | None = Field(None, description="_Optional_. URL of the scene video (with audio track).")
