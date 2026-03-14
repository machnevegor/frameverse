from pydantic import BaseModel, ConfigDict, Field


class TranscriptSegment(BaseModel):
    """This object represents a time-aligned segment of a transcription."""

    model_config = ConfigDict(extra="forbid")

    start: float = Field(..., description="Start time of the segment in seconds.", ge=0)
    end: float = Field(..., description="End time of the segment in seconds.", ge=0)
    text: str = Field(..., description="Text content of the segment.")
    speaker: str | None = Field(None, description="Speaker identifier for the segment.")


class SceneTranscript(BaseModel):
    """This object represents transcript segments before, within, and after a scene time window."""

    model_config = ConfigDict(extra="forbid")

    left_segments: list[TranscriptSegment] = Field(
        default_factory=list,
        description="Transcript segments before the scene time window.",
    )
    scene_segments: list[TranscriptSegment] = Field(
        default_factory=list,
        description="Transcript segments inside the scene time window.",
    )
    right_segments: list[TranscriptSegment] = Field(
        default_factory=list,
        description="Transcript segments after the scene time window.",
    )
