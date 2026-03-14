"""ASR provider protocol."""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from src.domain import TranscriptSegment


@dataclass(slots=True)
class TranscriptResult:
    """ASR response payload."""

    text: str
    language: str | None
    duration: float | None
    segments: list[TranscriptSegment]


@runtime_checkable
class ASRProtocol(Protocol):
    """Contract for ASR adapters."""

    async def transcribe(
        self,
        audio_url: str,
        *,
        trace_id: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> TranscriptResult: ...
