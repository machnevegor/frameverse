"""Task endpoint schemas."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain import PaginationInfo, Task


class CreateTaskInput(BaseModel):
    """This object represents the input for creating a processing task."""

    s3_key: str = Field(..., description="S3 key returned by the presign endpoint.")
    title: str = Field(..., description="Movie title.")
    year: int | None = Field(None, description="_Optional_. Movie release year.")
    slogan: str | None = Field(None, description="_Optional_. Movie slogan.")
    genres: list[str] | None = Field(None, description="_Optional_. Movie genres.")
    description: str | None = Field(None, description="_Optional_. Movie description.")
    short_description: str | None = Field(None, description="_Optional_. Movie short description.")
    poster_s3_key: str | None = Field(None, description="_Optional_. S3 key for movie poster.")


class ReadTaskParams(BaseModel):
    """This object represents the parameters used to read the task."""

    task_id: UUID = Field(..., description="Unique task identifier.")


class CancelTaskParams(BaseModel):
    """This object represents the parameters used to cancel the task."""

    task_id: UUID = Field(..., description="Unique task identifier.")


class CreateTaskResult(BaseModel):
    """This object represents the result when task is created."""

    data: Task
    success: Literal[True] = True


class ReadTaskResult(BaseModel):
    """This object represents the result when task is read."""

    data: Task
    success: Literal[True] = True


class CancelTaskResult(BaseModel):
    """This object represents the result when task is cancelled."""

    data: Task
    success: Literal[True] = True


class ListTasksResult(BaseModel):
    """This object represents the result when tasks are listed."""

    data: list[Task]
    pagination: PaginationInfo
    success: Literal[True] = True
