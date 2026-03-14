"""Scene endpoint schemas."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain import Frame, Scene


class ReadSceneParams(BaseModel):
    """This object represents the parameters used to read the scene."""

    scene_id: UUID = Field(..., description="Unique scene identifier.")


class SceneFileParams(BaseModel):
    """This object represents the parameters used to read the scene video."""

    scene_id: UUID = Field(..., description="Unique scene identifier.")


class SearchScenesInput(BaseModel):
    """This object represents the input for semantic scene search."""

    query: str = Field(..., min_length=1, description="Natural language search query.")
    movie_id: UUID | None = Field(None, description="_Optional_. Restrict search to one movie.")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results.")


class SceneSearchHit(Scene):
    """This object represents a scene search hit with similarity score."""

    score: float = Field(..., description="Cosine similarity score in range [0, 1].")


class SearchScenesResult(BaseModel):
    """This object represents the result of semantic scene search."""

    data: list[SceneSearchHit]
    success: Literal[True] = True


class ReadSceneResult(BaseModel):
    """This object represents the result when scene is read."""

    data: Scene
    success: Literal[True] = True


class ListSceneFramesResult(BaseModel):
    """This object represents the result when scene frames are listed."""

    data: list[Frame]
    success: Literal[True] = True
