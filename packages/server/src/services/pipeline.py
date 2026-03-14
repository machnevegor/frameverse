"""Pipeline orchestration service."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from uuid import UUID

from langfuse import get_client
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import (
    ANN_PREVIOUS_SCENES_CONTEXT_NUM,
    ANN_TRANSCRIPT_SIDE_CONTEXT_SEC,
    KEYFRAMES_MIN_GAP_SEC,
    KEYFRAMES_MIN_SCORE_PERCENTILE,
    KEYFRAMES_PER_SCENE,
    PRESIGNED_URL_TTL_SEC,
    SBE_CONCURRENCY,
)
from src.db.models import SceneModel
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

    async def extract_audio(self, task_id: UUID, *, trace_id: str | None = None) -> str:
        task = await self._get_task(task_id)
        movie = await self._get_movie(task.movie_id)
        trace = self._resolve_trace(task_id, trace_id)

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

    async def transcribe(self, task_id: UUID, *, trace_id: str | None = None) -> None:
        task = await self._get_task(task_id)
        movie = await self._get_movie(task.movie_id)
        if movie.audio_s3_key is None:
            raise LookupError("Movie audio not found")

        trace = self._resolve_trace(task_id, trace_id)
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

    async def detect_scenes(self, task_id: UUID, *, trace_id: str | None = None) -> list[UUID]:
        task = await self._get_task(task_id)
        movie = await self._get_movie(task.movie_id)
        trace = self._resolve_trace(task_id, trace_id)

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
            for scene in detected:
                created = await self.scene_service.create(
                    movie_id=movie.id,
                    position=scene.scene_index,
                    start=scene.start_time,
                    end=scene.end_time,
                    duration=max(0.0, scene.end_time - scene.start_time),
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

    async def materialize_scenes(self, task_id: UUID, scene_ids: list[UUID], *, trace_id: str | None = None) -> None:
        task = await self._get_task(task_id)
        movie = await self._get_movie(task.movie_id)
        trace = self._resolve_trace(task_id, trace_id)

        all_scenes = await self.scene_service.list_by_movie(movie.id)
        selected = {scene_id for scene_id in scene_ids}
        scenes = [scene for scene in all_scenes if scene.id in selected]
        scenes.sort(key=lambda item: item.position)
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
                clips_dir.mkdir(parents=True, exist_ok=True)
                source_path.write_bytes(await self.storage.download(movie.video_s3_key))

                split_times = [float(scene.start) for scene in scenes]
                if not split_times:
                    return
                if split_times[0] != 0.0:
                    split_times.insert(0, 0.0)
                clip_paths = await self.sbe.extract_clips(str(source_path), split_times, str(clips_dir))

                semaphore = asyncio.Semaphore(SBE_CONCURRENCY)
                transcript_source = movie.transcript or []

                async def _handle_scene(scene: SceneModel, clip_index: int) -> None:
                    async with semaphore:
                        clip_path = clip_paths.get(clip_index)
                        if clip_path is None:
                            raise RuntimeError(f"Missing clip for scene index {clip_index}")

                        scene_prefix = f"movies/{movie.id}/scenes/{scene.id}"
                        await self.storage.delete_prefix(f"{scene_prefix}/")
                        scene_video_key = f"{scene_prefix}/video.mp4"
                        await self.storage.upload_file(scene_video_key, clip_path, "video/mp4")

                        keyframes = await self.sbe.extract_keyframes(
                            clip_path,
                            max_keyframes=KEYFRAMES_PER_SCENE,
                            min_gap_sec=KEYFRAMES_MIN_GAP_SEC,
                            min_score_percentile=KEYFRAMES_MIN_SCORE_PERCENTILE,
                        )

                        await self.frame_service.delete_by_scene(scene.id)
                        for position, keyframe in enumerate(keyframes):
                            frame_key = f"{scene_prefix}/frames/{position:06d}.jpg"
                            await self.storage.upload(frame_key, keyframe.image_data, "image/jpeg")
                            await self.frame_service.create(
                                movie_id=movie.id,
                                scene_id=scene.id,
                                position=position,
                                timestamp=keyframe.timestamp,
                                score=keyframe.score,
                                image_s3_key=frame_key,
                            )

                        scene_transcript = self._slice_transcript(
                            transcript_source,
                            scene_start=float(scene.start),
                            scene_end=float(scene.end),
                        )
                        scene.video_s3_key = scene_video_key
                        scene.transcript = scene_transcript.model_dump(mode="json")
                        await self.task_service.increment_progress(task_id, "scenes_extracted")
                        await self.session.flush()

                # NOTE: preserve deterministic mapping of scenes to extracted clip index.
                await asyncio.gather(*(_handle_scene(scene, index) for index, scene in enumerate(scenes)))

    async def annotate_scene(self, task_id: UUID, scene_id: UUID, *, trace_id: str | None = None) -> None:
        task = await self._get_task(task_id)
        movie = await self._get_movie(task.movie_id)
        scene = await self._get_scene(scene_id)
        trace = self._resolve_trace(task_id, trace_id)

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
            annotation_text = await self.ann.annotate(
                movie_info=self._movie_info(movie),
                keyframe_urls=keyframe_urls,
                scene_transcript=scene_transcript,
                previous_annotations=previous_annotations,
                trace_id=trace,
                metadata={"task_id": str(task_id), "scene_id": str(scene.id)},
            )

        scene.annotation = SceneAnnotation(text=annotation_text).model_dump(mode="json")
        await self.task_service.increment_progress(task_id, "scenes_annotated")
        await self.session.flush()

    async def embed_scene(self, task_id: UUID, scene_id: UUID, *, trace_id: str | None = None) -> None:
        task = await self._get_task(task_id)
        movie = await self._get_movie(task.movie_id)
        scene = await self._get_scene(scene_id)
        trace = self._resolve_trace(task_id, trace_id)

        scene.status = "emb"
        await self.session.flush()

        frames = await self.frame_service.list_by_scene(scene.id)
        annotation_text = ""
        if scene.annotation and isinstance(scene.annotation.get("text"), str):
            annotation_text = scene.annotation["text"]
        transcript_obj = SceneTranscript.model_validate(scene.transcript)
        transcript_text = "\n".join(segment.text for segment in transcript_obj.scene_segments)
        frame_urls = [
            await self.storage.generate_presigned_get_url(frame.image_s3_key, expires_in=PRESIGNED_URL_TTL_SEC)
            for frame in frames
        ]

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
            image_vectors_task = self.emb.embed_images(
                frame_urls,
                trace_id=trace,
                metadata={"task_id": str(task_id), "scene_id": str(scene.id), "kind": "frames"},
            )
            annotation_vectors, transcript_vectors, image_vectors = await asyncio.gather(
                annotation_vectors_task,
                transcript_vectors_task,
                image_vectors_task,
            )

        scene.annotation_embedding = annotation_vectors[0] if annotation_vectors else None
        scene.transcript_embedding = transcript_vectors[0] if transcript_vectors else None
        for frame, vector in zip(frames, image_vectors, strict=True):
            frame.image_embedding = vector

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
    def _resolve_trace(task_id: UUID, trace_id: str | None) -> str:
        # Langfuse trace_context requires W3C hex format (32 chars, no dashes).
        raw = trace_id or str(task_id)
        return raw.replace("-", "")

    @staticmethod
    def _movie_info(movie: object) -> dict[str, object]:
        return {
            "title": getattr(movie, "title", None),
            "year": getattr(movie, "year", None),
            "slogan": getattr(movie, "slogan", None),
            "description": getattr(movie, "description", None),
            "short_description": getattr(movie, "short_description", None),
            "genres": getattr(movie, "genres", None),
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
