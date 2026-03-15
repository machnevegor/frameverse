"""Shot boundary extraction protocol."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable


@dataclass(slots=True)
class KeyframeData:
    """Scored keyframe payload."""

    timestamp: float
    score: float
    image_data: bytes


ClipExtractionMode = Literal["copy", "reencode"]


@runtime_checkable
class SBEProtocol(Protocol):
    """Contract for SBE adapters."""

    async def list_keyframe_times(
        self,
        source: str,
    ) -> list[float]:
        """Return timestamps of keyframes for the primary video stream."""

    async def extract_clip(
        self,
        source: str,
        *,
        start_time: float,
        end_time: float,
        output_path: str,
        mode: ClipExtractionMode,
    ) -> Path:
        """Extract one scene clip and return the produced file path."""

    async def extract_keyframes(
        self,
        clip_path: str,
        max_keyframes: int,
        min_gap_sec: float,
        min_score_percentile: int,
    ) -> list[KeyframeData]: ...
