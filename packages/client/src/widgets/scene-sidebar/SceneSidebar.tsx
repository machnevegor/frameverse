import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { parseAsString, useQueryState } from "nuqs";
import { Button } from "#/components/ui/button";
import { ScrollArea } from "#/components/ui/scroll-area";
import { Separator } from "#/components/ui/separator";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "#/components/ui/sheet";
import { Skeleton } from "#/components/ui/skeleton";
import {
  sceneFramesQueryOptions,
  sceneQueryOptions,
} from "#/entities/scene/api";
import { SceneTranscript } from "#/entities/scene/SceneTranscript";
import { getFrameImageUrl, getSceneVideoUrl } from "#/shared/api/client";
import type { Scene } from "#/shared/api/types";
import { formatTimestamp } from "#/shared/lib/format";
import { ScenePlayer } from "#/widgets/scene-player/ScenePlayer";

interface SceneSidebarProps {
  scenes: Scene[];
}

export function SceneSidebar({ scenes }: SceneSidebarProps) {
  const [sceneId, setSceneId] = useQueryState("scene", parseAsString);

  const currentIndex = scenes.findIndex((s) => s.id === sceneId);
  const isOpen = Boolean(sceneId);

  function close() {
    void setSceneId(null);
  }

  function navigateTo(index: number) {
    const scene = scenes[index];
    if (scene) void setSceneId(scene.id);
  }

  return (
    <Sheet onOpenChange={(o) => !o && close()} open={isOpen}>
      <SheetContent
        className="flex h-full w-full flex-col gap-0 overflow-hidden p-0 sm:max-w-2xl lg:max-w-3xl"
        showCloseButton={false}
        side="right"
      >
        <SheetHeader className="flex shrink-0 flex-row items-center justify-between border-b bg-background/80 px-6 py-4 backdrop-blur-sm">
          <SheetTitle className="text-base">
            {currentIndex >= 0
              ? `Сцена ${currentIndex + 1} из ${scenes.length}`
              : "Сцена"}
          </SheetTitle>
          <Button onClick={close} size="icon-sm" variant="ghost">
            <X className="size-4" />
          </Button>
        </SheetHeader>

        {sceneId && (
          <SceneSidebarContent
            currentIndex={currentIndex}
            onNext={() => navigateTo(currentIndex + 1)}
            onPrev={() => navigateTo(currentIndex - 1)}
            sceneId={sceneId}
            total={scenes.length}
          />
        )}
      </SheetContent>
    </Sheet>
  );
}

interface SceneSidebarContentProps {
  sceneId: string;
  currentIndex: number;
  total: number;
  onPrev: () => void;
  onNext: () => void;
}

function SceneSidebarContent({
  sceneId,
  currentIndex,
  total,
  onPrev,
  onNext,
}: SceneSidebarContentProps) {
  const { data: scene, isLoading: sceneLoading } = useQuery(
    sceneQueryOptions(sceneId),
  );
  const { data: frames } = useQuery(sceneFramesQueryOptions(sceneId));

  if (sceneLoading) {
    return (
      <div className="flex-1 space-y-4 overflow-auto p-4">
        <Skeleton className="aspect-video w-full rounded-lg" />
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (!scene) return null;

  const videoUrl = scene.video_url ?? getSceneVideoUrl(sceneId);

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <ScrollArea className="min-h-0 flex-1">
        <div className="space-y-6 p-6 pb-8">
          <ScenePlayer
            hasNext={currentIndex < total - 1}
            hasPrev={currentIndex > 0}
            onNext={onNext}
            onPrev={onPrev}
            videoUrl={videoUrl}
          />

          <p className="text-muted-foreground text-sm tabular-nums">
            {formatTimestamp(scene.start)} – {formatTimestamp(scene.end)}
            <span className="ml-2">({formatTimestamp(scene.duration)})</span>
          </p>

          {frames && frames.length > 0 && (
            <>
              <Separator />
              <div>
                <p className="mb-2 font-medium text-muted-foreground text-xs uppercase tracking-wide">
                  Ключевые кадры ({frames.length})
                </p>
                <div className="grid grid-cols-5 gap-1">
                  {frames.map((frame) => (
                    <img
                      alt={`Кадр ${frame.position + 1}`}
                      className="aspect-video w-full rounded object-cover"
                      key={frame.id}
                      loading="lazy"
                      src={frame.image_url ?? getFrameImageUrl(frame.id)}
                    />
                  ))}
                </div>
              </div>
            </>
          )}

          <Separator />
          <div className="space-y-2">
            <p className="font-medium text-muted-foreground text-xs uppercase tracking-wide">
              Аннотация
            </p>
            {scene.annotation?.text ? (
              <p className="text-sm leading-relaxed">{scene.annotation.text}</p>
            ) : (
              <p className="text-muted-foreground text-sm">
                Аннотация недоступна
              </p>
            )}
          </div>

          <Separator />
          <div className="space-y-3">
            <p className="font-medium text-muted-foreground text-xs uppercase tracking-wide">
              Транскрипт
            </p>
            <SceneTranscript transcript={scene.transcript} />
          </div>
        </div>
      </ScrollArea>

      {total > 1 && (
        <div className="flex shrink-0 justify-between border-t bg-background/90 px-6 py-4 backdrop-blur-sm">
          <Button
            disabled={currentIndex <= 0}
            onClick={onPrev}
            size="sm"
            variant="outline"
          >
            <ChevronLeft className="mr-1 size-4" />
            Предыдущая
          </Button>
          <Button
            disabled={currentIndex >= total - 1}
            onClick={onNext}
            size="sm"
            variant="outline"
          >
            Следующая
            <ChevronRight className="ml-1 size-4" />
          </Button>
        </div>
      )}
    </div>
  );
}
