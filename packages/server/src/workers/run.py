"""Temporal worker runner."""

from __future__ import annotations

import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from src.config import settings
from src.workers.activities import (
    annotate_scene_activity,
    detect_scenes_activity,
    embed_scene_activity,
    extract_audio_activity,
    mark_cancelled_activity,
    mark_completed_activity,
    mark_failed_activity,
    materialize_scenes_activity,
    transcribe_activity,
    update_status_activity,
)
from src.workers.workflows import ProcessMovieWorkflow


async def main() -> None:
    """Run temporal worker indefinitely."""

    client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[ProcessMovieWorkflow],
        activities=[
            update_status_activity,
            extract_audio_activity,
            transcribe_activity,
            detect_scenes_activity,
            materialize_scenes_activity,
            annotate_scene_activity,
            embed_scene_activity,
            mark_completed_activity,
            mark_cancelled_activity,
            mark_failed_activity,
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
