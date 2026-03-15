import { queryOptions } from "@tanstack/react-query";
import { getTask, listTasks } from "#/shared/api/client";

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
  });

export const taskQueryOptions = (taskId: string) =>
  queryOptions({
    queryKey: taskKeys.detail(taskId),
    queryFn: () => getTask(taskId),
    enabled: Boolean(taskId),
  });
