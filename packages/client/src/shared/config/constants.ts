import type { MovieStatus, SceneStatus, SearchEvent } from "../api/types";

export const API_BASE =
  typeof window === "undefined" ? "https://frameverse.ru/api/v0" : "/api/v0";

export const SCENES_PER_PAGE = 20;

export const MOVIE_STATUS_LABEL: Record<MovieStatus, string> = {
  queued: "В очереди",
  asr: "Распознаём речь",
  sbd: "Находим сцены",
  sbe: "Нарезаем фрагменты",
  ann: "Готовим описания сцен",
  emb: "Подключаем умный поиск",
  completed: "Готово",
  cancelled: "Отменено",
  failed_asr: "Ошибка распознавания речи",
  failed_sbd: "Ошибка обнаружения сцен",
  failed_sbe: "Ошибка нарезания фрагментов",
  failed_ann: "Ошибка подготовки описаний сцен",
  failed_emb: "Ошибка подключения умного поиска",
};

export const MOVIE_STATUS_VARIANT: Record<
  MovieStatus,
  "default" | "secondary" | "destructive" | "outline"
> = {
  queued: "secondary",
  asr: "default",
  sbd: "default",
  sbe: "default",
  ann: "default",
  emb: "default",
  completed: "default",
  cancelled: "outline",
  failed_asr: "destructive",
  failed_sbd: "destructive",
  failed_sbe: "destructive",
  failed_ann: "destructive",
  failed_emb: "destructive",
};

export const SCENE_STATUS_LABEL: Record<SceneStatus, string> = {
  queued: "В очереди",
  ann: "Готовим описания сцены",
  emb: "Подключаем умный поиск",
  completed: "Готово",
  cancelled: "Отменено",
  failed_ann: "Ошибка подготовки описания сцены",
  failed_emb: "Ошибка подключения умного поиска",
};

export const SCENE_STATUS_VARIANT: Record<
  SceneStatus,
  "default" | "secondary" | "destructive" | "outline"
> = {
  queued: "secondary",
  ann: "default",
  emb: "default",
  completed: "default",
  cancelled: "outline",
  failed_ann: "destructive",
  failed_emb: "destructive",
};

export const PIPELINE_STAGE_LABELS = [
  { key: "scenes_detected", label: "Находим сцены" },
  { key: "scenes_extracted", label: "Нарезаем фрагменты" },
  { key: "scenes_uploaded", label: "Загружаем видео сцен" },
  { key: "scenes_materialized", label: "Финализируем сцены" },
  { key: "scenes_annotated", label: "Готовим описания сцен" },
  { key: "scenes_embedded", label: "Подключаем умный поиск" },
] as const;

export const SEARCH_EVENT_LABEL: Record<SearchEvent["type"], string> = {
  search_started: "Начинаем поиск",
  thinking: "Анализируем запрос",
  searching: "Ищем совпадения",
  results_found: "Нашли похожие сцены",
  conclusion: "Формируем ответ",
  error: "Ошибка поиска",
};
