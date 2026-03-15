import { Link } from "@tanstack/react-router";
import type { ColumnDef } from "@tanstack/react-table";
import { Film, MoreHorizontal } from "lucide-react";
import { Badge } from "#/components/ui/badge";
import { Button } from "#/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "#/components/ui/dropdown-menu";
import { MovieStatusBadge } from "#/entities/movie/MovieStatusBadge";
import { DeleteMovieDialog } from "#/features/delete-movie/DeleteMovieDialog";
import type { Movie } from "#/shared/api/types";
import { formatDuration } from "#/shared/lib/format";

export const movieColumns: ColumnDef<Movie>[] = [
  {
    id: "poster",
    header: "",
    cell: ({ row }) => {
      const movie = row.original;
      if (!movie.poster_url) {
        return (
          <div className="flex size-10 w-7 items-center justify-center rounded bg-muted text-muted-foreground">
            <Film className="size-3.5" />
          </div>
        );
      }
      return (
        <img
          alt=""
          className="h-14 w-10 rounded object-cover"
          src={movie.poster_url}
        />
      );
    },
  },
  {
    accessorKey: "title",
    header: "Название",
    cell: ({ row }) => (
      <Link
        className="font-medium underline-offset-4 hover:underline"
        params={{ movieId: row.original.id }}
        to="/movies/$movieId"
      >
        {row.original.title}
      </Link>
    ),
  },
  {
    accessorKey: "year",
    header: "Год",
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm">
        {row.original.year ?? "—"}
      </span>
    ),
  },
  {
    id: "genres",
    header: "Жанры",
    cell: ({ row }) => {
      const genres = row.original.genres;
      if (!genres?.length)
        return <span className="text-muted-foreground text-sm">—</span>;
      return (
        <div className="flex flex-wrap gap-1">
          {genres.slice(0, 3).map((g) => (
            <Badge className="text-xs" key={g} variant="secondary">
              {g}
            </Badge>
          ))}
          {genres.length > 3 && (
            <Badge className="text-xs" variant="outline">
              +{genres.length - 3}
            </Badge>
          )}
        </div>
      );
    },
  },
  {
    id: "status",
    header: "Статус",
    cell: ({ row }) => <MovieStatusBadge movie={row.original} />,
  },
  {
    accessorKey: "duration",
    header: "Длительность",
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm tabular-nums">
        {row.original.duration ? formatDuration(row.original.duration) : "—"}
      </span>
    ),
  },
  {
    id: "actions",
    header: "",
    cell: ({ row }) => {
      const movie = row.original;
      return (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button size="icon-sm" variant="ghost">
              <MoreHorizontal className="size-4" />
              <span className="sr-only">Действия</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>Фильм</DropdownMenuLabel>
            <DropdownMenuItem asChild>
              <Link params={{ movieId: movie.id }} to="/movies/$movieId">
                Открыть
              </Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="p-0"
              onSelect={(e) => e.preventDefault()}
            >
              <DeleteMovieDialog
                movieId={movie.id}
                movieTitle={movie.title}
                trigger={
                  <button
                    className="w-full px-2 py-1.5 text-left text-destructive text-sm"
                    type="button"
                  >
                    Удалить
                  </button>
                }
              />
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );
    },
  },
];
