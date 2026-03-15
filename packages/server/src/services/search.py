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
    SEARCH_ANNOTATION_CANDIDATES,
    SEARCH_IMAGE_CANDIDATES,
    SEARCH_IMAGE_THRESHOLD,
    SEARCH_LLM_MAX_IMAGES,
    SEARCH_LLM_MAX_SCENES,
    SEARCH_LLM_MAX_TOKENS,
    SEARCH_MAX_LLM_ITERATIONS,
    SEARCH_MAX_MOVIE_GROUPS,
    SEARCH_MAX_SCENES_PER_GROUP,
    SEARCH_RERANK_PROMPT_NAME,
    SEARCH_SCORE_THRESHOLD,
    SEARCH_TRANSCRIPT_CANDIDATES,
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

SEARCH_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_scenes",
            "description": "Semantic search across transcript, annotation, and image embeddings",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query used for both text and visual embedding channels",
                    },
                },
                "required": ["query"],
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


_CHANNEL_LABELS: dict[str, str] = {
    "transcript": "транскрипт",
    "annotation": "аннотация",
    "image": "изображение",
}


def _similarity(distance: float) -> float:
    return round(max(0.0, min(1.0, 1.0 - distance / 2.0)), 2)


def _format_repeat_note(repeat_items: list[tuple[int, list[str]]]) -> str:
    parts = [
        f"#{num} (источник: {', '.join(_CHANNEL_LABELS.get(ch, ch) for ch in channels)})"
        for num, channels in sorted(repeat_items, key=lambda x: x[0])
    ]
    return f"Повторно найдены уже известные сцены: {', '.join(parts)}."


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

        self._candidates: dict[int, CandidateScene] = {}
        self._scene_id_to_number: dict[UUID, int] = {}
        self._movie_registry: dict[UUID, MovieModel] = {}
        self._seen_movie_ids: set[UUID] = set()
        # global image counter — capped at SEARCH_LLM_MAX_IMAGES across all iterations
        self._images_sent: int = 0
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
                langfuse_prompt=prompt_obj if iteration == 1 else None,
                name="scene-search-rerank",
                temperature=0.3,
                max_tokens=SEARCH_LLM_MAX_TOKENS,
            )
            assistant_msg = response.choices[0].message
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
                    yield _sse(SearchEventType.SEARCHING, SearchingPayload(query=args["query"]))

                    tool_content = await self._execute_search(
                        query=args["query"],
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
        query: str,
        movie_id: UUID | None,
    ) -> list[dict[str, Any]]:
        """Embed query for both text and visual channels (parallel HTTP), then run 3-channel DB search."""
        (text_vecs,), (image_vecs,) = await asyncio.gather(
            self._openrouter.embed_texts([query]),
            self._openrouter.embed_visual_queries([query]),
        )

        # sequential DB queries — AsyncSession does not support concurrent operations
        transcript_hits = await self._scene_svc.search_by_transcript(
            text_vecs, movie_id=movie_id, limit=SEARCH_TRANSCRIPT_CANDIDATES
        )
        annotation_hits = await self._scene_svc.search_by_annotation(
            text_vecs, movie_id=movie_id, limit=SEARCH_ANNOTATION_CANDIDATES
        )
        image_hits = await self._scene_svc.search_by_image(image_vecs, movie_id=movie_id, limit=SEARCH_IMAGE_CANDIDATES)

        by_channel: dict[UUID, dict[str, float]] = {}
        for hit in transcript_hits:
            d = by_channel.setdefault(hit.scene_id, {})
            d["transcript"] = min(d.get("transcript", hit.distance), hit.distance)
        for hit in annotation_hits:
            d = by_channel.setdefault(hit.scene_id, {})
            d["annotation"] = min(d.get("annotation", hit.distance), hit.distance)
        for hit in image_hits:
            d = by_channel.setdefault(hit.scene_id, {})
            d["image"] = min(d.get("image", hit.distance), hit.distance)

        # (number, [channels matched this iteration]) for already-known scenes
        repeat_items: list[tuple[int, list[str]]] = [
            (self._scene_id_to_number[sid], list(by_channel[sid].keys()))
            for sid in by_channel
            if sid in self._scene_id_to_number
        ]

        new_scene_ids = [sid for sid in by_channel if sid not in self._scene_id_to_number]
        if new_scene_ids:
            await self._load_and_register(new_scene_ids, by_channel)

        # update channel distances for already-registered scenes (keep minimum per channel)
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
        return self._render_tool_result(new_numbers, repeat_items)

    async def _load_and_register(
        self,
        new_scene_ids: list[UUID],
        by_channel: dict[UUID, dict[str, float]],
    ) -> None:
        scene_id_strs = [str(sid) for sid in new_scene_ids]

        scenes_result = await self._session.execute(select(SceneModel).where(SceneModel.id.in_(scene_id_strs)))
        scenes_by_id: dict[UUID, SceneModel] = {sc.id: sc for sc in scenes_result.scalars().all()}

        movie_ids = {sc.movie_id for sc in scenes_by_id.values()}
        movies_result = await self._session.execute(
            select(MovieModel).where(MovieModel.id.in_([str(mid) for mid in movie_ids]))
        )
        movies_by_id: dict[UUID, MovieModel] = {}
        for m in movies_result.scalars().all():
            movies_by_id[m.id] = m
            self._movie_registry[m.id] = m

        frames_result = await self._session.execute(select(FrameModel).where(FrameModel.scene_id.in_(scene_id_strs)))
        best_frames: dict[UUID, FrameModel] = {}
        for fr in frames_result.scalars().all():
            existing = best_frames.get(fr.scene_id)
            if existing is None or fr.score > existing.score:
                best_frames[fr.scene_id] = fr

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

    @staticmethod
    def _max_similarity(c: CandidateScene) -> float:
        scores = [
            max(0.0, min(1.0, 1.0 - d / 2.0))
            for d in (c.transcript_distance, c.annotation_distance, c.image_distance)
            if d is not None
        ]
        return max(scores) if scores else 0.0

    def _render_tool_result(
        self, new_numbers: list[int], repeat_items: list[tuple[int, list[str]]]
    ) -> list[dict[str, Any]]:
        above = [n for n in new_numbers if self._max_similarity(self._candidates[n]) >= SEARCH_SCORE_THRESHOLD][
            :SEARCH_LLM_MAX_SCENES
        ]

        if not above:
            text = "Новых релевантных сцен не найдено. Попробуй другой запрос."
            if repeat_items:
                text += "\n" + _format_repeat_note(repeat_items)
            return [{"type": "text", "text": text}]

        content: list[dict[str, Any]] = []

        # --- block 1: new movies (shown only once across all iterations) ---
        new_movies: dict[str, Any] = {}
        for n in above:
            c = self._candidates[n]
            movie_id = c.scene.movie_id
            if movie_id in self._seen_movie_ids:
                continue
            movie = self._movie_registry.get(movie_id)
            if movie is None:
                continue
            new_movies[movie.title] = {
                k: v
                for k, v in {
                    "год": movie.year,
                    "слоган": movie.slogan,
                    "жанры": movie.genres,
                    "краткое_описание": movie.short_description,
                }.items()
                if v is not None
            }
            self._seen_movie_ids.add(movie_id)

        if new_movies:
            movies_yaml = yaml.dump(new_movies, allow_unicode=True, default_flow_style=False, sort_keys=False)
            content.append({"type": "text", "text": f"Найденные фильмы:\n\n{movies_yaml}"})

        # --- block 2: unified scenes list with per-channel sources ---
        scenes_data: dict[str, Any] = {}
        # scenes whose image qualifies for a screenshot (decided here, attached after YAML)
        image_queue: list[tuple[int, CandidateScene]] = []

        for n in above:
            c = self._candidates[n]

            sources: list[str] = []
            scores: dict[str, float] = {}
            if c.transcript_distance is not None:
                sources.append("транскрипт")
                scores["транскрипт"] = _similarity(c.transcript_distance)
            if c.annotation_distance is not None:
                sources.append("аннотация")
                scores["аннотация"] = _similarity(c.annotation_distance)
            if c.image_distance is not None:
                sources.append("изображение")
                scores["изображение"] = _similarity(c.image_distance)

            entry: dict[str, Any] = {
                "фильм": c.movie_title,
                "источник": ", ".join(sources),
            }
            if c.transcript_distance is not None:
                entry["транскрипт"] = _transcript_text(c.scene)
            if c.annotation_distance is not None:
                entry["аннотация"] = (c.scene.annotation or {}).get("text", "(нет)")
            entry["совпадение"] = scores

            img_score = _similarity(c.image_distance) if c.image_distance is not None else 0.0
            if img_score >= SEARCH_IMAGE_THRESHOLD and c.frame_url and self._images_sent < SEARCH_LLM_MAX_IMAGES:
                entry["скриншот"] = "прилагается"
                image_queue.append((n, c))
                self._images_sent += 1

            scenes_data[f"Сцена #{n}"] = entry

        scenes_yaml = yaml.dump(scenes_data, allow_unicode=True, default_flow_style=False, sort_keys=False)
        content.append({"type": "text", "text": f"Найдено {len(above)} сцен:\n\n{scenes_yaml}"})

        for n, c in image_queue:
            content.append({"type": "text", "text": f"Скриншот сцены #{n} (фильм «{c.movie_title}»):"})
            content.append({"type": "image_url", "image_url": {"url": c.frame_url, "detail": "low"}})

        # --- repeat scenes note ---
        if repeat_items:
            content.append({"type": "text", "text": _format_repeat_note(repeat_items)})

        return content

    async def _build_search_result(self, scene_numbers: list[int], summary: str) -> SearchResult:
        valid = [n for n in scene_numbers if n in self._candidates]

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
