import { queryOptions } from "@tanstack/react-query";
import { getScene, listSceneFrames } from "#/shared/api/client";

export const sceneKeys = {
  all: ["scenes"] as const,
  detail: (id: string) => ["scenes", "detail", id] as const,
  frames: (id: string) => ["scenes", "frames", id] as const,
};

export const sceneQueryOptions = (sceneId: string) =>
  queryOptions({
    queryKey: sceneKeys.detail(sceneId),
    queryFn: () => getScene(sceneId),
    enabled: Boolean(sceneId),
  });

export const sceneFramesQueryOptions = (sceneId: string) =>
  queryOptions({
    queryKey: sceneKeys.frames(sceneId),
    queryFn: () => listSceneFrames(sceneId),
    enabled: Boolean(sceneId),
  });
