import { useQuery } from "@tanstack/react-query";
import { Image } from "lucide-react";
import { Skeleton } from "#/components/ui/skeleton";
import type { Scene } from "#/shared/api/types";
import { formatTimestamp } from "#/shared/lib/format";
import { sceneFramesQueryOptions } from "./api";

interface SceneCardProps {
  scene: Scene;
  active?: boolean;
  onClick?: () => void;
  /** Thumbnail URL from pre-loaded frames — skips the frames query when provided. */
  thumbnailUrl?: string;
  /** When false, frame thumbnail is not fetched (for lazy loading in long lists). */
  enableFrameQuery?: boolean;
}

export function SceneCard({
  scene,
  active,
  onClick,
  thumbnailUrl,
  enableFrameQuery = true,
}: SceneCardProps) {
  const { data: frames } = useQuery({
    ...sceneFramesQueryOptions(scene.id),
    enabled: enableFrameQuery && !thumbnailUrl,
  });

  const imageUrl = thumbnailUrl ?? frames?.[0]?.image_url;

  return (
    <button
      className={`group w-full rounded-xl border p-3 text-left transition hover:bg-accent/50 ${
        active ? "border-primary bg-accent/30" : "border-border"
      }`}
      onClick={onClick}
      type="button"
    >
      <div className="flex gap-3">
        <FrameThumb imageUrl={imageUrl} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <span className="font-medium text-sm">
              Сцена {scene.position + 1}
            </span>
            <span className="text-muted-foreground text-xs tabular-nums">
              {formatTimestamp(scene.start)} – {formatTimestamp(scene.end)}
            </span>
          </div>
          {scene.annotation && (
            <p className="mt-1 line-clamp-2 text-muted-foreground text-xs">
              {scene.annotation.text}
            </p>
          )}
        </div>
      </div>
    </button>
  );
}

interface FrameThumbProps {
  imageUrl?: string;
}

function FrameThumb({ imageUrl }: FrameThumbProps) {
  if (!imageUrl) {
    return (
      <div className="flex h-16 w-28 shrink-0 items-center justify-center rounded bg-muted text-muted-foreground">
        <Image className="size-4" />
      </div>
    );
  }

  return (
    <img
      alt=""
      className="h-16 w-28 shrink-0 rounded object-cover"
      loading="lazy"
      onError={(e) => {
        (e.currentTarget as HTMLImageElement).style.display = "none";
      }}
      src={imageUrl}
    />
  );
}

export function SceneCardSkeleton() {
  return (
    <div className="rounded-xl border p-3">
      <div className="flex gap-3">
        <Skeleton className="h-16 w-28 shrink-0 rounded" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-3/4" />
        </div>
      </div>
    </div>
  );
}
