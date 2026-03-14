"""SQLAlchemy models for Frameverse entities."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from advanced_alchemy.base import UUIDAuditBase
from advanced_alchemy.types import JsonB
from pgvector.sqlalchemy import Vector
from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config import EMB_DIMENSIONS


class TaskModel(UUIDAuditBase):
    """Movie processing task."""

    __tablename__ = "tasks"
    __table_args__ = (Index("ix_tasks_movie_id_status", "movie_id", "status"),)

    # ownership
    movie_id: Mapped[UUID] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # business data
    movie_title: Mapped[str] = mapped_column(String(length=512), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(length=32), nullable=False, index=True)
    progress: Mapped[dict[str, Any] | None] = mapped_column(JsonB, nullable=True)

    # diagnostics
    error_code: Mapped[str | None] = mapped_column(String(length=64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # workflow metadata
    temporal_workflow_id: Mapped[str] = mapped_column(String(length=255), nullable=False, unique=True, index=True)
    langfuse_trace_id: Mapped[str] = mapped_column(String(length=255), nullable=False, unique=True, index=True)

    movie: Mapped[MovieModel] = relationship(back_populates="tasks")


class MovieModel(UUIDAuditBase):
    """Movie metadata."""

    __tablename__ = "movies"
    __table_args__ = (UniqueConstraint("title", name="uq_movies_title"),)

    # descriptive fields
    title: Mapped[str] = mapped_column(String(length=512), nullable=False, unique=True, index=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    slogan: Mapped[str | None] = mapped_column(String(length=2048), nullable=True)

    # content
    genres: Mapped[list[str] | None] = mapped_column(JsonB, nullable=True)
    short_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    transcript: Mapped[list[dict[str, Any]] | None] = mapped_column(JsonB, nullable=True)

    # object storage keys
    poster_s3_key: Mapped[str | None] = mapped_column(String(length=1024), nullable=True)
    video_s3_key: Mapped[str | None] = mapped_column(String(length=1024), nullable=True)
    audio_s3_key: Mapped[str | None] = mapped_column(String(length=1024), nullable=True)

    tasks: Mapped[list[TaskModel]] = relationship(
        back_populates="movie",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="TaskModel.created_at.desc()",
    )
    scenes: Mapped[list[SceneModel]] = relationship(
        back_populates="movie",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="SceneModel.position.asc()",
    )


class SceneModel(UUIDAuditBase):
    """Detected movie scene."""

    __tablename__ = "scenes"
    __table_args__ = (
        UniqueConstraint("movie_id", "position", name="uq_scenes_movie_id_position"),
        Index("ix_scenes_movie_id_status", "movie_id", "status"),
        Index("ix_scenes_movie_id_position", "movie_id", "position"),
    )

    # ownership
    movie_id: Mapped[UUID] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # workflow / ordering
    status: Mapped[str] = mapped_column(String(length=32), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    # time bounds
    start: Mapped[float] = mapped_column(Float, nullable=False)
    end: Mapped[float] = mapped_column(Float, nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=False)

    # structured payloads
    transcript: Mapped[dict[str, Any]] = mapped_column(JsonB, nullable=False)
    annotation: Mapped[dict[str, Any] | None] = mapped_column(JsonB, nullable=True)

    # object storage
    video_s3_key: Mapped[str | None] = mapped_column(String(length=1024), nullable=True)

    # embeddings
    transcript_embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMB_DIMENSIONS),
        nullable=True,
    )
    annotation_embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMB_DIMENSIONS),
        nullable=True,
    )

    movie: Mapped[MovieModel] = relationship(back_populates="scenes")
    frames: Mapped[list[FrameModel]] = relationship(
        back_populates="scene",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="FrameModel.position.asc()",
    )


class FrameModel(UUIDAuditBase):
    """Representative frame extracted from a scene."""

    __tablename__ = "frames"
    __table_args__ = (
        UniqueConstraint("scene_id", "position", name="uq_frames_scene_id_position"),
        Index("ix_frames_movie_id_scene_id", "movie_id", "scene_id"),
        Index("ix_frames_scene_id_position", "scene_id", "position"),
    )

    # ownership
    movie_id: Mapped[UUID] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scene_id: Mapped[UUID] = mapped_column(
        ForeignKey("scenes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ordering / ranking
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)

    # object storage
    image_s3_key: Mapped[str] = mapped_column(String(length=1024), nullable=False)

    # embeddings
    image_embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMB_DIMENSIONS),
        nullable=True,
    )

    scene: Mapped[SceneModel] = relationship(back_populates="frames")
