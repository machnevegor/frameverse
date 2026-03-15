import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import type { ColumnDef } from "@tanstack/react-table";
import { ExternalLink, MoreHorizontal } from "lucide-react";
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
import { taskKeys } from "#/entities/task/api";
import { TaskProgressCompact } from "#/entities/task/TaskProgressBar";
import { TaskStatusBadge } from "#/entities/task/TaskStatusBadge";
import { DeleteMovieDialog } from "#/features/delete-movie/DeleteMovieDialog";
import { cancelTask } from "#/shared/api/client";
import type { Task } from "#/shared/api/types";
import { isNonTerminalStatus } from "#/shared/api/types";
import { formatRelativeDate } from "#/shared/lib/format";

export const taskColumns: ColumnDef<Task>[] = [
  {
    accessorKey: "status",
    header: "Статус",
    cell: ({ row }) => <TaskStatusBadge status={row.original.status} />,
  },
  {
    accessorKey: "movie_title",
    header: "Фильм",
    cell: ({ row }) => (
      <Link
        className="font-medium underline-offset-4 hover:underline"
        onClick={(e) => e.stopPropagation()}
        params={{ movieId: row.original.movie_id }}
        to="/movies/$movieId"
      >
        {row.original.movie_title}
      </Link>
    ),
  },
  {
    id: "progress",
    header: "Прогресс",
    cell: ({ row }) => {
      const p = row.original.progress;
      if (!p) return <span className="text-muted-foreground text-sm">—</span>;
      return <TaskProgressCompact progress={p} status={row.original.status} />;
    },
  },
  {
    accessorKey: "created_at",
    header: "Создана",
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm">
        {formatRelativeDate(row.original.created_at)}
      </span>
    ),
  },
  {
    id: "actions",
    header: "",
    cell: ({ row }) => <TaskActions task={row.original} />,
  },
];

function TaskActions({ task }: { task: Task }) {
  const queryClient = useQueryClient();
  const [menuOpen, setMenuOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const cancelMutation = useMutation({
    mutationFn: () => cancelTask(task.id),
    onSuccess: () => {
      toast.success("Задача отменена");
      void queryClient.invalidateQueries({ queryKey: taskKeys.all });
      void queryClient.invalidateQueries({ queryKey: movieKeys.all });
      setCancelOpen(false);
    },
    onError: () => toast.error("Не удалось отменить задачу"),
  });

  function handleOpenDelete(e: {
    preventDefault: () => void;
    stopPropagation: () => void;
  }) {
    e.preventDefault();
    e.stopPropagation();
    setMenuOpen(false);
    setTimeout(() => setDeleteOpen(true), 0);
  }

  function handleOpenCancel(e: {
    preventDefault: () => void;
    stopPropagation: () => void;
  }) {
    e.preventDefault();
    e.stopPropagation();
    setMenuOpen(false);
    setTimeout(() => setCancelOpen(true), 0);
  }

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
            <Link params={{ movieId: task.movie_id }} to="/movies/$movieId">
              Открыть
            </Link>
          </DropdownMenuItem>
          <DropdownMenuItem
            className="text-destructive focus:bg-destructive/10 focus:text-destructive"
            onClick={handleOpenDelete}
            onPointerDown={handleOpenDelete}
            onSelect={handleOpenDelete}
          >
            Удалить
          </DropdownMenuItem>

          <DropdownMenuSeparator />
          <DropdownMenuLabel>Задача</DropdownMenuLabel>
          <DropdownMenuItem asChild>
            <Link params={{ taskId: task.id }} to="/dashboard/tasks/$taskId">
              Открыть
            </Link>
          </DropdownMenuItem>
          {isNonTerminalStatus(task.status) ? (
            <DropdownMenuItem
              className="text-destructive focus:bg-destructive/10 focus:text-destructive"
              onClick={handleOpenCancel}
              onPointerDown={handleOpenCancel}
              onSelect={handleOpenCancel}
            >
              Отменить
            </DropdownMenuItem>
          ) : (
            <DropdownMenuItem disabled>Отменить</DropdownMenuItem>
          )}

          <DropdownMenuSeparator />
          <DropdownMenuLabel>Ссылки</DropdownMenuLabel>
          <DropdownMenuItem asChild>
            <a
              className="flex items-center gap-2"
              href={task.temporal_workflow_url}
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
              href={task.langfuse_trace_url}
              rel="noreferrer"
              target="_blank"
            >
              <ExternalLink className="size-3.5" />
              Langfuse
            </a>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <AlertDialog onOpenChange={setCancelOpen} open={cancelOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Отменить задачу?</AlertDialogTitle>
            <AlertDialogDescription>
              Выполнение текущей задачи будет остановлено без возможности
              восстановления.
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
        movieId={task.movie_id}
        movieTitle={task.movie_title}
        onOpenChange={setDeleteOpen}
        onSuccess={() => setMenuOpen(false)}
        open={deleteOpen}
      />
    </>
  );
}
