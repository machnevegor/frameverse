"""OpenRouter adapter for annotation and embeddings."""

from __future__ import annotations

from typing import Any

import yaml
from langfuse import get_client
from langfuse.openai import AsyncOpenAI as LangfuseAsyncOpenAI

from src.config import ANN_PROMPT_NAME, EMB_DIMENSIONS, OPENROUTER_BASE_URL, settings
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
        self._langfuse = get_client()

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
        prompt = self._langfuse.get_prompt(ANN_PROMPT_NAME)
        system_prompt = prompt.compile()
        if not isinstance(system_prompt, str) or not system_prompt.strip():
            raise ValueError(f"Langfuse prompt '{ANN_PROMPT_NAME}' must compile to non-empty text")

        user_content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": self._render_annotation_payload(movie_info, scene_transcript, previous_annotations),
            },
        ]
        user_content.extend({"type": "image_url", "image_url": {"url": url}} for url in keyframe_urls)

        response = await self._client.chat.completions.create(
            model=settings.ann_model,
            temperature=0.2,
            trace_id=trace_id,
            metadata=metadata or {},
            name="scene-annotation",
            langfuse_prompt=prompt,
            messages=[
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": user_content},
            ],
        )
        output = response.choices[0].message.content or ""
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
        response = await self._client.embeddings.create(
            model=settings.emb_model,
            dimensions=EMB_DIMENSIONS,
            input=[{"content": [{"type": "image_url", "image_url": {"url": url}}]} for url in image_urls],
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
        movie_block = {key: value for key, value in movie_info.items() if value is not None}

        previous_block = {
            f"{index} сцена до текущей": text
            for index, text in enumerate(reversed(previous_annotations or []), start=1)
        }

        return (
            "Информация о фильме:\n"
            f"{yaml.dump(movie_block, allow_unicode=True, default_flow_style=False, sort_keys=False)}\n"
            "\n\nТранскрипт:\n"
            f"{yaml.dump(scene_transcript.model_dump(mode='json'), allow_unicode=True, default_flow_style=False, sort_keys=False)}\n"
            "\n\nПредыдущие сцены:\n"
            f"{yaml.dump(previous_block, allow_unicode=True, default_flow_style=False, sort_keys=False)}"
        )
