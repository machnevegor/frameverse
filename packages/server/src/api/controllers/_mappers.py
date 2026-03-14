"""DTO mapper helpers for API controllers."""

from __future__ import annotations

from src.config import settings
from src.domain import (
    Frame,
    Movie,
    Progress,
    Scene,
    SceneAnnotation,
    SceneTranscript,
    Task,
    TranscriptSegment,
)


def _api_url(*parts: str) -> str:
    base = settings.base_url.rstrip("/")
    base_path = settings.base_path.rstrip("/")
    suffix = "/".join(part.strip("/") for part in parts)
    return f"{base}{base_path}/{suffix}"


def _temporal_url(workflow_id: str) -> str:
    return f"{settings.temporal_public_url.rstrip('/')}/workflows/{workflow_id}"


def _langfuse_url(trace_id: str) -> str:
    return f"{settings.langfuse_public_url.rstrip('/')}/traces/{trace_id}"


def to_task(model) -> Task:
    progress_obj = Progress.model_validate(model.progress) if model.progress is not None else None
    return Task.model_validate(
        {
            "id": model.id,
            "updated_at": model.updated_at,
            "created_at": model.created_at,
            "movie_id": model.movie_id,
            "movie_title": model.movie_title,
            "status": model.status,
            "progress": progress_obj,
            "error_message": model.error_message,
            "error_code": model.error_code,
            "temporal_workflow_id": model.temporal_workflow_id,
            "temporal_workflow_url": _temporal_url(model.temporal_workflow_id),
            "langfuse_trace_id": model.langfuse_trace_id,
            "langfuse_trace_url": _langfuse_url(model.langfuse_trace_id),
        },
    )


def to_movie(model, *, last_task: Task | None, poster_url: str | None) -> Movie:
    return Movie.model_validate(
        {
            "id": model.id,
            "updated_at": model.updated_at,
            "created_at": model.created_at,
            "title": model.title,
            "year": model.year,
            "slogan": model.slogan,
            "genres": model.genres,
            "description": model.description,
            "short_description": model.short_description,
            "duration": model.duration,
            "poster_url": poster_url,
            "video_url": _api_url("movies", str(model.id), "video"),
            "audio_url": _api_url("movies", str(model.id), "audio") if model.audio_s3_key else None,
            "last_task": last_task,
        },
    )


def to_scene(model) -> Scene:
    transcript = SceneTranscript.model_validate(model.transcript)
    annotation = SceneAnnotation.model_validate(model.annotation) if model.annotation is not None else None
    return Scene.model_validate(
        {
            "id": model.id,
            "updated_at": model.updated_at,
            "created_at": model.created_at,
            "status": model.status,
            "movie_id": model.movie_id,
            "position": model.position,
            "start": model.start,
            "end": model.end,
            "duration": model.duration,
            "transcript": transcript,
            "annotation": annotation,
            "video_url": _api_url("scenes", str(model.id), "video") if model.video_s3_key else None,
        },
    )


def to_frame(model) -> Frame:
    return Frame.model_validate(
        {
            "id": model.id,
            "updated_at": model.updated_at,
            "created_at": model.created_at,
            "movie_id": model.movie_id,
            "scene_id": model.scene_id,
            "position": model.position,
            "timestamp": model.timestamp,
            "score": model.score,
            "image_url": _api_url("frames", str(model.id), "image"),
        },
    )


def to_transcript_segments(raw_segments: list[dict]) -> list[TranscriptSegment]:
    return [TranscriptSegment.model_validate(item) for item in raw_segments]
