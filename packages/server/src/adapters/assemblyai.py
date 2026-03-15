"""AssemblyAI adapter implementation."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
from langfuse import get_client

from src.config import ASR_SILENCE_GAP_SEC, ASSEMBLYAI_BASE_URL, settings
from src.domain import TranscriptSegment
from src.protocols.asr import ASRProtocol, TranscriptResult

_POLL_REQUEST_TIMEOUT = httpx.Timeout(connect=15.0, read=30.0, write=10.0, pool=5.0)
_SUBMIT_TIMEOUT = httpx.Timeout(connect=15.0, read=60.0, write=30.0, pool=5.0)
_MAX_NETWORK_ERRORS = 10


class AssemblyAIAdapter(ASRProtocol):
    """ASR adapter for AssemblyAI transcript API."""

    def __init__(self, timeout_sec: float = 1800.0) -> None:
        self._timeout_sec = timeout_sec

    def _headers(self) -> dict[str, str]:
        return {"Authorization": settings.assemblyai_api_key}

    async def _submit(self, audio_url: str) -> str:
        payload = {
            "audio_url": audio_url,
            "speech_model": settings.asr_model,
            "language_detection": True,
            "speaker_labels": True,
        }
        async with httpx.AsyncClient(headers=self._headers(), timeout=_SUBMIT_TIMEOUT) as client:
            response = await client.post(f"{ASSEMBLYAI_BASE_URL}/transcript", json=payload)
            response.raise_for_status()
            return str(response.json()["id"])

    async def _poll_until_done(self, transcript_id: str) -> dict[str, Any]:
        delay_sec = 2.0
        elapsed = 0.0
        network_errors = 0
        url = f"{ASSEMBLYAI_BASE_URL}/transcript/{transcript_id}"

        while elapsed < self._timeout_sec:
            try:
                async with httpx.AsyncClient(headers=self._headers(), timeout=_POLL_REQUEST_TIMEOUT) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    payload = response.json()
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                network_errors += 1
                if network_errors >= _MAX_NETWORK_ERRORS:
                    raise RuntimeError(
                        f"AssemblyAI polling failed after {network_errors} consecutive network errors",
                    ) from exc
                await asyncio.sleep(delay_sec)
                elapsed += delay_sec
                delay_sec = min(delay_sec * 1.5, 15.0)
                continue

            network_errors = 0
            status = payload.get("status")
            if status == "completed":
                return payload
            if status == "error":
                raise RuntimeError(payload.get("error", "AssemblyAI transcription failed"))

            await asyncio.sleep(delay_sec)
            elapsed += delay_sec
            delay_sec = min(delay_sec * 1.5, 15.0)

        raise TimeoutError(f"AssemblyAI transcription timed out after {self._timeout_sec}s")

    async def transcribe(
        self,
        audio_url: str,
        *,
        trace_id: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> TranscriptResult:
        langfuse = get_client()
        if trace_id is None:
            return await self._transcribe_impl(audio_url)

        with langfuse.start_as_current_observation(
            as_type="span",
            name="assemblyai.transcribe",
            # Langfuse trace_context requires W3C hex format (32 chars, no dashes).
            trace_context={"trace_id": trace_id.replace("-", "")},
            input={"audio_url": audio_url},
            metadata=metadata or {},
        ) as span:
            result = await self._transcribe_impl(audio_url)
            span.update(
                output={
                    "language": result.language,
                    "duration": result.duration,
                    "segments_count": len(result.segments),
                },
            )
            return result

    async def _transcribe_impl(self, audio_url: str) -> TranscriptResult:
        transcript_id = await self._submit(audio_url)
        payload = await self._poll_until_done(transcript_id)
        return TranscriptResult(
            text=payload.get("text", ""),
            language=payload.get("language_code"),
            duration=(float(payload["audio_duration"]) if payload.get("audio_duration") is not None else None),
            segments=self._build_segments(payload.get("words", [])),
        )

    @staticmethod
    def _build_segments(words: list[dict]) -> list[TranscriptSegment]:
        """Group words into segments by speaker change or silence gap >= ASR_SILENCE_GAP_SEC.

        Segments are emitted only for speech regions — silent/music intervals
        between segments are left as natural gaps in the timeline.
        """
        if not words:
            return []

        segments: list[TranscriptSegment] = []
        current: list[dict] = [words[0]]

        for word in words[1:]:
            prev = current[-1]
            gap_sec = (word["start"] - prev["end"]) / 1000.0
            speaker_changed = word.get("speaker") != prev.get("speaker")

            if speaker_changed or gap_sec >= ASR_SILENCE_GAP_SEC:
                segments.append(
                    TranscriptSegment(
                        start=current[0]["start"] / 1000.0,
                        end=current[-1]["end"] / 1000.0,
                        text=" ".join(w["text"] for w in current),
                        speaker=current[0].get("speaker"),
                    )
                )
                current = [word]
            else:
                current.append(word)

        segments.append(
            TranscriptSegment(
                start=current[0]["start"] / 1000.0,
                end=current[-1]["end"] / 1000.0,
                text=" ".join(w["text"] for w in current),
                speaker=current[0].get("speaker"),
            )
        )
        return segments
