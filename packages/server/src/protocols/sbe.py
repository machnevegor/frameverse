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


SceneClipMode = Literal["copy", "reencode"]


@runtime_checkable
class SBEProtocol(Protocol):
    """Contract for SBE adapters."""

    async def list_video_keyframe_times(
        self,
        video_path: str,
    ) -> list[float]: ...

    async def extract_scene_clip(
        self,
        video_path: str,
        *,
        start_sec: float,
        end_sec: float,
        clip_path: str,
        mode: SceneClipMode,
        nearest_keyframe_sec: float | None = None,
    ) -> Path: ...

    async def extract_clip_keyframes(
        self,
        clip_path: str,
        max_keyframes: int,
        min_gap_sec: float,
        min_score_percentile: int,
    ) -> list[KeyframeData]: ...
