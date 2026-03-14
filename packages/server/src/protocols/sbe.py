"""Shot boundary extraction protocol."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass(slots=True)
class KeyframeData:
    """Scored keyframe payload."""

    timestamp: float
    score: float
    image_data: bytes


@runtime_checkable
class SBEProtocol(Protocol):
    """Contract for SBE adapters."""

    def stream_clips(
        self,
        source: str,
        split_times: list[float],
        output_dir: str,
    ) -> AsyncIterator[tuple[int, Path]]:
        """Yield (clip_index, path) as ffmpeg produces completed segment files.

        split_times must start with 0.0 and be strictly ascending.
        Expected clip count equals len(split_times).
        """
        ...

    async def extract_keyframes(
        self,
        clip_path: str,
        max_keyframes: int,
        min_gap_sec: float,
        min_score_percentile: int,
    ) -> list[KeyframeData]: ...
