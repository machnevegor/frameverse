"""OpenRouter adapter for annotation and embeddings."""

from __future__ import annotations

import json
from typing import Any

from langfuse.openai import AsyncOpenAI as LangfuseAsyncOpenAI

from src.config import EMB_DIMENSIONS, OPENROUTER_BASE_URL, settings
from src.domain import SceneTranscript
from src.protocols.ann import ANNProtocol
from src.protocols.emb import EMBProtocol


class OpenRouterAdapter(ANNProtocol, EMBProtocol):
    """OpenRouter adapter implementing ANN and EMB protocols."""

    def __init__(self) -> None:
        self._client = LangfuseAsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=OPENROUTER_BASE_URL,
        )

    async def annotate(
        self,
        movie_info: dict[str, Any],
        keyframe_urls: list[str],
        scene_transcript: SceneTranscript,
        previous_annotations: list[str],
        *,
        trace_id: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> str:
        text_block = self._render_annotation_payload(movie_info, scene_transcript, previous_annotations)
        content: list[dict[str, Any]] = [{"type": "text", "text": text_block}]
        for keyframe_url in keyframe_urls:
            content.append({"type": "image_url", "image_url": {"url": keyframe_url}})

        response = await self._client.chat.completions.create(
            model=settings.ann_model,
            temperature=0.2,
            trace_id=trace_id,
            metadata=metadata or {},
            name="scene-annotation",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a scene annotation model for movie retrieval. "
                        "Generate a compact, factual and grounded scene summary in plain text. "
                        "Do not infer identities from faces. "
                        "Use only provided transcript/context and visible evidence."
                    ),
                },
                {
                    "role": "user",
                    "content": content,
                },
            ],
        )
        message = response.choices[0].message
        output = message.content or ""
        return output.strip()

    async def embed_texts(
        self,
        texts: list[str],
        *,
        trace_id: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> list[list[float]]:
        if not texts:
            return []
        response = await self._client.embeddings.create(
            model=settings.emb_model,
            dimensions=EMB_DIMENSIONS,
            input=texts,
            trace_id=trace_id,
            metadata=metadata or {},
            name="scene-text-embedding",
        )
        return [list(item.embedding) for item in response.data]

    async def embed_images(
        self,
        image_urls: list[str],
        *,
        trace_id: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> list[list[float]]:
        if not image_urls:
            return []
        input_payload = [{"type": "image_url", "image_url": {"url": url}} for url in image_urls]
        response = await self._client.embeddings.create(
            model=settings.emb_model,
            dimensions=EMB_DIMENSIONS,
            input=input_payload,
            trace_id=trace_id,
            metadata=metadata or {},
            name="scene-image-embedding",
        )
        return [list(item.embedding) for item in response.data]

    @staticmethod
    def _render_annotation_payload(
        movie_info: dict[str, Any],
        scene_transcript: SceneTranscript,
        previous_annotations: list[str],
    ) -> str:
        movie_info_payload = {
            key: value
            for key, value in movie_info.items()
            if value is not None and (not isinstance(value, str) or value.strip())
        }
        transcript_payload = scene_transcript.model_dump(mode="json")
        previous_payload = previous_annotations or []
        return "\n\n".join(
            [
                "movie_info:\n" + json.dumps(movie_info_payload, ensure_ascii=False),
                "scene_transcript:\n" + json.dumps(transcript_payload, ensure_ascii=False),
                "previous_scene_annotations:\n" + json.dumps(previous_payload, ensure_ascii=False),
            ],
        )
