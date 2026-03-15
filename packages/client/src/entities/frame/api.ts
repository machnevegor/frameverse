import { queryOptions } from "@tanstack/react-query";
import { getFrameImageUrl } from "#/shared/api/client";

export const frameKeys = {
  all: ["frames"] as const,
  image: (id: string) => ["frames", "image", id] as const,
};

export const frameImageQueryOptions = (frameId: string) =>
  queryOptions({
    queryKey: frameKeys.image(frameId),
    queryFn: () => getFrameImageUrl(frameId),
    enabled: Boolean(frameId),
    // image URLs are stable — long stale time
    staleTime: 60 * 60 * 1000,
  });
