import { Link } from "@tanstack/react-router";
import type { ColumnDef } from "@tanstack/react-table";
import { ExternalLink, MoreHorizontal } from "lucide-react";
import { Button } from "#/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "#/components/ui/dropdown-menu";
import { TaskProgressCompact } from "#/entities/task/TaskProgressBar";
import { TaskStatusBadge } from "#/entities/task/TaskStatusBadge";
import { CancelTaskButton } from "#/features/cancel-task/CancelTaskButton";
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
      return <TaskProgressCompact progress={p} />;
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
    cell: ({ row }) => {
      const task = row.original;
      return (
        <div className="flex items-center justify-end gap-1">
          {isNonTerminalStatus(task.status) && (
            <CancelTaskButton status={task.status} taskId={task.id} />
          )}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                onClick={(e) => e.stopPropagation()}
                size="icon-sm"
                variant="ghost"
              >
                <MoreHorizontal className="size-4" />
                <span className="sr-only">Действия</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Задача</DropdownMenuLabel>
              <DropdownMenuItem asChild>
                <Link
                  params={{ taskId: task.id }}
                  to="/dashboard/tasks/$taskId"
                >
                  Открыть
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuLabel>Фильм</DropdownMenuLabel>
              <DropdownMenuItem asChild>
                <Link params={{ movieId: task.movie_id }} to="/movies/$movieId">
                  Открыть
                </Link>
              </DropdownMenuItem>
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
        </div>
      );
    },
  },
];
