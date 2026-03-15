import { useMutation, useQueryClient } from "@tanstack/react-query";
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
  AlertDialogTrigger,
} from "#/components/ui/alert-dialog";
import { Button } from "#/components/ui/button";
import { taskKeys } from "#/entities/task/api";
import { cancelTask } from "#/shared/api/client";
import type { MovieStatus } from "#/shared/api/types";
import { isNonTerminalStatus } from "#/shared/api/types";

interface CancelTaskButtonProps {
  taskId: string;
  status: MovieStatus;
}

export function CancelTaskButton({ taskId, status }: CancelTaskButtonProps) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);

  const mutation = useMutation({
    mutationFn: () => cancelTask(taskId),
    onSuccess: () => {
      toast.success("Задача отменена");
      void queryClient.invalidateQueries({ queryKey: taskKeys.all });
      setOpen(false);
    },
    onError: () => {
      toast.error("Не удалось отменить задачу");
    },
  });

  if (!isNonTerminalStatus(status)) return null;

  return (
    <AlertDialog onOpenChange={setOpen} open={open}>
      <AlertDialogTrigger asChild>
        <Button size="sm" variant="outline">
          Отменить задачу
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Отменить задачу?</AlertDialogTitle>
          <AlertDialogDescription>
            Текущая обработка будет прервана. Отменить это действие нельзя.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Назад</AlertDialogCancel>
          <AlertDialogAction
            disabled={mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? "Отмена..." : "Отменить задачу"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
