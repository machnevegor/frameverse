from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from src.domain.task import Task


class Movie(BaseModel):
    """This object represents a movie."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(..., description="Unique movie identifier.")
    updated_at: datetime = Field(..., description="Date and time of last movie update.")
    created_at: datetime = Field(..., description="Date and time of movie creation.")

    title: str = Field(..., description="Movie title.")
    year: int | None = Field(None, description="_Optional_. Movie release year.")
    slogan: str | None = Field(None, description="_Optional_. Movie slogan.")

    genres: list[str] | None = Field(None, description="_Optional_. Movie genres.")
    description: str | None = Field(None, description="_Optional_. Movie description.")
    short_description: str | None = Field(None, description="_Optional_. Movie short description.")
    duration: float | None = Field(None, description="_Optional_. Movie duration in seconds.")

    poster_url: HttpUrl | None = Field(None, description="_Optional_. URL of the movie poster image.")
    video_url: HttpUrl = Field(..., description="URL of the movie video (with audio track).")
    audio_url: HttpUrl | None = Field(None, description="_Optional_. URL of the extracted audio-only track.")

    last_task: Task | None = Field(None, description="_Optional_. Most recent processing task for the movie.")
