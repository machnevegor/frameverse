import { useQuery } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";
import { AlertCircle, ArrowLeft, ExternalLink } from "lucide-react";
import { motion } from "motion/react";
import { Button } from "#/components/ui/button";
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
    // Poll while task is still processing
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
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-center gap-2">
        <Button asChild size="sm" variant="ghost">
          <Link to="/dashboard">
            <ArrowLeft className="mr-1 size-4" />
            Дашборд
          </Link>
        </Button>
      </div>

      {/* Status + title */}
      <motion.div
        animate={{ opacity: 1, y: 0 }}
        className="island-shell space-y-4 rounded-2xl p-5 sm:p-6"
        initial={{ opacity: 0, y: 16 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <p className="font-semibold text-lg">{task.movie_title}</p>
            <p className="text-muted-foreground text-sm">
              Задача создана {formatRelativeDate(task.created_at)}
            </p>
          </div>
          <TaskStatusBadge status={task.status} />
        </div>

        <div className="text-sm">
          <span className="text-muted-foreground">Фильм: </span>
          <Link
            className="font-medium underline-offset-4 hover:underline"
            params={{ movieId: task.movie_id }}
            to="/movies/$movieId"
          >
            Открыть страницу фильма →
          </Link>
        </div>

        {/* Progress */}
        {task.progress && (
          <>
            <Separator />
            <div>
              <p className="mb-3 font-medium text-sm">Прогресс обработки</p>
              <TaskProgressBar progress={task.progress} />
            </div>
          </>
        )}

        {/* Error */}
        {isFailedStatus(task.status) && (
          <>
            <Separator />
            <div className="flex gap-3 rounded-lg border border-destructive/20 bg-destructive/5 p-4">
              <AlertCircle className="mt-0.5 size-4 shrink-0 text-destructive" />
              <div className="space-y-1 text-sm">
                {task.error_code && (
                  <p className="font-medium text-destructive">
                    Код ошибки: {task.error_code}
                  </p>
                )}
                {task.error_message && (
                  <p className="text-muted-foreground">{task.error_message}</p>
                )}
              </div>
            </div>
          </>
        )}

        {/* External links */}
        <Separator />
        <div className="flex flex-wrap gap-2">
          <Button asChild size="sm" variant="outline">
            <a
              href={task.temporal_workflow_url}
              rel="noreferrer"
              target="_blank"
            >
              <ExternalLink className="mr-1.5 size-3.5" />
              Temporal Workflow
            </a>
          </Button>
          <Button asChild size="sm" variant="outline">
            <a href={task.langfuse_trace_url} rel="noreferrer" target="_blank">
              <ExternalLink className="mr-1.5 size-3.5" />
              Langfuse Trace
            </a>
          </Button>
        </div>

        {/* Cancel */}
        <CancelTaskButton status={task.status} taskId={task.id} />
      </motion.div>
    </div>
  );
}
