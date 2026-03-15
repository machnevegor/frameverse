"""Search domain models and SSE event types."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.frame import Frame
from src.domain.scene import Scene


class SearchEventType(StrEnum):
    SEARCH_STARTED = "search_started"
    THINKING = "thinking"
    SEARCHING = "searching"
    RESULTS_FOUND = "results_found"
    CONCLUSION = "conclusion"
    ERROR = "error"


class SearchStartedPayload(BaseModel):
    """Emitted once when the search begins."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., description="Original search query from the user.")


class ThinkingPayload(BaseModel):
    """Emitted when the LLM produces a reasoning step (content field)."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(..., description="Brief LLM reasoning step in Russian.")


class SearchingPayload(BaseModel):
    """Emitted when the LLM calls search_scenes tool."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., description="Query used for both text and visual embedding channels.")


class ResultsFoundPayload(BaseModel):
    """Emitted after each search_scenes execution with the running unique candidate count."""

    model_config = ConfigDict(extra="forbid")

    count: int = Field(..., description="Total unique candidate scenes found so far.")


class SearchResultScene(BaseModel):
    """A scene paired with its best representative frame."""

    model_config = ConfigDict(extra="forbid")

    scene: Scene = Field(..., description="Scene data.")
    frames: list[Frame] = Field(..., description="Representative frames for the scene.")


class SearchResultGroup(BaseModel):
    """A group of scenes from one movie."""

    model_config = ConfigDict(extra="forbid")

    movie_id: UUID = Field(..., description="Unique movie identifier.")
    movie_title: str = Field(..., description="Movie title.")
    scenes: list[SearchResultScene] = Field(
        ...,
        description="Relevant scenes from this movie, ordered by relevance.",
    )


class SearchResult(BaseModel):
    """Final re-ranked and grouped search result."""

    model_config = ConfigDict(extra="forbid")

    groups: list[SearchResultGroup] = Field(
        ...,
        description="Grouped scenes, ordered by first scene relevance.",
    )
    summary: str = Field(..., description="LLM-generated summary in Russian.")


class ConclusionPayload(BaseModel):
    """Emitted as the final event with the complete search result."""

    model_config = ConfigDict(extra="forbid")

    result: SearchResult = Field(..., description="Final grouped and re-ranked result.")


class ErrorPayload(BaseModel):
    """Emitted when an unrecoverable error occurs."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(..., description="Error description.")
