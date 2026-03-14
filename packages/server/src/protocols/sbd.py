"""Shot boundary detection protocol."""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(slots=True)
class DetectedScene:
    """Detected scene start point in seconds; end is derived from the next scene's start."""

    scene_index: int
    start_time: float


@runtime_checkable
class SBDProtocol(Protocol):
    """Contract for SBD adapters."""

    async def detect_scenes(self, video_path: str) -> list[DetectedScene]: ...
