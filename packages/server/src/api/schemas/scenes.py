"""Scene endpoint schemas."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain import Frame, Scene
from src.domain.search import (
    ConclusionPayload,
    ErrorPayload,
    ResultsFoundPayload,
    SearchingPayload,
    SearchStartedPayload,
    ThinkingPayload,
)


class ReadSceneParams(BaseModel):
    """This object represents the parameters used to read the scene."""

    scene_id: UUID = Field(..., description="Unique scene identifier.")


class SceneFileParams(BaseModel):
    """This object represents the parameters used to read the scene video."""

    scene_id: UUID = Field(..., description="Unique scene identifier.")


class SearchSseEventSchema(BaseModel):
    """OpenAPI documentation: all SSE event types for scene search.

    Each field name corresponds to the SSE `event` field value;
    the field type is the JSON payload sent in the SSE `data` field.
    This model is not used at runtime — it exists only for schema generation.
    """

    search_started: SearchStartedPayload
    thinking: ThinkingPayload
    searching: SearchingPayload
    results_found: ResultsFoundPayload
    conclusion: ConclusionPayload
    error: ErrorPayload


class ReadSceneResult(BaseModel):
    """This object represents the result when scene is read."""

    data: Scene
    success: Literal[True] = True


class ListSceneFramesResult(BaseModel):
    """This object represents the result when scene frames are listed."""

    data: list[Frame]
    success: Literal[True] = True
