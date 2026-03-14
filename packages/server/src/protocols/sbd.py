"""Shot boundary detection protocol."""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(slots=True)
class DetectedScene:
    """Detected scene interval in seconds."""

    scene_index: int
    start_time: float
    end_time: float


@runtime_checkable
class SBDProtocol(Protocol):
    """Contract for SBD adapters."""

    async def detect_scenes(self, video_path: str) -> list[DetectedScene]: ...
