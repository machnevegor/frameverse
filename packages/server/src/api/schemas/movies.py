"""Movie endpoint schemas."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain import Movie, PaginationInfo, Scene, TranscriptSegment


class ReadMovieParams(BaseModel):
    """This object represents the parameters used to read the movie."""

    movie_id: UUID = Field(..., description="Unique movie identifier.")


class DeleteMovieParams(BaseModel):
    """This object represents the parameters used to delete the movie."""

    movie_id: UUID = Field(..., description="Unique movie identifier.")


class MovieFileParams(BaseModel):
    """This object represents parameters for reading a movie file."""

    movie_id: UUID = Field(..., description="Unique movie identifier.")


class ReadMovieResult(BaseModel):
    """This object represents the result when movie is read."""

    data: Movie
    success: Literal[True] = True


class ListMoviesResult(BaseModel):
    """This object represents the result when movies are listed."""

    data: list[Movie]
    pagination: PaginationInfo
    success: Literal[True] = True


class MovieTranscriptResult(BaseModel):
    """This object represents the result when movie transcript is read."""

    data: list[TranscriptSegment]
    success: Literal[True] = True


class ListMovieScenesResult(BaseModel):
    """This object represents the result when movie scenes are listed."""

    data: list[Scene]
    success: Literal[True] = True
