import type { MovieStatus, SceneStatus } from "../api/types";

export const API_BASE =
  typeof window === "undefined" ? "https://frameverse.ru/api/v0" : "/api/v0";

export const SEARCH_SCENES_LIMIT = 30;
export const SEARCH_SCENES_PER_MOVIE = 3;

export const SCENES_PER_PAGE = 20;

export const MOVIE_STATUS_LABEL: Record<MovieStatus, string> = {
  queued: "В очереди",
  asr: "Распознавание речи",
  sbd: "Определение сцен",
  sbe: "Извлечение сцен",
  ann: "Аннотирование",
  emb: "Эмбеддинг",
  completed: "Завершено",
  cancelled: "Отменено",
  failed_asr: "Ошибка: распознавание речи",
  failed_sbd: "Ошибка: определение сцен",
  failed_sbe: "Ошибка: извлечение сцен",
  failed_ann: "Ошибка: аннотирование",
  failed_emb: "Ошибка: эмбеддинг",
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
  ann: "Аннотирование",
  emb: "Эмбеддинг",
  completed: "Завершено",
  cancelled: "Отменено",
  failed_ann: "Ошибка: аннотирование",
  failed_emb: "Ошибка: эмбеддинг",
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
  { key: "scenes_detected", label: "Сцены обнаружены" },
  { key: "scenes_extracted", label: "Сцены извлечены" },
  { key: "scenes_annotated", label: "Аннотировано" },
  { key: "scenes_embedded", label: "Эмбеддинг" },
] as const;
