"""Temporal activities."""

from __future__ import annotations

import asyncio
from uuid import UUID

from temporalio import activity

from src.db.session import SessionLocal
from src.services.factory import build_pipeline_service
from src.services.scene import SceneService
from src.services.task import TaskService


@activity.defn
async def update_status_activity(task_id: str, status: str) -> None:
    async with SessionLocal() as session:
        task_service = TaskService(session)
        task = await task_service.get(UUID(task_id))
        if task is None:
            return
        await task_service.update_status(task, status)
        await session.commit()


@activity.defn
async def extract_audio_activity(task_id: str) -> str:
    async with SessionLocal() as session:
        pipeline = build_pipeline_service(session)
        audio_s3_key = await pipeline.extract_audio(UUID(task_id))
        await session.commit()
        return audio_s3_key


@activity.defn
async def transcribe_activity(task_id: str) -> None:
    async with SessionLocal() as session:
        pipeline = build_pipeline_service(session)
        await pipeline.transcribe(UUID(task_id))
        await session.commit()


@activity.defn
async def detect_scenes_activity(task_id: str) -> list[str]:
    async def heartbeat_loop() -> None:
        while True:
            await asyncio.sleep(30)
            activity.heartbeat()

    task = asyncio.create_task(heartbeat_loop())
    try:
        async with SessionLocal() as session:
            pipeline = build_pipeline_service(session)
            scene_ids = await pipeline.detect_scenes(UUID(task_id))
            await session.commit()
            return [str(scene_id) for scene_id in scene_ids]
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
        async with SessionLocal() as session:
            pipeline = build_pipeline_service(session)
            await pipeline.materialize_scenes(
                UUID(task_id),
                [UUID(scene_id) for scene_id in scene_ids],
            )
            await session.commit()
    finally:
        task.cancel()


@activity.defn
async def annotate_scene_activity(task_id: str, scene_id: str) -> None:
    async with SessionLocal() as session:
        pipeline = build_pipeline_service(session)
        await pipeline.annotate_scene(UUID(task_id), UUID(scene_id))
        await session.commit()


@activity.defn
async def embed_scene_activity(task_id: str, scene_id: str) -> None:
    async with SessionLocal() as session:
        pipeline = build_pipeline_service(session)
        await pipeline.embed_scene(UUID(task_id), UUID(scene_id))
        await session.commit()


@activity.defn
async def mark_completed_activity(task_id: str) -> None:
    async with SessionLocal() as session:
        pipeline = build_pipeline_service(session)
        await pipeline.mark_completed(UUID(task_id))
        await session.commit()


@activity.defn
async def mark_cancelled_activity(task_id: str) -> None:
    async with SessionLocal() as session:
        task_service = TaskService(session)
        scene_service = SceneService(session)
        task = await task_service.get(UUID(task_id))
        if task is None:
            return
        await task_service.update_status(task, "cancelled")
        await scene_service.cancel_non_terminal_for_movie(task.movie_id)
        await session.commit()


@activity.defn
async def mark_failed_activity(task_id: str, status: str, error_message: str) -> None:
    async with SessionLocal() as session:
        task_service = TaskService(session)
        task = await task_service.get(UUID(task_id))
        if task is None:
            return
        await task_service.update_status(
            task,
            status,
            error_message=error_message,
            error_code="unknown",
        )
        await session.commit()
