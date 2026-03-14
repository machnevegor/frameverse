"""Temporal workflows."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from src.config import ANN_CONCURRENCY, EMB_CONCURRENCY
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


async def run_with_concurrency(limit: int, coroutines: list[Awaitable[None]]) -> None:
    """Run awaitables with fixed maximum parallelism."""

    semaphore = asyncio.Semaphore(limit)

    async def run(coro: Awaitable[None]) -> None:
        async with semaphore:
            await coro

    await asyncio.gather(*(run(coro) for coro in coroutines))


@workflow.defn
class ProcessMovieWorkflow:
    """Main processing workflow for one movie task."""

    def __init__(self) -> None:
        self._cancelled = False

    @workflow.signal
    async def cancel_processing(self) -> None:
        self._cancelled = True

    @staticmethod
    def _map_error_status(stage: str) -> str:
        if stage == "asr":
            return "failed_asr"
        if stage == "sbd":
            return "failed_sbd"
        if stage == "sbe":
            return "failed_sbe"
        if stage == "ann":
            return "failed_ann"
        return "failed_emb"

    _retry_policy = RetryPolicy(
        initial_interval=timedelta(seconds=5),
        maximum_interval=timedelta(seconds=60),
    )

    async def _act(
        self,
        fn: object,
        *args: object,
        timeout: timedelta = timedelta(minutes=60),
    ) -> object:
        return await workflow.execute_activity(
            fn,
            args=args,
            start_to_close_timeout=timeout,
            retry_policy=self._retry_policy,
        )

    async def _cancel(self, task_id: str) -> None:
        await self._act(mark_cancelled_activity, task_id)

    @workflow.run
    async def run(self, task_id: str) -> None:
        stage = "asr"
        try:
            await self._act(update_status_activity, task_id, "asr")
            await self._act(extract_audio_activity, task_id, timeout=timedelta(hours=2))
            await self._act(transcribe_activity, task_id, timeout=timedelta(hours=2))
            if self._cancelled:
                await self._cancel(task_id)
                return

            stage = "sbd"
            await self._act(update_status_activity, task_id, "sbd")
            scene_ids = list(await self._act(detect_scenes_activity, task_id, timeout=timedelta(hours=1)))
            if self._cancelled:
                await self._cancel(task_id)
                return

            stage = "sbe"
            await self._act(update_status_activity, task_id, "sbe")
            await self._act(materialize_scenes_activity, task_id, scene_ids, timeout=timedelta(hours=2))
            if self._cancelled:
                await self._cancel(task_id)
                return

            stage = "ann"
            await self._act(update_status_activity, task_id, "ann")
            await run_with_concurrency(
                ANN_CONCURRENCY,
                [self._act(annotate_scene_activity, task_id, scene_id) for scene_id in scene_ids],
            )
            if self._cancelled:
                await self._cancel(task_id)
                return

            stage = "emb"
            await self._act(update_status_activity, task_id, "emb")
            await run_with_concurrency(
                EMB_CONCURRENCY,
                [self._act(embed_scene_activity, task_id, scene_id) for scene_id in scene_ids],
            )

            await self._act(mark_completed_activity, task_id)
            await self._act(update_status_activity, task_id, "completed")
        except Exception as exc:
            await self._act(mark_failed_activity, task_id, self._map_error_status(stage), str(exc))
            raise
