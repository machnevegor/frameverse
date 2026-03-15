"""SceneDetect adapter for SBD and SBE."""

from __future__ import annotations

import asyncio
import signal
from collections.abc import AsyncGenerator
from pathlib import Path

import cv2
import numpy as np
from scenedetect import ContentDetector, detect

from src.config import SBD_THRESHOLD, SBE_POLL_INTERVAL_SEC
from src.protocols.sbd import DetectedScene, SBDProtocol
from src.protocols.sbe import KeyframeData, SBEProtocol


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

    def stream_clips(
        self,
        source: str,
        split_times: list[float],
        output_dir: str,
    ) -> AsyncGenerator[tuple[int, Path], None]:
        """Stream scene clips as they are produced by ffmpeg.

        Yields (scene_index, clip_path) pairs in order as each clip becomes
        available. split_times must be strictly ascending scene start times.
        Expected total yield count equals len(split_times).
        """
        return _stream_clips(source, split_times, output_dir)

    async def extract_keyframes(
        self,
        clip_path: str,
        max_keyframes: int,
        min_gap_sec: float,
        min_score_percentile: int,
    ) -> list[KeyframeData]:
        return await asyncio.to_thread(
            self._extract_keyframes_sync,
            clip_path,
            max_keyframes,
            min_gap_sec,
            min_score_percentile,
        )

    def _extract_keyframes_sync(
        self,
        clip_path: str,
        max_keyframes: int,
        min_gap_sec: float,
        min_score_percentile: int,
    ) -> list[KeyframeData]:
        capture = cv2.VideoCapture(clip_path)
        if not capture.isOpened():
            raise RuntimeError(f"Failed to open clip: {clip_path}")

        try:
            fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
            candidates: list[tuple[float, float, np.ndarray]] = []
            previous_gray: np.ndarray | None = None
            frame_index = 0

            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                if previous_gray is None:
                    motion = 0.0
                else:
                    diff = cv2.absdiff(gray, previous_gray)
                    motion = float(np.mean(diff)) / 255.0

                focus = float(cv2.Laplacian(gray, cv2.CV_64F).var())
                focus_norm = min(focus / 1000.0, 1.0)

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


async def _stream_clips(
    source: str,
    split_times: list[float],
    output_dir: str,
) -> AsyncGenerator[tuple[int, Path], None]:
    if not split_times:
        return

    if split_times[0] < 0:
        raise RuntimeError("split_times must be non-negative")
    if any(cur <= prev for prev, cur in zip(split_times, split_times[1:], strict=False)):
        raise RuntimeError("split_times must be strictly ascending")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    expected = len(split_times)

    # Re-encode so each segment starts with an I-frame (avoids black screen when
    # cutting at non-keyframe positions). -c copy would produce broken first frames.
    force_keyframes = ",".join(f"{t:.6f}" for t in split_times)
    video_encode = [
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-force_key_frames",
        force_keyframes,
    ]
    audio_encode = ["-c:a", "aac"]

    if len(split_times) == 1:
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-nostdin",
            "-loglevel",
            "error",
            "-progress",
            "pipe:1",
            "-y",
            "-i",
            source,
            "-map",
            "0",
            *video_encode,
            *audio_encode,
            str(output_path / "part_000000.mp4"),
        ]
    else:
        segment_times = ",".join(f"{t:.6f}" for t in split_times[1:])
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-nostdin",
            "-loglevel",
            "error",
            "-progress",
            "pipe:1",
            "-y",
            "-i",
            source,
            "-map",
            "0",
            *video_encode,
            *audio_encode,
            "-f",
            "segment",
            "-reset_timestamps",
            "1",
            "-segment_times",
            segment_times,
            str(output_path / "part_%06d.mp4"),
        ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stderr_task = asyncio.create_task(_read_all(proc.stderr))
    ffmpeg_done = asyncio.Event()

    async def _drain_stdout() -> None:
        assert proc.stdout is not None
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
        code = await proc.wait()
        stderr = await stderr_task
        if code != 0:
            raise RuntimeError(stderr.strip() or f"ffmpeg failed with code {code}")
        ffmpeg_done.set()

    drain_task = asyncio.create_task(_drain_stdout())

    try:
        yielded = 0
        while yielded < expected:
            # Propagate ffmpeg errors early without waiting for the next poll.
            if drain_task.done() and not ffmpeg_done.is_set():
                await drain_task  # re-raise the stored exception

            files = sorted(output_path.glob("part_*.mp4"))
            # While ffmpeg is still running the last file may be incomplete
            ready = files if ffmpeg_done.is_set() else files[:-1]

            while yielded < len(ready):
                yield yielded, ready[yielded]
                yielded += 1

            if yielded < expected:
                await asyncio.sleep(SBE_POLL_INTERVAL_SEC)

        await drain_task

    except (asyncio.CancelledError, Exception):
        if proc.returncode is None:
            proc.send_signal(signal.SIGTERM)
        drain_task.cancel()
        raise


async def _read_all(stream: asyncio.StreamReader | None) -> str:
    if stream is None:
        return ""
    chunks: list[str] = []
    while True:
        chunk = await stream.read(65536)
        if not chunk:
            break
        chunks.append(chunk.decode("utf-8", "replace"))
    return "".join(chunks)
