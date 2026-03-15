"""Temporal activities."""

from __future__ import annotations

import asyncio
from uuid import UUID

import structlog
from temporalio import activity

from src.db.session import SessionLocal
from src.services.factory import build_pipeline_service
from src.services.scene import SceneService
from src.services.task import TaskService

logger = structlog.get_logger(__name__)


@activity.defn
async def update_status_activity(task_id: str, status: str) -> None:
    logger.info("activity.started", activity="update_status", task_id=task_id, status=status)
    try:
        async with SessionLocal() as session:
            task_service = TaskService(session)
            task = await task_service.get(UUID(task_id))
            if task is None:
                logger.warning("activity.skipped", activity="update_status", task_id=task_id, reason="task_not_found")
                return
            await task_service.update_status(task, status)
            await session.commit()
        logger.info("activity.finished", activity="update_status", task_id=task_id, status=status)
    except Exception as exc:
        logger.error(
            "activity.failed", activity="update_status", task_id=task_id, status=status, error=str(exc), exc_info=True
        )
        raise


@activity.defn
async def extract_audio_activity(task_id: str) -> str:
    logger.info("activity.started", activity="extract_audio", task_id=task_id)
    try:
        async with SessionLocal() as session:
            pipeline = build_pipeline_service(session)
            audio_s3_key = await pipeline.extract_audio(UUID(task_id))
            await session.commit()
        logger.info("activity.finished", activity="extract_audio", task_id=task_id, audio_s3_key=audio_s3_key)
        return audio_s3_key
    except Exception as exc:
        logger.error("activity.failed", activity="extract_audio", task_id=task_id, error=str(exc), exc_info=True)
        raise


@activity.defn
async def transcribe_activity(task_id: str) -> None:
    logger.info("activity.started", activity="transcribe", task_id=task_id)
    try:
        async with SessionLocal() as session:
            pipeline = build_pipeline_service(session)
            await pipeline.transcribe(UUID(task_id))
            await session.commit()
        logger.info("activity.finished", activity="transcribe", task_id=task_id)
    except Exception as exc:
        logger.error("activity.failed", activity="transcribe", task_id=task_id, error=str(exc), exc_info=True)
        raise


@activity.defn
async def detect_scenes_activity(task_id: str) -> list[str]:
    async def heartbeat_loop() -> None:
        while True:
            await asyncio.sleep(30)
            activity.heartbeat()

    task = asyncio.create_task(heartbeat_loop())
    try:
        logger.info("activity.started", activity="detect_scenes", task_id=task_id)
        async with SessionLocal() as session:
            pipeline = build_pipeline_service(session)
            scene_ids = await pipeline.detect_scenes(UUID(task_id))
            await session.commit()
            logger.info("activity.finished", activity="detect_scenes", task_id=task_id, scenes_detected=len(scene_ids))
            return [str(scene_id) for scene_id in scene_ids]
    except Exception as exc:
        logger.error("activity.failed", activity="detect_scenes", task_id=task_id, error=str(exc), exc_info=True)
        raise
    finally:
        task.cancel()


@activity.defn
async def materialize_scenes_activity(task_id: str, scene_ids: list[str]) -> None:
    async def heartbeat_loop() -> None:
        while True:
            await asyncio.sleep(30)
            activity.heartbeat()

    task = asyncio.create_task(heartbeat_loop())
    try:
        logger.info("activity.started", activity="materialize_scenes", task_id=task_id, scenes_total=len(scene_ids))
        async with SessionLocal() as session:
            pipeline = build_pipeline_service(session)
            await pipeline.materialize_scenes(
                UUID(task_id),
                [UUID(scene_id) for scene_id in scene_ids],
            )
            await session.commit()
        logger.info("activity.finished", activity="materialize_scenes", task_id=task_id, scenes_total=len(scene_ids))
    except Exception as exc:
        logger.error(
            "activity.failed",
            activity="materialize_scenes",
            task_id=task_id,
            scenes_total=len(scene_ids),
            error=str(exc),
            exc_info=True,
        )
        raise
    finally:
        task.cancel()


@activity.defn
async def annotate_scene_activity(task_id: str, scene_id: str) -> None:
    logger.info("activity.started", activity="annotate_scene", task_id=task_id, scene_id=scene_id)
    try:
        async with SessionLocal() as session:
            pipeline = build_pipeline_service(session)
            await pipeline.annotate_scene(UUID(task_id), UUID(scene_id))
            await session.commit()
        logger.info("activity.finished", activity="annotate_scene", task_id=task_id, scene_id=scene_id)
    except Exception as exc:
        logger.error(
            "activity.failed",
            activity="annotate_scene",
            task_id=task_id,
            scene_id=scene_id,
            error=str(exc),
            exc_info=True,
        )
        raise


@activity.defn
async def embed_scene_activity(task_id: str, scene_id: str) -> None:
    logger.info("activity.started", activity="embed_scene", task_id=task_id, scene_id=scene_id)
    try:
        async with SessionLocal() as session:
            pipeline = build_pipeline_service(session)
            await pipeline.embed_scene(UUID(task_id), UUID(scene_id))
            await session.commit()
        logger.info("activity.finished", activity="embed_scene", task_id=task_id, scene_id=scene_id)
    except Exception as exc:
        logger.error(
            "activity.failed", activity="embed_scene", task_id=task_id, scene_id=scene_id, error=str(exc), exc_info=True
        )
        raise


@activity.defn
async def mark_completed_activity(task_id: str) -> None:
    logger.info("activity.started", activity="mark_completed", task_id=task_id)
    try:
        async with SessionLocal() as session:
            pipeline = build_pipeline_service(session)
            await pipeline.mark_completed(UUID(task_id))
            await session.commit()
        logger.info("activity.finished", activity="mark_completed", task_id=task_id)
    except Exception as exc:
        logger.error("activity.failed", activity="mark_completed", task_id=task_id, error=str(exc), exc_info=True)
        raise


@activity.defn
async def mark_cancelled_activity(task_id: str) -> None:
    logger.info("activity.started", activity="mark_cancelled", task_id=task_id)
    try:
        async with SessionLocal() as session:
            task_service = TaskService(session)
            scene_service = SceneService(session)
            task = await task_service.get(UUID(task_id))
            if task is None:
                logger.warning("activity.skipped", activity="mark_cancelled", task_id=task_id, reason="task_not_found")
                return
            await task_service.update_status(task, "cancelled")
            await scene_service.cancel_non_terminal_for_movie(task.movie_id)
            await session.commit()
        logger.info("activity.finished", activity="mark_cancelled", task_id=task_id)
    except Exception as exc:
        logger.error("activity.failed", activity="mark_cancelled", task_id=task_id, error=str(exc), exc_info=True)
        raise


@activity.defn
async def mark_failed_activity(task_id: str, status: str, error_message: str) -> None:
    logger.info("activity.started", activity="mark_failed", task_id=task_id, status=status)
    try:
        async with SessionLocal() as session:
            task_service = TaskService(session)
            task = await task_service.get(UUID(task_id))
            if task is None:
                logger.warning(
                    "activity.skipped", activity="mark_failed", task_id=task_id, status=status, reason="task_not_found"
                )
                return
            await task_service.update_status(
                task,
                status,
                error_message=error_message,
                error_code="unknown",
            )
            await session.commit()
        logger.info("activity.finished", activity="mark_failed", task_id=task_id, status=status)
    except Exception as exc:
        logger.error(
            "activity.failed", activity="mark_failed", task_id=task_id, status=status, error=str(exc), exc_info=True
        )
        raise
