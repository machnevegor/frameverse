from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from src.domain.status import MovieStatus, TaskErrorCode


class Progress(BaseModel):
    """This object represents scene-level progress counters for a task."""

    model_config = ConfigDict(extra="forbid")

    scenes_detected: int = Field(..., description="Number of scenes detected.", ge=0)
    scenes_extracted: int = Field(0, description="Number of scenes with extracted video clips.", ge=0)
    scenes_annotated: int = Field(0, description="Number of scenes with completed annotations.", ge=0)
    scenes_embedded: int = Field(0, description="Number of scenes with completed embeddings.", ge=0)


class Task(BaseModel):
    """This object represents a movie processing task."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(..., description="Unique task identifier")
    updated_at: datetime = Field(..., description="Date and time of last task update")
    created_at: datetime = Field(..., description="Date and time of task creation")

    movie_id: UUID = Field(..., description="Unique movie identifier.")
    movie_title: str = Field(..., description="Title of the associated movie.")

    status: MovieStatus = Field(..., description="Task status.")
    progress: Progress | None = Field(None, description="_Optional_. Scene-level task progress.")

    error_message: str | None = Field(None, description="_Optional_. Error message describing what went wrong.")
    error_code: TaskErrorCode | None = Field(None, description="_Optional_. Error code for programmatic handling.")

    temporal_workflow_id: str = Field(..., description="Temporal workflow ID.")
    temporal_workflow_url: HttpUrl = Field(..., description="Temporal workflow URL.")
    langfuse_trace_id: str = Field(..., description="Langfuse trace ID.")
    langfuse_trace_url: HttpUrl = Field(..., description="Langfuse trace URL.")
