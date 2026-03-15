import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { SearchX } from "lucide-react";
import { motion } from "motion/react";
import { parseAsString, useQueryState } from "nuqs";
import { Badge } from "#/components/ui/badge";
import { Card, CardContent, CardHeader } from "#/components/ui/card";
import { Separator } from "#/components/ui/separator";
import { movieQueryOptions } from "#/entities/movie/api";
import { PosterThumb } from "#/entities/movie/MovieCard";
import { SceneCard, SceneCardSkeleton } from "#/entities/scene/SceneCard";
import type { SceneSearchHit } from "#/shared/api/types";
import { SEARCH_SCENES_PER_MOVIE } from "#/shared/config/constants";
import { formatDuration } from "#/shared/lib/format";

interface SearchResultsProps {
  hits: SceneSearchHit[];
  isLoading?: boolean;
}

export function SearchResults({ hits, isLoading }: SearchResultsProps) {
  if (isLoading) return <SearchSkeleton />;

  if (hits.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 py-16 text-center">
        <SearchX className="size-10 text-muted-foreground" />
        <p className="font-medium">Ничего не найдено</p>
        <p className="text-muted-foreground text-sm">
          Попробуйте другой запрос — опишите мотив, атмосферу или конкретную
          реплику
        </p>
      </div>
    );
  }

  const grouped = groupByMovie(hits);

  return (
    <motion.div
      animate={{ opacity: 1 }}
      className="space-y-8"
      initial={{ opacity: 0 }}
      transition={{ duration: 0.25 }}
    >
      {grouped.map(({ movieId, scenes }, i) => (
        <MovieResultGroup
          index={i}
          key={movieId}
          movieId={movieId}
          scenes={scenes}
        />
      ))}
    </motion.div>
  );
}

interface MovieGroup {
  movieId: string;
  scenes: SceneSearchHit[];
}

function groupByMovie(hits: SceneSearchHit[]): MovieGroup[] {
  const map = new Map<string, SceneSearchHit[]>();
  for (const hit of hits) {
    const arr = map.get(hit.movie_id) ?? [];
    arr.push(hit);
    map.set(hit.movie_id, arr);
  }
  return Array.from(map.entries()).map(([movieId, scenes]) => {
    const topByScore = [...scenes]
      .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
      .slice(0, SEARCH_SCENES_PER_MOVIE);
    return { movieId, scenes: topByScore };
  });
}

interface MovieResultGroupProps {
  movieId: string;
  scenes: SceneSearchHit[];
  index: number;
}

function MovieResultGroup({ movieId, scenes, index }: MovieResultGroupProps) {
  const { data: movie } = useQuery(movieQueryOptions(movieId));
  const [, setSceneId] = useQueryState("scene", parseAsString);

  const meta: { label: string; value: React.ReactNode }[] = [];
  if (movie) {
    if (movie.year) meta.push({ label: "Год", value: movie.year });
    if (movie.duration)
      meta.push({ label: "Время", value: formatDuration(movie.duration) });
    if (movie.genres?.length)
      meta.push({
        label: "Жанр",
        value: (
          <div className="flex flex-wrap gap-1">
            {movie.genres.slice(0, 4).map((g) => (
              <Badge key={g} variant="secondary">
                {g}
              </Badge>
            ))}
          </div>
        ),
      });
    if (movie.slogan)
      meta.push({
        label: "Слоган",
        value: <span className="italic">«{movie.slogan}»</span>,
      });
  }

  return (
    <motion.div
      animate={{ opacity: 1, y: 0 }}
      initial={{ opacity: 0, y: 16 }}
      transition={{ delay: index * 0.07, duration: 0.35, ease: "easeOut" }}
    >
      <Card>
        <CardHeader className="pb-3">
          {movie ? (
            <div className="flex flex-col gap-5 sm:flex-row sm:gap-6">
              <div className="shrink-0">
                <PosterThumb
                  posterUrl={movie.poster_url}
                  size="md"
                  title={movie.title}
                />
              </div>

              <div className="min-w-0 flex-1 space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h3 className="font-bold text-lg leading-tight">
                      {movie.title}
                      {movie.year && (
                        <span className="ml-2 font-normal text-base text-muted-foreground">
                          ({movie.year})
                        </span>
                      )}
                    </h3>
                    {movie.short_description && (
                      <p className="mt-1 line-clamp-2 text-muted-foreground text-sm">
                        {movie.short_description}
                      </p>
                    )}
                  </div>
                  <Link
                    className="shrink-0 text-primary text-sm underline-offset-4 hover:underline"
                    params={{ movieId }}
                    to="/movies/$movieId"
                  >
                    Все сцены →
                  </Link>
                </div>

                {meta.length > 0 && (
                  <>
                    <Separator />
                    <dl className="grid grid-cols-[auto_1fr] gap-x-5 gap-y-1.5 text-sm">
                      {meta.map(({ label, value }) => (
                        <>
                          <dt
                            className="text-muted-foreground"
                            key={`${label}-dt`}
                          >
                            {label}
                          </dt>
                          <dd className="font-medium" key={`${label}-dd`}>
                            {value}
                          </dd>
                        </>
                      ))}
                    </dl>
                  </>
                )}
              </div>
            </div>
          ) : (
            <div className="flex gap-5">
              <div className="h-28 w-20 shrink-0 animate-pulse rounded-lg bg-muted" />
              <div className="flex-1 space-y-2 pt-1">
                <div className="h-5 w-2/3 animate-pulse rounded bg-muted" />
                <div className="h-4 w-1/2 animate-pulse rounded bg-muted" />
                <div className="h-px w-full animate-pulse rounded bg-muted" />
                <div className="h-4 w-3/4 animate-pulse rounded bg-muted" />
              </div>
            </div>
          )}
        </CardHeader>

        <CardContent className="space-y-2 pt-0">
          <p className="text-muted-foreground text-xs">
            {scenes.length} {scenesLabel(scenes.length)} в выдаче
          </p>
          {scenes.map((scene, j) => (
            <motion.div
              animate={{ opacity: 1, y: 0 }}
              initial={{ opacity: 0, y: 8 }}
              key={scene.id}
              transition={{
                delay: index * 0.07 + j * 0.04,
                duration: 0.3,
                ease: "easeOut",
              }}
            >
              <SceneCard
                onClick={() => void setSceneId(scene.id)}
                scene={scene}
              />
            </motion.div>
          ))}
        </CardContent>
      </Card>
    </motion.div>
  );
}

function scenesLabel(n: number): string {
  if (n % 10 === 1 && n % 100 !== 11) return "сцена";
  if (n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 10 || n % 100 >= 20))
    return "сцены";
  return "сцен";
}

function SearchSkeleton() {
  return (
    <div className="space-y-6">
      {[1, 2].map((i) => (
        <Card key={i}>
          <CardHeader className="pb-3">
            <div className="flex gap-5">
              <div className="h-28 w-20 shrink-0 animate-pulse rounded-lg bg-muted" />
              <div className="flex-1 space-y-2 pt-1">
                <div className="h-5 w-2/3 animate-pulse rounded bg-muted" />
                <div className="h-4 w-1/2 animate-pulse rounded bg-muted" />
                <div className="h-px w-full rounded bg-muted" />
                <div className="h-4 w-3/4 animate-pulse rounded bg-muted" />
                <div className="h-4 w-1/3 animate-pulse rounded bg-muted" />
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            {[1, 2, 3].map((j) => (
              <SceneCardSkeleton key={j} />
            ))}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
