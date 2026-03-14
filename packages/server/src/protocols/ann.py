"""Scene annotation protocol."""

from typing import Any, Protocol, runtime_checkable

from src.domain import SceneTranscript


@runtime_checkable
class ANNProtocol(Protocol):
    """Contract for scene annotation adapters."""

    async def annotate(
        self,
        movie_info: dict[str, Any],
        keyframe_urls: list[str],
        scene_transcript: SceneTranscript,
        previous_annotations: list[str],
        *,
        trace_id: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> str: ...
