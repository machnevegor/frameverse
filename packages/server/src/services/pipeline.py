"""Pipeline orchestration service."""

from __future__ import annotations

import asyncio
import tempfile
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import openai
import structlog
from langfuse import get_client
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.controllers._mappers import _api_url
from src.config import (
    ANN_PREVIOUS_SCENES_CONTEXT_NUM,
    ANN_TRANSCRIPT_SIDE_CONTEXT_SEC,
    KEYFRAMES_CONCURRENCY,
    KEYFRAMES_MIN_GAP_SEC,
    KEYFRAMES_MIN_SCORE_PERCENTILE,
    KEYFRAMES_PER_SCENE,
    PRESIGNED_URL_TTL_SEC,
    SBE_COPY_CONCURRENCY,
    SBE_KEYFRAME_ALIGNMENT_TOLERANCE_SEC,
    SBE_REENCODE_CONCURRENCY,
)
from src.db.models import MovieModel
from src.domain import (
    Progress,
    SceneAnnotation,
    SceneTranscript,
    TranscriptSegment,
)
from src.protocols.ann import ANNProtocol
from src.protocols.asr import ASRProtocol
from src.protocols.emb import EMBProtocol
from src.protocols.sbd import SBDProtocol
from src.protocols.sbe import ClipExtractionMode, SBEProtocol
from src.protocols.storage import StorageProtocol
from src.services.frame import FrameService
from src.services.movie import MovieService
from src.services.scene import SceneService
from src.services.task import TaskService

logger = structlog.get_logger(__name__)


@dataclass(slots=True, frozen=True)
class SceneMaterializationPlan:
    scene_id: UUID
    position: int
    start_time: float
    end_time: float
    clip_path: Path
    clip_mode: ClipExtractionMode
    scene_prefix: str


@dataclass(slots=True, frozen=True)
class SceneVideoUploadedEvent:
    scene_id: UUID
    video_key: str


@dataclass(slots=True, frozen=True)
class SceneArtifactsReadyEvent:
    scene_id: UUID
    transcript: dict
    frame_rows: list[tuple[int, float, float, str]]


class PipelineService:
    """Business logic for ASR/SBD/SBE/ANN/EMB stages."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        storage: StorageProtocol,
        asr: ASRProtocol,
        sbd: SBDProtocol,
        sbe: SBEProtocol,
        ann: ANNProtocol,
        emb: EMBProtocol,
    ) -> None:
        self.session = session
        self.storage = storage
        self.asr = asr
        self.sbd = sbd
        self.sbe = sbe
        self.ann = ann
        self.emb = emb
        self.task_service = TaskService(session)
        self.movie_service = MovieService(session)
        self.scene_service = SceneService(session)
        self.frame_service = FrameService(session)
        self.langfuse = get_client()

    async def extract_audio(self, task_id: UUID) -> str:
        task = await self._get_task(task_id)
        movie = await self._get_movie(task.movie_id)
        trace = task.langfuse_trace_id

        with self.langfuse.start_as_current_observation(
            as_type="span",
            name="pipeline.extract_audio",
            trace_context={"trace_id": trace},
            metadata={"task_id": str(task_id), "movie_id": str(movie.id), "stage": "asr"},
            input={"video_s3_key": movie.video_s3_key},
        ):
            with tempfile.TemporaryDirectory(prefix="frameverse-audio-") as tmp_dir:
                video_path = Path(tmp_dir) / "movie.mp4"
                audio_path = Path(tmp_dir) / "movie.m4a"
                video_path.write_bytes(await self.storage.download(movie.video_s3_key))

                process = await asyncio.create_subprocess_exec(
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(video_path),
                    "-vn",
                    "-acodec",
                    "aac",
                    str(audio_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                _, stderr = await process.communicate()
                if process.returncode != 0:
                    raise RuntimeError(stderr.decode("utf-8", "replace").strip() or "ffmpeg audio extraction failed")

                audio_s3_key = f"movies/{movie.id}/audio.m4a"
                await self.storage.upload_file(audio_s3_key, str(audio_path), "audio/mp4")
                movie.audio_s3_key = audio_s3_key
                await self.session.flush()
                return audio_s3_key

    async def transcribe(self, task_id: UUID) -> None:
        task = await self._get_task(task_id)
        movie = await self._get_movie(task.movie_id)
        if movie.audio_s3_key is None:
            raise LookupError("Movie audio not found")

        trace = task.langfuse_trace_id
        with self.langfuse.start_as_current_observation(
            as_type="span",
            name="pipeline.transcribe",
            trace_context={"trace_id": trace},
            metadata={"task_id": str(task_id), "movie_id": str(movie.id), "stage": "asr"},
            input={"audio_s3_key": movie.audio_s3_key},
        ):
            audio_url = await self.storage.generate_presigned_get_url(
                movie.audio_s3_key, expires_in=PRESIGNED_URL_TTL_SEC
            )
            result = await self.asr.transcribe(
                audio_url,
                trace_id=trace,
                metadata={"task_id": str(task_id), "movie_id": str(movie.id), "provider": "assemblyai"},
            )
            movie.duration = result.duration
            movie.transcript = [segment.model_dump(mode="json") for segment in result.segments]
            await self.session.flush()

    async def detect_scenes(self, task_id: UUID) -> list[UUID]:
        task = await self._get_task(task_id)
        movie = await self._get_movie(task.movie_id)
        trace = task.langfuse_trace_id

        if movie.duration is None:
            raise LookupError("Movie duration not set — transcription must complete first")

        with self.langfuse.start_as_current_observation(
            as_type="span",
            name="pipeline.detect_scenes",
            trace_context={"trace_id": trace},
            metadata={"task_id": str(task_id), "movie_id": str(movie.id), "stage": "sbd"},
            input={"video_s3_key": movie.video_s3_key},
        ):
            with tempfile.TemporaryDirectory(prefix="frameverse-sbd-") as tmp_dir:
                video_path = Path(tmp_dir) / "movie.mp4"
                video_path.write_bytes(await self.storage.download(movie.video_s3_key))
                detected = await self.sbd.detect_scenes(str(video_path))

            scene_ids: list[UUID] = []
            for i, scene in enumerate(detected):
                # end = start of the next scene; for the last scene use movie duration
                end = detected[i + 1].start_time if i + 1 < len(detected) else movie.duration
                created = await self.scene_service.create(
                    movie_id=movie.id,
                    position=scene.scene_index,
                    start=scene.start_time,
                    end=end,
                    duration=max(0.0, end - scene.start_time),
                    status="queued",
                    transcript=SceneTranscript().model_dump(mode="json"),
                    video_s3_key=None,
                )
                scene_ids.append(created.id)

            await self.task_service.set_progress(
                task_id,
                Progress(
                    scenes_detected=len(scene_ids),
                    scenes_extracted=0,
                    scenes_annotated=0,
                    scenes_embedded=0,
                ),
            )
            await self.session.flush()
            return scene_ids

    async def materialize_scenes(self, task_id: UUID, scene_ids: list[UUID]) -> None:
        task = await self._get_task(task_id)
        movie = await self._get_movie(task.movie_id)
        trace = task.langfuse_trace_id

        selected = set(scene_ids)
        all_scenes = await self.scene_service.list_by_movie(movie.id)
        scenes = sorted(
            (s for s in all_scenes if s.id in selected),
            key=lambda s: s.position,
        )
        if not scenes:
            return

        with self.langfuse.start_as_current_observation(
            as_type="span",
            name="pipeline.materialize_scenes",
            trace_context={"trace_id": trace},
            metadata={"task_id": str(task_id), "movie_id": str(movie.id), "stage": "sbe"},
            input={"scenes_total": len(scenes)},
        ):
            with tempfile.TemporaryDirectory(prefix="frameverse-sbe-") as tmp_dir:
                tmp_path = Path(tmp_dir)
                source_path = tmp_path / "movie.mp4"
                clips_dir = tmp_path / "clips"
                clips_dir.mkdir()
                source_path.write_bytes(await self.storage.download(movie.video_s3_key))
                keyframe_times = await self.sbe.list_keyframe_times(str(source_path))
                plans = self._build_scene_materialization_plans(movie.id, scenes, clips_dir, keyframe_times)
                copy_count = sum(1 for plan in plans if plan.clip_mode == "copy")
                reencode_count = len(plans) - copy_count

                logger.info(
                    "materialize_scenes started",
                    scenes=len(scenes),
                    source_keyframes=len(keyframe_times),
                    copy_scenes=copy_count,
                    reencode_scenes=reencode_count,
                )

                transcript_source = movie.transcript or []
                persist_queue: asyncio.Queue[SceneVideoUploadedEvent | SceneArtifactsReadyEvent] = asyncio.Queue()
                workers_done = asyncio.Event()
                copy_semaphore = asyncio.Semaphore(SBE_COPY_CONCURRENCY)
                reencode_semaphore = asyncio.Semaphore(SBE_REENCODE_CONCURRENCY)
                keyframes_semaphore = asyncio.Semaphore(KEYFRAMES_CONCURRENCY)

                async def _run_workers() -> None:
                    try:
                        async with asyncio.TaskGroup() as tg:
                            for plan in plans:
                                tg.create_task(
                                    self._materialize_scene(
                                        plan,
                                        source_path=source_path,
                                        transcript_source=transcript_source,
                                        persist_queue=persist_queue,
                                        copy_semaphore=copy_semaphore,
                                        reencode_semaphore=reencode_semaphore,
                                        keyframes_semaphore=keyframes_semaphore,
                                    )
                                )
                    finally:
                        workers_done.set()

                try:
                    async with asyncio.TaskGroup() as tg:
                        tg.create_task(
                            self._persist_materialization_events(
                                task_id=task_id,
                                movie_id=movie.id,
                                persist_queue=persist_queue,
                                workers_done=workers_done,
                            )
                        )
                        tg.create_task(_run_workers())
                except BaseExceptionGroup as eg:
                    first = eg.exceptions[0]
                    logger.error("materialize_scenes TaskGroup failed", exc_info=eg)
                    if isinstance(first, Exception):
                        raise first from None
                    raise

    async def annotate_scene(self, task_id: UUID, scene_id: UUID) -> None:
        task = await self._get_task(task_id)
        movie = await self._get_movie(task.movie_id)
        scene = await self._get_scene(scene_id)
        trace = task.langfuse_trace_id

        scene.status = "ann"
        await self.session.flush()

        frames = await self.frame_service.list_by_scene(scene.id)
        keyframe_urls = [
            await self.storage.generate_presigned_get_url(frame.image_s3_key, expires_in=PRESIGNED_URL_TTL_SEC)
            for frame in frames
        ]
        scene_transcript = SceneTranscript.model_validate(scene.transcript)
        previous_scenes = await self.scene_service.list_by_movie(movie.id)
        previous_annotations = [
            str(item.annotation["text"])
            for item in previous_scenes
            if item.position < scene.position and item.annotation and isinstance(item.annotation.get("text"), str)
        ][-ANN_PREVIOUS_SCENES_CONTEXT_NUM:]

        with self.langfuse.start_as_current_observation(
            as_type="span",
            name="pipeline.annotate_scene",
            trace_context={"trace_id": trace},
            metadata={"task_id": str(task_id), "movie_id": str(movie.id), "scene_id": str(scene.id), "stage": "ann"},
            input={"keyframes_count": len(keyframe_urls), "previous_count": len(previous_annotations)},
        ):
            try:
                annotation_text = await self.ann.annotate(
                    movie_info=self._movie_info(movie),
                    keyframe_urls=keyframe_urls,
                    scene_transcript=scene_transcript,
                    previous_annotations=previous_annotations,
                    trace_id=trace,
                    metadata={"task_id": str(task_id), "scene_id": str(scene.id)},
                )
            except openai.BadRequestError as exc:
                # content filter or moderation — skip annotation, do not fail the activity
                logger.warning("annotation skipped: content filter", scene_id=str(scene.id), error=str(exc))
                annotation_text = ""

        scene.annotation = SceneAnnotation(text=annotation_text).model_dump(mode="json")
        await self.task_service.increment_progress(task_id, "scenes_annotated")
        await self.session.flush()

    async def embed_scene(self, task_id: UUID, scene_id: UUID) -> None:
        task = await self._get_task(task_id)
        movie = await self._get_movie(task.movie_id)
        scene = await self._get_scene(scene_id)
        trace = task.langfuse_trace_id

        scene.status = "emb"
        await self.session.flush()

        frames = await self.frame_service.list_by_scene(scene.id)
        annotation_text = ""
        if scene.annotation and isinstance(scene.annotation.get("text"), str):
            annotation_text = scene.annotation["text"]
        transcript_obj = SceneTranscript.model_validate(scene.transcript)
        transcript_text = "\n".join(segment.text for segment in transcript_obj.scene_segments)
        frame_urls = [_api_url("frames", str(frame.id), "image") for frame in frames]
        logger.info("embed_scene started", scene_id=str(scene.id), frame_urls=frame_urls)

        with self.langfuse.start_as_current_observation(
            as_type="span",
            name="pipeline.embed_scene",
            trace_context={"trace_id": trace},
            metadata={"task_id": str(task_id), "movie_id": str(movie.id), "scene_id": str(scene.id), "stage": "emb"},
            input={"frames_count": len(frame_urls)},
        ):
            annotation_vectors_task = self.emb.embed_texts(
                [annotation_text] if annotation_text else [],
                trace_id=trace,
                metadata={"task_id": str(task_id), "scene_id": str(scene.id), "kind": "annotation"},
            )
            transcript_vectors_task = self.emb.embed_texts(
                [transcript_text] if transcript_text else [],
                trace_id=trace,
                metadata={"task_id": str(task_id), "scene_id": str(scene.id), "kind": "transcript"},
            )

            async def _safe_embed_images() -> list[list[float]]:
                try:
                    return await self.emb.embed_images(
                        frame_urls,
                        trace_id=trace,
                        metadata={"task_id": str(task_id), "scene_id": str(scene.id), "kind": "frames"},
                    )
                except Exception as exc:
                    # content filter or provider error — skip image embeddings, do not fail the activity
                    logger.warning("image embedding skipped", scene_id=str(scene.id), error=str(exc))
                    return []

            annotation_vectors, transcript_vectors, image_vectors = await asyncio.gather(
                annotation_vectors_task,
                transcript_vectors_task,
                _safe_embed_images(),
            )

        scene.annotation_embedding = annotation_vectors[0] if annotation_vectors else None
        scene.transcript_embedding = transcript_vectors[0] if transcript_vectors else None
        if image_vectors:
            for frame, vector in zip(frames, image_vectors, strict=True):
                frame.image_embedding = vector
        else:
            logger.warning("image embeddings skipped, frame embeddings will be null", scene_id=str(scene.id))

        await self.task_service.increment_progress(task_id, "scenes_embedded")
        await self.session.flush()

    async def mark_completed(self, task_id: UUID) -> None:
        task = await self._get_task(task_id)
        scenes = await self.scene_service.list_by_movie(task.movie_id)
        for scene in scenes:
            if scene.status == "emb":
                scene.status = "completed"
        await self.session.flush()

    async def mark_cancelled(self, movie_id: UUID) -> None:
        await self.scene_service.cancel_non_terminal_for_movie(movie_id)
        await self.session.flush()

    def _build_scene_materialization_plans(
        self,
        movie_id: UUID,
        scenes: list,
        clips_dir: Path,
        keyframe_times: list[float],
    ) -> list[SceneMaterializationPlan]:
        plans: list[SceneMaterializationPlan] = []
        for scene in scenes:
            mode: ClipExtractionMode = (
                "copy" if self._is_keyframe_aligned(float(scene.start), keyframe_times) else "reencode"
            )
            plans.append(
                SceneMaterializationPlan(
                    scene_id=scene.id,
                    position=int(scene.position),
                    start_time=float(scene.start),
                    end_time=float(scene.end),
                    clip_path=clips_dir / f"{int(scene.position):06d}.mp4",
                    clip_mode=mode,
                    scene_prefix=f"movies/{movie_id}/scenes/{scene.id}",
                )
            )
        return plans

    async def _materialize_scene(
        self,
        plan: SceneMaterializationPlan,
        *,
        source_path: Path,
        transcript_source: list[dict],
        persist_queue: asyncio.Queue[SceneVideoUploadedEvent | SceneArtifactsReadyEvent],
        copy_semaphore: asyncio.Semaphore,
        reencode_semaphore: asyncio.Semaphore,
        keyframes_semaphore: asyncio.Semaphore,
    ) -> None:
        clip_semaphore = copy_semaphore if plan.clip_mode == "copy" else reencode_semaphore
        scene_video_key = f"{plan.scene_prefix}/video.mp4"

        logger.info(
            "scene materialization started",
            scene_id=str(plan.scene_id),
            position=plan.position,
            mode=plan.clip_mode,
        )

        clip_path = plan.clip_path
        async with clip_semaphore:
            clip_path = await self.sbe.extract_clip(
                str(source_path),
                start_time=plan.start_time,
                end_time=plan.end_time,
                output_path=str(plan.clip_path),
                mode=plan.clip_mode,
            )

        try:
            await self.storage.delete_prefix(f"{plan.scene_prefix}/")
            await self.storage.upload_file(scene_video_key, str(clip_path), "video/mp4")
            await persist_queue.put(SceneVideoUploadedEvent(scene_id=plan.scene_id, video_key=scene_video_key))

            async with keyframes_semaphore:
                keyframes = await self.sbe.extract_keyframes(
                    str(clip_path),
                    max_keyframes=KEYFRAMES_PER_SCENE,
                    min_gap_sec=KEYFRAMES_MIN_GAP_SEC,
                    min_score_percentile=KEYFRAMES_MIN_SCORE_PERCENTILE,
                )

            frame_rows: list[tuple[int, float, float, str]] = []
            for position, keyframe in enumerate(keyframes):
                frame_key = f"{plan.scene_prefix}/frames/{position:06d}.jpg"
                await self.storage.upload(frame_key, keyframe.image_data, "image/jpeg")
                frame_rows.append((position, keyframe.timestamp, keyframe.score, frame_key))

            scene_transcript = self._slice_transcript(
                transcript_source,
                scene_start=plan.start_time,
                scene_end=plan.end_time,
            )
            await persist_queue.put(
                SceneArtifactsReadyEvent(
                    scene_id=plan.scene_id,
                    transcript=scene_transcript.model_dump(mode="json"),
                    frame_rows=frame_rows,
                )
            )
            logger.info(
                "scene materialization finished",
                scene_id=str(plan.scene_id),
                position=plan.position,
                mode=plan.clip_mode,
                keyframes=len(frame_rows),
            )
        finally:
            clip_path.unlink(missing_ok=True)

    async def _persist_materialization_events(
        self,
        *,
        task_id: UUID,
        movie_id: UUID,
        persist_queue: asyncio.Queue[SceneVideoUploadedEvent | SceneArtifactsReadyEvent],
        workers_done: asyncio.Event,
    ) -> None:
        while True:
            if workers_done.is_set() and persist_queue.empty():
                return

            try:
                event = await asyncio.wait_for(persist_queue.get(), timeout=0.5)
            except TimeoutError:
                continue

            try:
                if isinstance(event, SceneVideoUploadedEvent):
                    await self._persist_scene_video_upload(task_id, event)
                else:
                    await self._persist_scene_artifacts(movie_id, event)
            except Exception:
                await self.session.rollback()
                raise
            finally:
                persist_queue.task_done()

    async def _persist_scene_video_upload(self, task_id: UUID, event: SceneVideoUploadedEvent) -> None:
        scene = await self._get_scene(event.scene_id)
        scene.video_s3_key = event.video_key
        await self.task_service.increment_progress(task_id, "scenes_extracted")
        await self.session.commit()
        logger.info("scene video persisted", scene_id=str(event.scene_id), video_key=event.video_key)

    async def _persist_scene_artifacts(self, movie_id: UUID, event: SceneArtifactsReadyEvent) -> None:
        scene = await self._get_scene(event.scene_id)
        await self.frame_service.delete_by_scene(scene.id)
        for position, timestamp, score, frame_key in event.frame_rows:
            await self.frame_service.create(
                movie_id=movie_id,
                scene_id=scene.id,
                position=position,
                timestamp=timestamp,
                score=score,
                image_s3_key=frame_key,
            )
        scene.transcript = event.transcript
        await self.session.commit()
        logger.info("scene artifacts persisted", scene_id=str(event.scene_id), frames=len(event.frame_rows))

    async def _get_task(self, task_id: UUID):
        task = await self.task_service.get(task_id)
        if task is None:
            raise LookupError("Task not found")
        return task

    async def _get_movie(self, movie_id: UUID):
        movie = await self.movie_service.get(movie_id)
        if movie is None:
            raise LookupError("Movie not found")
        return movie

    async def _get_scene(self, scene_id: UUID):
        scene = await self.scene_service.get(scene_id)
        if scene is None:
            raise LookupError("Scene not found")
        return scene

    @staticmethod
    def _is_keyframe_aligned(scene_start: float, keyframe_times: list[float]) -> bool:
        if scene_start <= SBE_KEYFRAME_ALIGNMENT_TOLERANCE_SEC:
            return True
        if not keyframe_times:
            return False

        previous_index = bisect_right(keyframe_times, scene_start) - 1
        if previous_index < 0:
            return False
        return (scene_start - keyframe_times[previous_index]) <= SBE_KEYFRAME_ALIGNMENT_TOLERANCE_SEC

    @staticmethod
    def _movie_info(movie: MovieModel) -> dict[str, object]:
        return {
            "title": movie.title,
            "year": movie.year,
            "slogan": movie.slogan,
            "description": movie.description,
            "short_description": movie.short_description,
            "genres": movie.genres,
        }

    @staticmethod
    def _slice_transcript(
        transcript: list[dict],
        *,
        scene_start: float,
        scene_end: float,
    ) -> SceneTranscript:
        left: list[TranscriptSegment] = []
        core: list[TranscriptSegment] = []
        right: list[TranscriptSegment] = []

        left_bound = scene_start - ANN_TRANSCRIPT_SIDE_CONTEXT_SEC
        right_bound = scene_end + ANN_TRANSCRIPT_SIDE_CONTEXT_SEC
        for item in transcript:
            segment = TranscriptSegment.model_validate(item)
            if segment.end < scene_start and segment.end >= left_bound:
                left.append(segment)
                continue
            if segment.start <= scene_end and segment.end >= scene_start:
                core.append(segment)
                continue
            if segment.start > scene_end and segment.start <= right_bound:
                right.append(segment)

        return SceneTranscript(
            left_segments=left,
            scene_segments=core,
            right_segments=right,
        )
