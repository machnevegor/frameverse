"""Shot boundary extraction protocol."""

from __future__ import annotations

from collections.abc import AsyncGenerator
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
    ) -> AsyncGenerator[tuple[int, Path], None]: ...

    async def extract_keyframes(
        self,
        clip_path: str,
        max_keyframes: int,
        min_gap_sec: float,
        min_score_percentile: int,
    ) -> list[KeyframeData]: ...
