"""SceneDetect adapter for SBD and SBE."""

from __future__ import annotations

import asyncio
from pathlib import Path

import cv2
import numpy as np
from scenedetect import ContentDetector, detect

from src.config import SBD_THRESHOLD
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

    async def extract_clips(
        self,
        source: str,
        split_times: list[float],
        output_dir: str,
    ) -> list[Path]:
        """Extract scene clips in batch and return them in scene order.

        Caller must ensure split_times is strictly ascending.
        Raises RuntimeError if ffmpeg exits with non-zero code or clip count mismatches.
        """
        if not split_times:
            return []
        if split_times[0] < 0:
            raise RuntimeError("split_times must be non-negative")
        if any(current <= previous for previous, current in zip(split_times, split_times[1:], strict=False)):
            raise RuntimeError("split_times must be strictly ascending")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        expected = len(split_times)
        batch_start = split_times[0]

        if len(split_times) == 1:
            # Single segment still needs re-encode so clips starting mid-movie
            # begin with a decodable intra frame.
            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-nostdin",
                "-loglevel",
                "error",
                "-y",
                "-ss",
                f"{batch_start:.6f}",
                "-i",
                source,
                "-map",
                "0:v:0",
                "-map",
                "0:a?",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "21",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                str(output_path / "part_000000.mp4"),
            ]
        else:
            relative_times = [split_time - batch_start for split_time in split_times[1:]]
            segment_times = ",".join(f"{t:.9f}" for t in relative_times)
            # Force keyframes exactly at split boundaries to guarantee every produced
            # clip starts with a decodable intra frame.
            force_keyframes = ",".join(f"{t:.9f}" for t in relative_times)
            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-nostdin",
                "-loglevel",
                "error",
                "-y",
                "-ss",
                f"{batch_start:.6f}",
                "-i",
                source,
                "-map",
                "0:v:0",
                "-map",
                "0:a?",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "21",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                "-force_key_frames",
                force_keyframes,
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
        _, stderr_bytes = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(stderr_bytes.decode("utf-8", "replace").strip() or "ffmpeg segment failed")

        clips = sorted(output_path.glob("part_*.mp4"))
        if len(clips) != expected:
            raise RuntimeError(f"ffmpeg produced {len(clips)} clips, expected {expected}")
        return clips

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
