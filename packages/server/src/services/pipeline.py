"""Pipeline orchestration service."""

from __future__ import annotations

import asyncio
import tempfile
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
    KEYFRAMES_MIN_GAP_SEC,
    KEYFRAMES_MIN_SCORE_PERCENTILE,
    KEYFRAMES_PER_SCENE,
    PRESIGNED_URL_TTL_SEC,
    SBE_CONCURRENCY,
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
from src.protocols.sbe import SBEProtocol
from src.protocols.storage import StorageProtocol
from src.services.frame import FrameService
from src.services.movie import MovieService
from src.services.scene import SceneService
from src.services.task import TaskService

logger = structlog.get_logger(__name__)


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

                split_times = [round(float(s.start), 6) for s in scenes]

                logger.info(
                    "materialize_scenes started",
                    scenes=len(scenes),
                    split_times=len(split_times),
                )

                transcript_source = movie.transcript or []
                prepared: dict[int, tuple[str, SceneTranscript, list[tuple[int, float, float, str]]]] = {}
                clip_paths = await self.sbe.extract_clips(str(source_path), split_times, str(clips_dir))

                semaphore = asyncio.Semaphore(SBE_CONCURRENCY)

                async def _process_clip(scene_idx: int, clip_path: Path) -> None:
                    scene = scenes[scene_idx]
                    scene_prefix = f"movies/{movie.id}/scenes/{scene.id}"
                    try:
                        await self.storage.delete_prefix(f"{scene_prefix}/")
                        scene_video_key = f"{scene_prefix}/video.mp4"
                        await self.storage.upload_file(scene_video_key, str(clip_path), "video/mp4")

                        keyframes = await self.sbe.extract_keyframes(
                            str(clip_path),
                            max_keyframes=KEYFRAMES_PER_SCENE,
                            min_gap_sec=KEYFRAMES_MIN_GAP_SEC,
                            min_score_percentile=KEYFRAMES_MIN_SCORE_PERCENTILE,
                        )

                        frame_rows: list[tuple[int, float, float, str]] = []
                        for position, kf in enumerate(keyframes):
                            frame_key = f"{scene_prefix}/frames/{position:06d}.jpg"
                            await self.storage.upload(frame_key, kf.image_data, "image/jpeg")
                            frame_rows.append((position, kf.timestamp, kf.score, frame_key))

                        scene_transcript = self._slice_transcript(
                            transcript_source,
                            scene_start=float(scene.start),
                            scene_end=float(scene.end),
                        )
                        prepared[scene_idx] = (scene_video_key, scene_transcript, frame_rows)
                    finally:
                        clip_path.unlink(missing_ok=True)

                async def _worker(scene_idx: int, clip_path: Path) -> None:
                    async with semaphore:
                        await _process_clip(scene_idx, clip_path)

                # Unwrap ExceptionGroup so Temporal sees the actual root cause
                try:
                    async with asyncio.TaskGroup() as tg:
                        for scene_idx, clip_path in enumerate(clip_paths):
                            tg.create_task(_worker(scene_idx, clip_path))
                except BaseExceptionGroup as eg:
                    first = eg.exceptions[0]
                    logger.error("materialize_scenes TaskGroup failed", exc_info=eg)
                    if isinstance(first, Exception):
                        raise first from None
                    raise

            missing = [i for i in range(len(scenes)) if i not in prepared]
            if missing:
                raise RuntimeError(f"Scenes not processed after extraction: indices {missing}")

            # SQLAlchemy AsyncSession requires strictly sequential DB writes
            for scene_idx, scene in enumerate(scenes):
                video_key, scene_transcript, frame_rows = prepared[scene_idx]
                await self.frame_service.delete_by_scene(scene.id)
                for position, timestamp, score, frame_key in frame_rows:
                    await self.frame_service.create(
                        movie_id=movie.id,
                        scene_id=scene.id,
                        position=position,
                        timestamp=timestamp,
                        score=score,
                        image_s3_key=frame_key,
                    )
                scene.video_s3_key = video_key
                scene.transcript = scene_transcript.model_dump(mode="json")
                await self.task_service.increment_progress(task_id, "scenes_extracted")
                await self.session.flush()

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
