import { queryOptions } from "@tanstack/react-query";
import { getTask, listTasks } from "#/shared/api/client";
import { isNonTerminalStatus } from "#/shared/api/types";

export const taskKeys = {
  all: ["tasks"] as const,
  list: (page: number, perPage: number) =>
    ["tasks", "list", page, perPage] as const,
  detail: (id: string) => ["tasks", "detail", id] as const,
};

export const tasksQueryOptions = (page: number, perPage: number) =>
  queryOptions({
    queryKey: taskKeys.list(page, perPage),
    queryFn: () => listTasks(page, perPage),
    refetchInterval: (query) => {
      const tasks = query.state.data?.data ?? [];
      const hasActive = tasks.some((t) => isNonTerminalStatus(t.status));
      return hasActive ? 3000 : false;
    },
  });

export const taskQueryOptions = (taskId: string) =>
  queryOptions({
    queryKey: taskKeys.detail(taskId),
    queryFn: () => getTask(taskId),
    enabled: Boolean(taskId),
    refetchInterval: (query) => {
      const task = query.state.data;
      if (!task) return false;
      return isNonTerminalStatus(task.status) ? 3000 : false;
    },
  });
