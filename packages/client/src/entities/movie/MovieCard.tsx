import { Film } from "lucide-react";
import { Badge } from "#/components/ui/badge";
import { Separator } from "#/components/ui/separator";
import type { Movie } from "#/shared/api/types";
import { formatDuration } from "#/shared/lib/format";

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

  const meta: { label: string; value: React.ReactNode }[] = [];

  if (movie.year) meta.push({ label: "Год", value: movie.year });
  if (movie.duration)
    meta.push({ label: "Время", value: formatDuration(movie.duration) });
  if (movie.genres?.length)
    meta.push({
      label: "Жанр",
      value: (
        <div className="flex flex-wrap gap-1">
          {movie.genres.map((g) => (
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

  return (
    <div className="flex flex-col gap-6 sm:flex-row sm:gap-8">
      {/* Poster */}
      <div className="shrink-0">
        <PosterThumb
          posterUrl={movie.poster_url}
          size="lg"
          title={movie.title}
        />
      </div>

      {/* Info */}
      <div className="min-w-0 flex-1 space-y-4">
        <div>
          <h1 className="font-bold text-2xl leading-tight sm:text-3xl">
            {movie.title}
            {movie.year && (
              <span className="ml-2 font-normal text-2xl text-muted-foreground">
                ({movie.year})
              </span>
            )}
          </h1>
          {movie.short_description && (
            <p className="mt-2 text-muted-foreground text-sm leading-relaxed">
              {movie.short_description}
            </p>
          )}
        </div>

        {meta.length > 0 && (
          <>
            <Separator />
            <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2.5 text-sm">
              {meta.map(({ label, value }) => (
                <>
                  <dt className="text-muted-foreground" key={`${label}-dt`}>
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

        {movie.description && movie.description !== movie.short_description && (
          <>
            <Separator />
            <div>
              <p className="mb-1.5 font-medium text-muted-foreground text-xs uppercase tracking-wide">
                О фильме
              </p>
              <p className="text-sm leading-relaxed">{movie.description}</p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

interface PosterThumbProps {
  posterUrl?: string | null;
  title: string;
  size: "sm" | "md" | "lg";
}

const POSTER_SIZES = {
  sm: "h-14 w-10",
  md: "h-28 w-20",
  lg: "h-72 w-48 sm:h-80 sm:w-56",
};

function PosterThumb({ posterUrl, title, size }: PosterThumbProps) {
  const sizeClass = POSTER_SIZES[size];

  if (!posterUrl) {
    return (
      <div
        className={`${sizeClass} flex shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground`}
      >
        <Film className="size-6" />
      </div>
    );
  }

  return (
    <img
      alt={title}
      className={`${sizeClass} shrink-0 rounded-lg object-cover shadow-md`}
      src={posterUrl}
    />
  );
}

export { PosterThumb };
