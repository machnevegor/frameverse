import { Film } from "lucide-react";
import { Badge } from "#/components/ui/badge";
import type { Movie } from "#/shared/api/types";

interface MovieCardProps {
  movie: Movie;
  compact?: boolean;
}

export function MovieCard({ movie, compact = false }: MovieCardProps) {
  if (compact) {
    return (
      <div className="flex items-center gap-3">
        <PosterThumb
          posterUrl={movie.poster_url}
          size="sm"
          title={movie.title}
        />
        <div className="min-w-0">
          <p className="truncate font-medium text-sm">{movie.title}</p>
          {movie.year && (
            <p className="text-muted-foreground text-xs">{movie.year}</p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-4">
      <PosterThumb posterUrl={movie.poster_url} size="md" title={movie.title} />
      <div className="min-w-0 flex-1">
        <h2 className="font-semibold text-xl leading-tight">{movie.title}</h2>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          {movie.year && (
            <span className="text-muted-foreground text-sm">{movie.year}</span>
          )}
          {movie.genres?.map((g) => (
            <Badge className="text-xs" key={g} variant="secondary">
              {g}
            </Badge>
          ))}
        </div>
        {movie.short_description && (
          <p className="mt-2 line-clamp-3 text-muted-foreground text-sm">
            {movie.short_description}
          </p>
        )}
      </div>
    </div>
  );
}

interface PosterThumbProps {
  posterUrl?: string | null;
  title: string;
  size: "sm" | "md";
}

function PosterThumb({ posterUrl, title, size }: PosterThumbProps) {
  const sizeClass = size === "sm" ? "h-14 w-10" : "h-28 w-20";

  if (!posterUrl) {
    return (
      <div
        className={`${sizeClass} flex shrink-0 items-center justify-center rounded bg-muted text-muted-foreground`}
      >
        <Film className="size-4" />
      </div>
    );
  }

  return (
    <img
      alt={title}
      className={`${sizeClass} shrink-0 rounded object-cover`}
      src={posterUrl}
    />
  );
}

export { PosterThumb };
