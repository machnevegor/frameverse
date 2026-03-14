from pydantic import BaseModel, ConfigDict, Field


class SceneAnnotation(BaseModel):
    """This object represents a scene annotation."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(..., description="Scene annotation text.")
