"""Scene search service with ReAct LLM re-ranking."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import yaml
from litestar.response import ServerSentEventMessage
from litestar.types import SSEData
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.openrouter import OpenRouterAdapter
from src.adapters.s3 import S3Adapter
from src.api.controllers._mappers import to_frame, to_scene
from src.config import (
    PRESIGNED_URL_TTL_SEC,
    SEARCH_CANDIDATES_PER_CHANNEL,
    SEARCH_LLM_MAX_TOKENS,
    SEARCH_MAX_LLM_ITERATIONS,
    SEARCH_MAX_MOVIE_GROUPS,
    SEARCH_MAX_SCENES_PER_GROUP,
    SEARCH_RERANK_PROMPT_NAME,
    settings,
)
from src.db.models import FrameModel, MovieModel, SceneModel
from src.domain.search import (
    ConclusionPayload,
    ErrorPayload,
    ResultsFoundPayload,
    SearchEventType,
    SearchingPayload,
    SearchResult,
    SearchResultGroup,
    SearchResultScene,
    SearchStartedPayload,
    ThinkingPayload,
)
from src.services.scene import SceneService

# OpenAI function-calling tool definitions for the ReAct search agent
SEARCH_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_scenes",
            "description": "Semantic search across transcript, annotation, and image embeddings",
            "parameters": {
                "type": "object",
                "properties": {
                    "text_query": {
                        "type": "string",
                        "description": "Text query for transcript and annotation channels",
                    },
                    "visual_query": {
                        "type": "string",
                        "description": "Visual description for image embedding channel",
                    },
                },
                "required": ["text_query", "visual_query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_results",
            "description": "Submit final re-ranked scene numbers and summary",
            "parameters": {
                "type": "object",
                "properties": {
                    "scene_numbers": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Relevant scene numbers ordered by relevance (most relevant first)",
                    },
                    "summary": {
                        "type": "string",
                        "description": "Brief summary in Russian for the user",
                    },
                },
                "required": ["scene_numbers", "summary"],
            },
        },
    },
]


def _sse(event: SearchEventType, payload: Any) -> ServerSentEventMessage:
    return ServerSentEventMessage(data=payload.model_dump_json(), event=event.value)


def _transcript_text(scene: SceneModel) -> str:
    """Extract scene-segment text from raw transcript JSON."""
    raw = scene.transcript or {}
    segments = raw.get("scene_segments", [])
    if not segments:
        return "(нет)"
    parts = []
    for seg in segments:
        speaker = seg.get("speaker")
        text = seg.get("text", "")
        parts.append(f"[{speaker}] {text}" if speaker else text)
    return " ".join(parts)


@dataclass(slots=True)
class CandidateScene:
    number: int
    scene: SceneModel
    movie_title: str
    movie_year: int | None
    best_frame: FrameModel | None
    frame_url: str | None
    transcript_distance: float | None
    annotation_distance: float | None
    image_distance: float | None


class SearchService:
    """ReAct-based scene search with LLM re-ranking over per-channel vector search."""

    def __init__(
        self,
        session: AsyncSession,
        openrouter: OpenRouterAdapter,
        storage: S3Adapter,
    ) -> None:
        self._session = session
        self._openrouter = openrouter
        self._storage = storage
        self._scene_svc = SceneService(session)

        # incremental candidate registry — persists across all ReAct iterations
        self._candidates: dict[int, CandidateScene] = {}
        self._scene_id_to_number: dict[UUID, int] = {}
        self._next_number: int = 1

    async def search(self, query: str, movie_id: UUID | None = None) -> AsyncGenerator[SSEData, None]:
        yield _sse(SearchEventType.SEARCH_STARTED, SearchStartedPayload(query=query))

        prompt_obj, system_text = self._openrouter.get_prompt(SEARCH_RERANK_PROMPT_NAME)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_text},
            {"role": "user", "content": query},
        ]

        for iteration in range(1, SEARCH_MAX_LLM_ITERATIONS + 1):
            response = await self._openrouter.chat(
                model=settings.llm_model,
                messages=messages,
                tools=SEARCH_TOOLS,
                # pass langfuse_prompt only on the first call to link all turns to one prompt version
                langfuse_prompt=prompt_obj if iteration == 1 else None,
                name="scene-search-rerank",
                temperature=0.3,
                max_tokens=SEARCH_LLM_MAX_TOKENS,
            )
            assistant_msg = response.choices[0].message

            # preserve full assistant turn (content + tool_calls) in conversation history
            messages.append(assistant_msg.model_dump(exclude_unset=True, exclude_none=True))

            if assistant_msg.content:
                yield _sse(SearchEventType.THINKING, ThinkingPayload(message=assistant_msg.content))

            if not assistant_msg.tool_calls:
                yield _sse(SearchEventType.ERROR, ErrorPayload(message="LLM не вернула инструментальный вызов"))
                return

            finished = False
            for tool_call in assistant_msg.tool_calls:
                fn_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)

                if fn_name == "submit_results":
                    result = await self._build_search_result(
                        scene_numbers=args.get("scene_numbers", []),
                        summary=args.get("summary", ""),
                    )
                    yield _sse(SearchEventType.CONCLUSION, ConclusionPayload(result=result))
                    finished = True
                    break

                if fn_name == "search_scenes":
                    yield _sse(
                        SearchEventType.SEARCHING,
                        SearchingPayload(text_query=args["text_query"], visual_query=args["visual_query"]),
                    )

                    new_numbers, tool_content = await self._execute_search(
                        text_query=args["text_query"],
                        visual_query=args["visual_query"],
                        movie_id=movie_id,
                    )

                    yield _sse(SearchEventType.RESULTS_FOUND, ResultsFoundPayload(count=len(self._candidates)))

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": tool_content,
                        }
                    )

            if finished:
                return

        yield _sse(SearchEventType.ERROR, ErrorPayload(message="Достигнут лимит итераций поиска без результата"))

    async def _execute_search(
        self,
        text_query: str,
        visual_query: str,
        movie_id: UUID | None,
    ) -> tuple[list[int], list[dict[str, Any]]]:
        """Embed queries, run 3-channel search in parallel, register new candidates."""
        (text_vecs,), (image_vecs,) = await asyncio.gather(
            self._openrouter.embed_texts([text_query]),
            self._openrouter.embed_visual_queries([visual_query]),
        )

        transcript_hits, annotation_hits, image_hits = await asyncio.gather(
            self._scene_svc.search_by_transcript(text_vecs, movie_id=movie_id, limit=SEARCH_CANDIDATES_PER_CHANNEL),
            self._scene_svc.search_by_annotation(text_vecs, movie_id=movie_id, limit=SEARCH_CANDIDATES_PER_CHANNEL),
            self._scene_svc.search_by_image(image_vecs, movie_id=movie_id, limit=SEARCH_CANDIDATES_PER_CHANNEL),
        )

        # aggregate per-channel distances by scene_id; keep minimum per channel
        by_channel: dict[UUID, dict[str, float]] = {}
        for hit in transcript_hits:
            by_channel.setdefault(hit.scene_id, {})["transcript"] = hit.distance
        for hit in annotation_hits:
            d = by_channel.setdefault(hit.scene_id, {})
            d["annotation"] = min(d.get("annotation", hit.distance), hit.distance)
        for hit in image_hits:
            d = by_channel.setdefault(hit.scene_id, {})
            d["image"] = min(d.get("image", hit.distance), hit.distance)

        new_scene_ids = [sid for sid in by_channel if sid not in self._scene_id_to_number]

        if new_scene_ids:
            await self._load_and_register(new_scene_ids, by_channel)

        # update channel distances for already-registered scenes
        for scene_id, distances in by_channel.items():
            if scene_id not in self._scene_id_to_number:
                continue
            c = self._candidates[self._scene_id_to_number[scene_id]]
            for attr, key in [
                ("transcript_distance", "transcript"),
                ("annotation_distance", "annotation"),
                ("image_distance", "image"),
            ]:
                if key in distances:
                    current = getattr(c, attr)
                    if current is None or distances[key] < current:
                        setattr(c, attr, distances[key])

        new_numbers = [self._scene_id_to_number[sid] for sid in new_scene_ids if sid in self._scene_id_to_number]
        return new_numbers, self._render_tool_result(new_numbers)

    async def _load_and_register(
        self,
        new_scene_ids: list[UUID],
        by_channel: dict[UUID, dict[str, float]],
    ) -> None:
        """Load SceneModel, MovieModel and best FrameModel for new scene_ids; register candidates."""
        scene_id_strs = [str(sid) for sid in new_scene_ids]

        scenes_result = await self._session.execute(select(SceneModel).where(SceneModel.id.in_(scene_id_strs)))
        scenes_by_id: dict[UUID, SceneModel] = {sc.id: sc for sc in scenes_result.scalars().all()}

        movie_ids = {sc.movie_id for sc in scenes_by_id.values()}
        movies_result = await self._session.execute(
            select(MovieModel).where(MovieModel.id.in_([str(mid) for mid in movie_ids]))
        )
        movies_by_id: dict[UUID, MovieModel] = {m.id: m for m in movies_result.scalars().all()}

        frames_result = await self._session.execute(select(FrameModel).where(FrameModel.scene_id.in_(scene_id_strs)))
        best_frames: dict[UUID, FrameModel] = {}
        for fr in frames_result.scalars().all():
            existing = best_frames.get(fr.scene_id)
            if existing is None or fr.score > existing.score:
                best_frames[fr.scene_id] = fr

        # generate presigned URLs concurrently
        frame_url_tasks = {
            sid: self._storage.generate_presigned_get_url(fr.image_s3_key, expires_in=PRESIGNED_URL_TTL_SEC)
            for sid, fr in best_frames.items()
        }
        frame_urls: dict[UUID, str] = dict(
            zip(frame_url_tasks.keys(), await asyncio.gather(*frame_url_tasks.values()), strict=True)
        )

        for scene_id in new_scene_ids:
            sc = scenes_by_id.get(scene_id)
            if sc is None:
                continue
            movie = movies_by_id.get(sc.movie_id)
            distances = by_channel.get(scene_id, {})
            number = self._next_number
            self._next_number += 1
            self._scene_id_to_number[scene_id] = number
            self._candidates[number] = CandidateScene(
                number=number,
                scene=sc,
                movie_title=movie.title if movie else "Неизвестный фильм",
                movie_year=movie.year if movie else None,
                best_frame=best_frames.get(scene_id),
                frame_url=frame_urls.get(scene_id),
                transcript_distance=distances.get("transcript"),
                annotation_distance=distances.get("annotation"),
                image_distance=distances.get("image"),
            )

    def _render_tool_result(self, new_numbers: list[int]) -> list[dict[str, Any]]:
        """Render YAML scene descriptions + labeled frames for multimodal tool result."""
        content: list[dict[str, Any]] = []

        if not new_numbers:
            content.append({"type": "text", "text": "Новых сцен не найдено. Попробуй другой запрос."})
            return content

        scenes_data: dict[str, Any] = {}
        for num in new_numbers:
            c = self._candidates[num]
            movie_label = c.movie_title + (f" ({c.movie_year})" if c.movie_year else "")
            match_scores: dict[str, float] = {}
            # distance to cosine similarity: score = 1 - dist/2, clamped to [0, 1]
            for label, dist in [
                ("транскрипт", c.transcript_distance),
                ("аннотация", c.annotation_distance),
                ("изображение", c.image_distance),
            ]:
                if dist is not None:
                    match_scores[label] = round(max(0.0, min(1.0, 1.0 - dist / 2.0)), 2)
            scenes_data[f"Сцена #{num}"] = {
                "фильм": movie_label,
                "транскрипт": _transcript_text(c.scene),
                "аннотация": (c.scene.annotation or {}).get("text", "(нет)"),
                "совпадения": match_scores,
            }

        yaml_text = yaml.dump(scenes_data, allow_unicode=True, default_flow_style=False, sort_keys=False)
        content.append({"type": "text", "text": f"Найдено {len(new_numbers)} новых сцен:\n\n{yaml_text}"})

        # labeled frames for vision inspection — only new scenes to avoid re-sending known images
        for num in new_numbers:
            c = self._candidates[num]
            if c.frame_url:
                movie_label = c.movie_title + (f" ({c.movie_year})" if c.movie_year else "")
                content.append({"type": "text", "text": f"Кадр сцены #{num}, фильм «{movie_label}»"})
                content.append({"type": "image_url", "image_url": {"url": c.frame_url, "detail": "low"}})

        return content

    async def _build_search_result(self, scene_numbers: list[int], summary: str) -> SearchResult:
        """Map LLM-returned scene numbers to domain objects and group by movie."""
        valid = [n for n in scene_numbers if n in self._candidates]

        # load all frames for selected scenes (client needs all keyframes, not just best)
        selected_scene_ids = [self._candidates[n].scene.id for n in valid]
        all_frames: dict[UUID, list[FrameModel]] = {}
        if selected_scene_ids:
            frame_stmt = (
                select(FrameModel)
                .where(FrameModel.scene_id.in_([str(sid) for sid in selected_scene_ids]))
                .order_by(FrameModel.position.asc())
            )
            for fr in (await self._session.execute(frame_stmt)).scalars().all():
                all_frames.setdefault(fr.scene_id, []).append(fr)

        # group by movie_id, preserving LLM relevance order
        groups_map: dict[UUID, SearchResultGroup] = {}
        groups_order: list[UUID] = []

        for num in valid:
            c = self._candidates[num]
            movie_id: UUID = c.scene.movie_id

            if movie_id not in groups_map:
                if len(groups_map) >= SEARCH_MAX_MOVIE_GROUPS:
                    continue
                groups_map[movie_id] = SearchResultGroup(
                    movie_id=movie_id,
                    movie_title=c.movie_title,
                    scenes=[],
                )
                groups_order.append(movie_id)

            group = groups_map[movie_id]
            if len(group.scenes) >= SEARCH_MAX_SCENES_PER_GROUP:
                continue

            frames = [to_frame(fr) for fr in all_frames.get(c.scene.id, [])]
            group.scenes.append(SearchResultScene(scene=to_scene(c.scene), frames=frames))

        return SearchResult(
            groups=[groups_map[mid] for mid in groups_order],
            summary=summary,
        )
