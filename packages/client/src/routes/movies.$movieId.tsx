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
import { formatDuration } from "#/shared/lib/format";
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

  return (
    <main className="py-8 content-container">
      {/* Movie details */}
      {movieLoading ? (
        <div className="mb-8 flex gap-4">
          <Skeleton className="h-28 w-20 shrink-0 rounded" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-16 w-full" />
          </div>
        </div>
      ) : movie ? (
        <div className="mb-8">
          <MovieCard movie={movie} />
          <div className="mt-3 flex flex-wrap items-center gap-3">
            {movie.duration && (
              <span className="text-muted-foreground text-sm">
                {formatDuration(movie.duration)}
              </span>
            )}
            {movie.slogan && (
              <span className="text-muted-foreground text-sm italic">
                «{movie.slogan}»
              </span>
            )}
          </div>
          {movie.description &&
            movie.short_description !== movie.description && (
              <p className="mt-3 max-w-3xl text-muted-foreground text-sm leading-relaxed">
                {movie.description}
              </p>
            )}
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
      {scenes && <SceneSidebar movieId={movieId} scenes={scenes} />}
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
