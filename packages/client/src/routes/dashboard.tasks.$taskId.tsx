import { useQuery } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";
import {
  AlertCircle,
  ArrowLeft,
  Clock3,
  ExternalLink,
  Film,
} from "lucide-react";
import { motion } from "motion/react";
import { Button } from "#/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "#/components/ui/card";
import { Separator } from "#/components/ui/separator";
import { Skeleton } from "#/components/ui/skeleton";
import { taskQueryOptions } from "#/entities/task/api";
import { TaskProgressBar } from "#/entities/task/TaskProgressBar";
import { TaskStatusBadge } from "#/entities/task/TaskStatusBadge";
import { CancelTaskButton } from "#/features/cancel-task/CancelTaskButton";
import { isFailedStatus, isNonTerminalStatus } from "#/shared/api/types";
import { formatRelativeDate } from "#/shared/lib/format";

export const Route = createFileRoute("/dashboard/tasks/$taskId")({
  loader: async ({ context: { queryClient }, params }) => {
    await queryClient.ensureQueryData(taskQueryOptions(params.taskId));
  },
  component: TaskDetailPage,
});

function TaskDetailPage() {
  const { taskId } = Route.useParams();
  const { data: task, isLoading } = useQuery({
    ...taskQueryOptions(taskId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (!status) return false;
      return isNonTerminalStatus(status) ? 5000 : false;
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (!task) return null;

  return (
    <div className="space-y-6 py-1">
      <Button asChild size="sm" variant="ghost">
        <Link search={{ tab: "tasks" }} to="/dashboard">
          <ArrowLeft className="mr-1 size-4" />
          Дашборд
        </Link>
      </Button>

      <motion.div
        animate={{ opacity: 1, y: 0 }}
        initial={{ opacity: 0, y: 16 }}
        transition={{ duration: 0.35, ease: "easeOut" }}
      >
        <Card className="gap-0 overflow-hidden py-0">
          <CardHeader className="gap-3 border-b bg-muted/20">
            <CardTitle className="flex flex-wrap items-center justify-between gap-3">
              <span className="text-xl leading-tight">{task.movie_title}</span>
              <TaskStatusBadge status={task.status} />
            </CardTitle>
            <CardDescription className="flex flex-wrap items-center gap-4">
              <span className="inline-flex items-center gap-1.5">
                <Clock3 className="size-3.5" />
                Создана {formatRelativeDate(task.created_at)}
              </span>
              <span className="text-xs">Task ID: {task.id}</span>
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6 py-6">
            <div className="flex flex-wrap gap-2">
              <Button asChild variant="outline">
                <Link params={{ movieId: task.movie_id }} to="/movies/$movieId">
                  <Film className="mr-2 size-4" />
                  Открыть фильм
                </Link>
              </Button>
              <Button asChild variant="outline">
                <a
                  href={task.temporal_workflow_url}
                  rel="noreferrer"
                  target="_blank"
                >
                  <ExternalLink className="mr-2 size-4" />
                  Temporal
                </a>
              </Button>
              <Button asChild variant="outline">
                <a
                  href={task.langfuse_trace_url}
                  rel="noreferrer"
                  target="_blank"
                >
                  <ExternalLink className="mr-2 size-4" />
                  Langfuse
                </a>
              </Button>
            </div>

            {task.progress && (
              <div className="space-y-3 rounded-lg border bg-background p-4">
                <p className="text-muted-foreground text-xs">
                  Прогресс обработки
                </p>
                <TaskProgressBar progress={task.progress} />
              </div>
            )}

            {isFailedStatus(task.status) && (
              <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-4">
                <div className="mb-2 flex items-center gap-2">
                  <AlertCircle className="size-4 text-destructive" />
                  <p className="font-medium text-destructive text-sm">
                    Выполнение завершилось ошибкой
                  </p>
                </div>
                <div className="space-y-1.5 text-sm">
                  {task.error_code && <p>Код ошибки: {task.error_code}</p>}
                  {task.error_message && (
                    <p className="text-muted-foreground">
                      {task.error_message}
                    </p>
                  )}
                </div>
              </div>
            )}

            {isNonTerminalStatus(task.status) && (
              <>
                <Separator />
                <CancelTaskButton status={task.status} taskId={task.id} />
              </>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
