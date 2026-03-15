import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { SearchX } from "lucide-react";
import { motion } from "motion/react";
import { Separator } from "#/components/ui/separator";
import { movieQueryOptions } from "#/entities/movie/api";
import { MovieCard } from "#/entities/movie/MovieCard";
import { SceneCard, SceneCardSkeleton } from "#/entities/scene/SceneCard";
import type { SceneSearchHit } from "#/shared/api/types";
import { SEARCH_SCENES_PER_MOVIE } from "#/shared/config/constants";

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

  // Group hits by movie_id preserving order of first occurrence
  const grouped = groupByMovie(hits);
  const isSingleMovie = grouped.length === 1;

  return (
    <motion.div
      animate={{ opacity: 1 }}
      className="space-y-8"
      initial={{ opacity: 0 }}
      transition={{ duration: 0.25 }}
    >
      {grouped.map(({ movieId, scenes }, i) => (
        <MovieResultGroup
          expanded={isSingleMovie}
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
  expanded: boolean;
  index: number;
}

function MovieResultGroup({
  movieId,
  scenes,
  expanded,
  index,
}: MovieResultGroupProps) {
  const { data: movie } = useQuery(movieQueryOptions(movieId));
  const navigate = useNavigate();

  function handleSceneClick(sceneId: string) {
    void navigate({
      to: "/movies/$movieId",
      params: { movieId },
      search: { scene: sceneId },
    });
  }

  return (
    <motion.div
      animate={{ opacity: 1, y: 0 }}
      className="island-shell rounded-2xl p-4 sm:p-6"
      initial={{ opacity: 0, y: 16 }}
      transition={{ delay: index * 0.07, duration: 0.35, ease: "easeOut" }}
    >
      {movie ? (
        <MovieCard compact={!expanded} movie={movie} />
      ) : (
        // Skeleton while movie loads
        <div className="h-10 animate-pulse rounded bg-muted" />
      )}

      <Separator className="my-4" />

      <div className="mb-3 flex items-center justify-between">
        <p className="font-medium text-muted-foreground text-sm">
          {scenes.length} {scenesLabel(scenes.length)}
        </p>
        {movie && (
          <a
            className="text-muted-foreground text-xs underline-offset-4 hover:text-foreground hover:underline"
            href={`/movies/${movieId}`}
          >
            Все сцены фильма →
          </a>
        )}
      </div>

      <div className="space-y-2">
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
              onClick={() => handleSceneClick(scene.id)}
              scene={scene}
            />
          </motion.div>
        ))}
      </div>
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
    <div className="space-y-8">
      {[1, 2].map((i) => (
        <div className="island-shell rounded-2xl p-4 sm:p-6" key={i}>
          <div className="mb-4 h-12 animate-pulse rounded bg-muted" />
          <div className="space-y-2">
            {[1, 2, 3].map((j) => (
              <SceneCardSkeleton key={j} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
