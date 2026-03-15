import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { SearchX } from "lucide-react";
import { motion } from "motion/react";
import { parseAsString, useQueryState } from "nuqs";
import { Fragment } from "react";
import { Badge } from "#/components/ui/badge";
import { Card, CardContent, CardHeader } from "#/components/ui/card";
import { Separator } from "#/components/ui/separator";
import { movieQueryOptions } from "#/entities/movie/api";
import { PosterThumb } from "#/entities/movie/MovieCard";
import { SceneCard } from "#/entities/scene/SceneCard";
import type { SearchResultGroup } from "#/shared/api/types";
import { formatDuration } from "#/shared/lib/format";

interface SearchResultsProps {
  groups: SearchResultGroup[];
  summary: string | null;
}

export function SearchResults({ groups, summary }: SearchResultsProps) {
  if (groups.length === 0) {
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

  return (
    <motion.div
      animate={{ opacity: 1 }}
      className="space-y-6"
      initial={{ opacity: 0 }}
      transition={{ duration: 0.25 }}
    >
      {summary && (
        <motion.div
          animate={{ opacity: 1, y: 0 }}
          initial={{ opacity: 0, y: 8 }}
          transition={{ duration: 0.3 }}
        >
          <div className="rounded-lg border border-primary/20 bg-primary/5 p-4">
            <p className="text-muted-foreground text-sm leading-relaxed">
              {summary}
            </p>
          </div>
        </motion.div>
      )}
      {groups.map((group, i) => (
        <MovieResultGroup group={group} index={i} key={group.movie_id} />
      ))}
    </motion.div>
  );
}

interface MovieResultGroupProps {
  group: SearchResultGroup;
  index: number;
}

function MovieResultGroup({ group, index }: MovieResultGroupProps) {
  const { data: movie } = useQuery(movieQueryOptions(group.movie_id));
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
                    params={{ movieId: group.movie_id }}
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
                        <Fragment key={label}>
                          <dt className="text-muted-foreground">{label}</dt>
                          <dd className="font-medium">{value}</dd>
                        </Fragment>
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
            {group.scenes.length} {scenesLabel(group.scenes.length)} в выдаче
          </p>
          {group.scenes.map((resultScene, j) => (
            <motion.div
              animate={{ opacity: 1, y: 0 }}
              initial={{ opacity: 0, y: 8 }}
              key={resultScene.scene.id}
              transition={{
                delay: index * 0.07 + j * 0.04,
                duration: 0.3,
                ease: "easeOut",
              }}
            >
              <SceneCard
                onClick={() => void setSceneId(resultScene.scene.id)}
                scene={resultScene.scene}
                thumbnailUrl={resultScene.frames[0]?.image_url}
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
