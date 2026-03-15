import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import type { ColumnDef } from "@tanstack/react-table";
import { ExternalLink, Film, MoreHorizontal } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "#/components/ui/alert-dialog";
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
import { movieKeys } from "#/entities/movie/api";
import { MovieStatusBadge } from "#/entities/movie/MovieStatusBadge";
import { taskKeys } from "#/entities/task/api";
import { DeleteMovieDialog } from "#/features/delete-movie/DeleteMovieDialog";
import { cancelTask } from "#/shared/api/client";
import type { Movie } from "#/shared/api/types";
import { isNonTerminalStatus } from "#/shared/api/types";
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
        onClick={(e) => e.stopPropagation()}
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
    cell: ({ row }) => <MovieActions movie={row.original} />,
  },
];

function MovieActions({ movie }: { movie: Movie }) {
  const queryClient = useQueryClient();
  const [menuOpen, setMenuOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const activeTask = movie.last_task;

  const cancelMutation = useMutation({
    mutationFn: () => {
      if (!activeTask) throw new Error("Task not found");
      return cancelTask(activeTask.id);
    },
    onSuccess: () => {
      toast.success("Задача отменена");
      void queryClient.invalidateQueries({ queryKey: taskKeys.all });
      void queryClient.invalidateQueries({ queryKey: movieKeys.all });
      setCancelOpen(false);
    },
    onError: () => toast.error("Не удалось отменить задачу"),
  });

  return (
    <>
      <DropdownMenu onOpenChange={setMenuOpen} open={menuOpen}>
        <DropdownMenuTrigger asChild>
          <Button
            data-row-action="true"
            onClick={(e) => e.stopPropagation()}
            onPointerDown={(e) => e.stopPropagation()}
            size="icon-sm"
            variant="ghost"
          >
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
          <DropdownMenuItem
            className="text-destructive focus:bg-destructive/10 focus:text-destructive"
            onSelect={(e) => {
              e.preventDefault();
              setMenuOpen(false);
              setDeleteOpen(true);
            }}
          >
            Удалить
          </DropdownMenuItem>

          <DropdownMenuSeparator />
          <DropdownMenuLabel>Задача</DropdownMenuLabel>
          {activeTask ? (
            <>
              <DropdownMenuItem asChild>
                <Link
                  params={{ taskId: activeTask.id }}
                  to="/dashboard/tasks/$taskId"
                >
                  Открыть
                </Link>
              </DropdownMenuItem>
              {isNonTerminalStatus(activeTask.status) ? (
                <DropdownMenuItem
                  className="text-destructive focus:bg-destructive/10 focus:text-destructive"
                  onSelect={(e) => {
                    e.preventDefault();
                    setMenuOpen(false);
                    setCancelOpen(true);
                  }}
                >
                  Отменить
                </DropdownMenuItem>
              ) : (
                <DropdownMenuItem disabled>Отменить</DropdownMenuItem>
              )}
            </>
          ) : (
            <>
              <DropdownMenuItem disabled>Открыть</DropdownMenuItem>
              <DropdownMenuItem disabled>Отменить</DropdownMenuItem>
            </>
          )}

          <DropdownMenuSeparator />
          <DropdownMenuLabel>Ссылки</DropdownMenuLabel>
          {activeTask ? (
            <>
              <DropdownMenuItem asChild>
                <a
                  className="flex items-center gap-2"
                  href={activeTask.temporal_workflow_url}
                  rel="noreferrer"
                  target="_blank"
                >
                  <ExternalLink className="size-3.5" />
                  Temporal
                </a>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <a
                  className="flex items-center gap-2"
                  href={activeTask.langfuse_trace_url}
                  rel="noreferrer"
                  target="_blank"
                >
                  <ExternalLink className="size-3.5" />
                  Langfuse
                </a>
              </DropdownMenuItem>
            </>
          ) : (
            <>
              <DropdownMenuItem disabled>Temporal</DropdownMenuItem>
              <DropdownMenuItem disabled>Langfuse</DropdownMenuItem>
            </>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      <AlertDialog onOpenChange={setCancelOpen} open={cancelOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Отменить задачу?</AlertDialogTitle>
            <AlertDialogDescription>
              Выполнение последней задачи фильма будет остановлено.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Назад</AlertDialogCancel>
            <AlertDialogAction
              disabled={cancelMutation.isPending}
              onClick={() => cancelMutation.mutate()}
              variant="destructive"
            >
              {cancelMutation.isPending ? "Отмена..." : "Отменить"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <DeleteMovieDialog
        movieId={movie.id}
        movieTitle={movie.title}
        onOpenChange={setDeleteOpen}
        onSuccess={() => setMenuOpen(false)}
        open={deleteOpen}
      />
    </>
  );
}
