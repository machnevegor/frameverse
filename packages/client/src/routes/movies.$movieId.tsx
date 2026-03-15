import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { motion } from "motion/react";
import { parseAsInteger, parseAsString, useQueryState } from "nuqs";
import { useEffect, useRef, useState } from "react";
import { Badge } from "#/components/ui/badge";
import { Button } from "#/components/ui/button";
import { Separator } from "#/components/ui/separator";
import { Skeleton } from "#/components/ui/skeleton";
import {
  movieQueryOptions,
  movieScenesQueryOptions,
} from "#/entities/movie/api";
import { MovieCard } from "#/entities/movie/MovieCard";
import { SceneCard, SceneCardSkeleton } from "#/entities/scene/SceneCard";
import type { Scene } from "#/shared/api/types";
import { SCENES_PER_PAGE } from "#/shared/config/constants";
import { SceneSidebar } from "#/widgets/scene-sidebar/SceneSidebar";

export const Route = createFileRoute("/movies/$movieId")({
  loader: async ({ context: { queryClient }, params }) => {
    await queryClient.ensureQueryData(movieQueryOptions(params.movieId));
  },
  component: MoviePage,
});

function MoviePage() {
  const { movieId } = Route.useParams();
  const [selectedSceneId, setSelectedSceneId] = useQueryState(
    "scene",
    parseAsString,
  );
  const [scenePage, setScenePage] = useQueryState(
    "scenePage",
    parseAsInteger.withDefault(1),
  );

  const { data: movie, isLoading: movieLoading } = useQuery(
    movieQueryOptions(movieId),
  );
  const { data: scenes, isLoading: scenesLoading } = useQuery(
    movieScenesQueryOptions(movieId),
  );

  const totalScenes = scenes?.length ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalScenes / SCENES_PER_PAGE));
  const page = Math.min(scenePage, totalPages);
  const start = (page - 1) * SCENES_PER_PAGE;
  const paginatedScenes = scenes?.slice(start, start + SCENES_PER_PAGE) ?? [];

  // When a scene is opened, jump to the page that contains it
  useEffect(() => {
    if (!selectedSceneId || !scenes) return;
    const idx = scenes.findIndex((s) => s.id === selectedSceneId);
    if (idx < 0) return;
    const targetPage = Math.floor(idx / SCENES_PER_PAGE) + 1;
    if (targetPage !== scenePage) {
      void setScenePage(targetPage <= 1 ? null : targetPage);
    }
  }, [selectedSceneId, scenes, scenePage, setScenePage]);

  return (
    <main className="py-8 content-container">
      {/* Movie details */}
      {movieLoading ? (
        <div className="mb-8 flex flex-col gap-6 sm:flex-row sm:gap-8">
          <Skeleton className="h-72 w-48 shrink-0 rounded-lg sm:h-80 sm:w-56" />
          <div className="flex-1 space-y-3">
            <Skeleton className="h-8 w-2/3" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
            <Skeleton className="h-px w-full" />
            <div className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2.5">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton
                  className="h-4 w-16"
                  // biome-ignore lint/suspicious/noArrayIndexKey: skeleton
                  key={i * 2}
                />
              ))}
            </div>
          </div>
        </div>
      ) : movie ? (
        <div className="mb-8">
          <MovieCard movie={movie} />
        </div>
      ) : null}

      <Separator className="mb-6" />

      {/* Scenes list */}
      <div>
        <div className="mb-4 flex items-center gap-2">
          <h2 className="font-semibold text-lg">Сцены</h2>
          {scenes && (
            <Badge className="text-xs" variant="secondary">
              {totalScenes}
            </Badge>
          )}
        </div>

        <div className="space-y-2">
          {scenesLoading ? (
            Array.from({ length: 6 }).map((_, i) => (
              // biome-ignore lint/suspicious/noArrayIndexKey: skeleton
              <SceneCardSkeleton key={i} />
            ))
          ) : scenes?.length === 0 ? (
            <p className="py-8 text-center text-muted-foreground text-sm">
              Сцены ещё не обработаны
            </p>
          ) : (
            paginatedScenes.map((scene, i) => (
              <motion.div
                animate={{ opacity: 1, y: 0 }}
                initial={{ opacity: 0, y: 8 }}
                key={scene.id}
                transition={{
                  delay: Math.min(i * 0.03, 0.3),
                  duration: 0.28,
                  ease: "easeOut",
                }}
              >
                <LazySceneCard
                  active={scene.id === selectedSceneId}
                  onClick={() => void setSelectedSceneId(scene.id)}
                  scene={scene}
                />
              </motion.div>
            ))
          )}
        </div>

        {totalScenes > SCENES_PER_PAGE && (
          <div className="mt-4 flex items-center justify-between text-sm">
            <span className="text-muted-foreground">
              Страница {page} из {totalPages}
            </span>
            <div className="flex gap-1">
              <Button
                disabled={page <= 1}
                onClick={() => void setScenePage(page - 1)}
                size="sm"
                variant="outline"
              >
                Назад
              </Button>
              <Button
                disabled={page >= totalPages}
                onClick={() => void setScenePage(page + 1)}
                size="sm"
                variant="outline"
              >
                Вперёд
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Scene sidebar sheet */}
      {scenes && <SceneSidebar scenes={scenes} />}
    </main>
  );
}

function LazySceneCard({
  scene,
  active,
  onClick,
}: {
  scene: Scene;
  active: boolean;
  onClick: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([entry]) => setInView(entry.isIntersecting),
      { rootMargin: "200px", threshold: 0 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  // Scroll active card into view when it becomes active (e.g. after page jump)
  useEffect(() => {
    if (active && ref.current) {
      ref.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [active]);

  return (
    <div ref={ref}>
      <SceneCard
        active={active}
        enableFrameQuery={inView}
        onClick={onClick}
        scene={scene}
      />
    </div>
  );
}
