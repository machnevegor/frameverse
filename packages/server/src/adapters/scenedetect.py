"""SceneDetect adapter for SBD and SBE."""

from __future__ import annotations

import asyncio
import time
from contextlib import suppress
from pathlib import Path

import cv2
import numpy as np
import structlog
from scenedetect import ContentDetector, detect

from src.config import KEYFRAMES_EXTRACTION_TIMEOUT_SEC, KEYFRAMES_FRAME_SAMPLE_STEP, SBD_THRESHOLD
from src.protocols.sbd import DetectedScene, SBDProtocol
from src.protocols.sbe import KeyframeData, SBEProtocol, SceneClipMode

logger = structlog.get_logger(__name__)


class SceneDetectAdapter(SBDProtocol, SBEProtocol):
    """Adapter implementing scene boundary detection and keyframe extraction."""

    async def detect_scenes(self, video_path: str) -> list[DetectedScene]:
        return await asyncio.to_thread(self._detect_sync, video_path)

    def _detect_sync(self, video_path: str) -> list[DetectedScene]:
        detected = detect(video_path=video_path, detector=ContentDetector(threshold=SBD_THRESHOLD))
        return [
            DetectedScene(scene_index=idx, start_time=float(start_tc.get_seconds()))
            for idx, (start_tc, _) in enumerate(detected)
        ]

    async def list_video_keyframe_times(self, video_path: str) -> list[float]:
        started_at = time.perf_counter()
        logger.info("sbe.keyframe_scan.started", video_path=video_path)
        proc = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-skip_frame",
            "nokey",
            "-show_entries",
            "frame=best_effort_timestamp_time",
            "-of",
            "csv=p=0",
            video_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            error = stderr.decode("utf-8", "replace").strip() or "ffprobe keyframe scan failed"
            logger.error("sbe.keyframe_scan.failed", video_path=video_path, error=error)
            raise RuntimeError(error)

        values: list[float] = []
        for line in stdout.decode("utf-8", "replace").splitlines():
            value = line.strip().split(",")[0]
            if not value:
                continue
            values.append(float(value))

        if not values:
            logger.warning(
                "sbe.keyframe_scan.empty",
                video_path=video_path,
                elapsed_ms=round((time.perf_counter() - started_at) * 1000),
            )
            return []

        unique_sorted = sorted({round(value, 6) for value in values})
        logger.info(
            "sbe.keyframe_scan.finished",
            video_path=video_path,
            keyframes=len(unique_sorted),
            elapsed_ms=round((time.perf_counter() - started_at) * 1000),
        )
        return unique_sorted

    async def extract_scene_clip(
        self,
        video_path: str,
        *,
        start_sec: float,
        end_sec: float,
        clip_path: str,
        mode: SceneClipMode,
        nearest_keyframe_sec: float | None = None,
    ) -> Path:
        source = Path(video_path)
        if not source.exists():
            raise RuntimeError(f"video_path does not exist: {video_path}")
        if start_sec < 0:
            raise RuntimeError("start_sec must be non-negative")
        if end_sec <= start_sec:
            raise RuntimeError("end_sec must be greater than start_sec")

        output = Path(clip_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        duration = end_sec - start_sec
        started_at = time.perf_counter()

        if mode == "copy":
            # Input seeking is fast and sufficient for copy: we only use copy when
            # start_sec is already on a keyframe boundary (verified by _is_keyframe_aligned),
            # so the clip starts at the correct I-frame with no black-screen risk.
            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-nostdin",
                "-loglevel",
                "error",
                "-y",
                "-ss",
                f"{start_sec:.6f}",
                "-i",
                video_path,
                "-t",
                f"{duration:.6f}",
                "-map",
                "0",
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(output),
            ]
        else:
            # For re-encode we need frame-accurate positioning.  The trick is to
            # combine a fast input seek to the nearest preceding keyframe with a
            # short output seek that advances the decoder to the exact start_sec.
            # This avoids decoding from the very beginning of the file (slow for
            # long movies) while still producing a clip whose first frame is
            # exactly at start_sec.
            if nearest_keyframe_sec is not None and nearest_keyframe_sec <= start_sec:
                input_seek = nearest_keyframe_sec
                output_seek = start_sec - nearest_keyframe_sec
            else:
                # Fallback: output-only seek — accurate but slower for large files.
                input_seek = start_sec
                output_seek = 0.0
            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-nostdin",
                "-loglevel",
                "error",
                "-y",
                "-ss",
                f"{input_seek:.6f}",
                "-i",
                video_path,
                "-ss",
                f"{output_seek:.6f}",
                "-t",
                f"{duration:.6f}",
                "-map",
                "0",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-crf",
                "23",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                str(output),
            ]

        logger.info(
            "sbe.clip_extract.started",
            video_path=video_path,
            clip_path=str(output),
            mode=mode,
            start_sec=round(start_sec, 3),
            end_sec=round(end_sec, 3),
            duration_sec=round(duration, 3),
        )

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _, stderr = await proc.communicate()
        except asyncio.CancelledError:
            if proc.returncode is None:
                proc.terminate()
                with suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(proc.wait(), timeout=2.0)
                if proc.returncode is None:
                    proc.kill()
                    with suppress(asyncio.TimeoutError):
                        await asyncio.wait_for(proc.wait(), timeout=2.0)
            logger.warning(
                "sbe.clip_extract.cancelled",
                clip_path=str(output),
                mode=mode,
                elapsed_ms=round((time.perf_counter() - started_at) * 1000),
            )
            raise

        if proc.returncode != 0:
            error = stderr.decode("utf-8", "replace").strip() or "ffmpeg clip extraction failed"
            logger.error(
                "sbe.clip_extract.failed",
                clip_path=str(output),
                mode=mode,
                error=error,
                elapsed_ms=round((time.perf_counter() - started_at) * 1000),
            )
            raise RuntimeError(error)
        if not output.exists():
            raise RuntimeError(f"ffmpeg clip not found after extraction: {output}")
        if output.stat().st_size <= 0:
            raise RuntimeError(f"ffmpeg produced empty clip: {output}")

        logger.info(
            "sbe.clip_extract.finished",
            clip_path=str(output),
            mode=mode,
            elapsed_ms=round((time.perf_counter() - started_at) * 1000),
        )
        return output

    async def extract_clip_keyframes(
        self,
        clip_path: str,
        max_keyframes: int,
        min_gap_sec: float,
        min_score_percentile: int,
    ) -> list[KeyframeData]:
        started_at = time.perf_counter()
        logger.info(
            "sbe.keyframe_extract.started",
            clip_path=clip_path,
            max_keyframes=max_keyframes,
            min_gap_sec=min_gap_sec,
            min_score_percentile=min_score_percentile,
        )
        result = await asyncio.to_thread(
            self._extract_keyframes_sync,
            clip_path,
            max_keyframes,
            min_gap_sec,
            min_score_percentile,
            KEYFRAMES_EXTRACTION_TIMEOUT_SEC,
            KEYFRAMES_FRAME_SAMPLE_STEP,
        )
        logger.info(
            "sbe.keyframe_extract.finished",
            clip_path=clip_path,
            extracted_keyframes=len(result),
            elapsed_ms=round((time.perf_counter() - started_at) * 1000),
        )
        return result

    def _extract_keyframes_sync(
        self,
        clip_path: str,
        max_keyframes: int,
        min_gap_sec: float,
        min_score_percentile: int,
        max_processing_sec: float,
        frame_sample_step: int,
    ) -> list[KeyframeData]:
        capture = cv2.VideoCapture(clip_path)
        if not capture.isOpened():
            raise RuntimeError(f"Failed to open clip: {clip_path}")

        try:
            fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
            candidates: list[tuple[float, float, np.ndarray]] = []
            previous_gray: np.ndarray | None = None
            frame_index = 0
            sample_step = max(1, int(frame_sample_step))
            deadline = time.perf_counter() + max(0.0, float(max_processing_sec))
            timed_out = False
            center_weight: float | None = None

            while True:
                if time.perf_counter() >= deadline:
                    timed_out = True
                    break
                ok, frame = capture.read()
                if not ok:
                    break
                if frame_index % sample_step != 0:
                    frame_index += 1
                    continue
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                if previous_gray is None:
                    motion = 0.0
                else:
                    diff = cv2.absdiff(gray, previous_gray)
                    motion = float(np.mean(diff)) / 255.0

                focus = float(cv2.Laplacian(gray, cv2.CV_64F).var())
                focus_norm = min(focus / 1000.0, 1.0)

                if center_weight is None:
                    h, w = gray.shape
                    center_x = w / 2.0
                    center_y = h / 2.0
                    y_indices, x_indices = np.indices(gray.shape)
                    distance = np.sqrt((x_indices - center_x) ** 2 + (y_indices - center_y) ** 2)
                    distance /= max(distance.max(), 1.0)
                    center_weight = float(np.mean(1.0 - distance))

                score = 0.55 * motion + 0.30 * focus_norm + 0.15 * center_weight
                timestamp = frame_index / fps
                candidates.append((timestamp, score, frame.copy()))
                previous_gray = gray
                frame_index += 1

            if timed_out:
                logger.warning(
                    "sbe.keyframe_extract.timeout_reached",
                    clip_path=clip_path,
                    timeout_sec=max_processing_sec,
                    sampled_candidates=len(candidates),
                )

            if not candidates:
                return []

            scores = np.array([c[1] for c in candidates], dtype=np.float32)
            threshold = float(np.percentile(scores, min_score_percentile))

            selected: list[tuple[float, float, np.ndarray]] = []
            last_timestamp = -999999.0
            for timestamp, score, frame in sorted(candidates, key=lambda item: item[1], reverse=True):
                if score < threshold:
                    continue
                if timestamp - last_timestamp < min_gap_sec:
                    continue
                selected.append((timestamp, score, frame))
                last_timestamp = timestamp
                if len(selected) >= max_keyframes:
                    break

            if not selected:
                selected = sorted(candidates, key=lambda item: item[1], reverse=True)[:max_keyframes]

            selected.sort(key=lambda item: item[0])
            results: list[KeyframeData] = []
            for timestamp, score, frame in selected:
                ok, encoded = cv2.imencode(".jpg", frame)
                if not ok:
                    continue
                results.append(
                    KeyframeData(
                        timestamp=float(timestamp),
                        score=max(0.0, min(1.0, float(score))),
                        image_data=encoded.tobytes(),
                    ),
                )
            return results
        finally:
            capture.release()
