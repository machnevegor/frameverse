"""Public domain schemas."""

from src.domain.annotation import SceneAnnotation
from src.domain.common import FormattedError, PaginationInfo
from src.domain.frame import Frame
from src.domain.movie import Movie
from src.domain.scene import Scene
from src.domain.search import (
    ConclusionPayload,
    ErrorPayload,
    ResultsFoundPayload,
    SearchEventType,
    SearchingPayload,
    SearchResult,
    SearchResultGroup,
    SearchResultScene,
    SearchStartedPayload,
    ThinkingPayload,
)
from src.domain.status import (
    FailedMovieStatus,
    FailedSceneStatus,
    MovieStatus,
    NonTerminalMovieStatus,
    NonTerminalSceneStatus,
    SceneStatus,
    TaskErrorCode,
    TerminalMovieStatus,
    TerminalSceneStatus,
)
from src.domain.task import Progress, Task
from src.domain.transcript import SceneTranscript, TranscriptSegment

__all__ = [
    "ConclusionPayload",
    "ErrorPayload",
    "FailedMovieStatus",
    "FailedSceneStatus",
    "FormattedError",
    "Frame",
    "Movie",
    "MovieStatus",
    "NonTerminalMovieStatus",
    "NonTerminalSceneStatus",
    "PaginationInfo",
    "Progress",
    "ResultsFoundPayload",
    "Scene",
    "SceneAnnotation",
    "SceneStatus",
    "SceneTranscript",
    "SearchEventType",
    "SearchResult",
    "SearchResultGroup",
    "SearchResultScene",
    "SearchingPayload",
    "SearchStartedPayload",
    "Task",
    "TaskErrorCode",
    "TerminalMovieStatus",
    "TerminalSceneStatus",
    "ThinkingPayload",
    "TranscriptSegment",
]
