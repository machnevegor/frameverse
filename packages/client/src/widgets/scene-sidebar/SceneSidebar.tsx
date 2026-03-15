import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { parseAsString, useQueryState } from "nuqs";
import { useState } from "react";
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
import type { Frame, Scene, SearchResultScene } from "#/shared/api/types";
import { formatTimestamp } from "#/shared/lib/format";
import { ScenePlayer } from "#/widgets/scene-player/ScenePlayer";

// Sidebar accepts either plain Scene[] (movie page) or SearchResultScene[] (search results)
type SidebarEntry = Scene | SearchResultScene;

function isSidebarEntry(entry: SidebarEntry): entry is SearchResultScene {
  return "frames" in entry;
}

function entryScene(entry: SidebarEntry): Scene {
  return isSidebarEntry(entry) ? entry.scene : entry;
}

function entryFrames(entry: SidebarEntry): Frame[] | undefined {
  return isSidebarEntry(entry) ? entry.frames : undefined;
}

interface SceneSidebarProps {
  scenes: SidebarEntry[];
}

export function SceneSidebar({ scenes }: SceneSidebarProps) {
  const [sceneId, setSceneId] = useQueryState("scene", parseAsString);

  const currentIndex = scenes.findIndex((s) => entryScene(s).id === sceneId);
  const isOpen = Boolean(sceneId);

  function close() {
    void setSceneId(null);
  }

  function navigateTo(index: number) {
    const entry = scenes[index];
    if (entry) void setSceneId(entryScene(entry).id);
  }

  const currentEntry = currentIndex >= 0 ? scenes[currentIndex] : undefined;

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
            preloadedFrames={
              currentEntry ? entryFrames(currentEntry) : undefined
            }
            preloadedScene={
              currentEntry && isSidebarEntry(currentEntry)
                ? currentEntry.scene
                : undefined
            }
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
  preloadedScene?: Scene;
  preloadedFrames?: Frame[];
}

function SceneSidebarContent({
  sceneId,
  currentIndex,
  total,
  onPrev,
  onNext,
  preloadedScene,
  preloadedFrames,
}: SceneSidebarContentProps) {
  const [currentSceneTime, setCurrentSceneTime] = useState(0);
  const [seekRequest, setSeekRequest] = useState<{
    time: number;
    seq: number;
  } | null>(null);
  const [seekSeq, setSeekSeq] = useState(0);
  const { data: fetchedScene, isLoading: sceneLoading } = useQuery({
    ...sceneQueryOptions(sceneId),
    enabled: !preloadedScene,
  });
  const { data: fetchedFrames } = useQuery({
    ...sceneFramesQueryOptions(sceneId),
    enabled: !preloadedFrames,
  });

  const scene = preloadedScene ?? fetchedScene;
  const frames = preloadedFrames ?? fetchedFrames;
  const isLoading = !preloadedScene && sceneLoading;

  if (isLoading) {
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
            onTimeChange={setCurrentSceneTime}
            seekRequest={seekRequest}
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
                    <button
                      className="group overflow-hidden rounded"
                      key={frame.id}
                      onClick={() => {
                        const nextSeq = seekSeq + 1;
                        setSeekSeq(nextSeq);
                        setSeekRequest({ time: frame.timestamp, seq: nextSeq });
                      }}
                      type="button"
                    >
                      <img
                        alt={`Кадр ${frame.position + 1}`}
                        className="aspect-video w-full rounded object-cover transition group-hover:opacity-90"
                        loading="lazy"
                        src={frame.image_url ?? getFrameImageUrl(frame.id)}
                      />
                    </button>
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
            <SceneTranscript
              currentSceneTime={currentSceneTime}
              sceneStartInMovie={scene.start}
              transcript={scene.transcript}
            />
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
