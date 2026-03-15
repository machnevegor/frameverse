import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
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
import { movieKeys } from "#/entities/movie/api";
import { deleteMovie } from "#/shared/api/client";

interface DeleteMovieDialogProps {
  movieId: string;
  movieTitle: string;
  trigger: React.ReactNode;
  onSuccess?: () => void;
}

export function DeleteMovieDialog({
  movieId,
  movieTitle,
  trigger,
  onSuccess,
}: DeleteMovieDialogProps) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const mutation = useMutation({
    mutationFn: () => deleteMovie(movieId),
    onSuccess: () => {
      toast.success(`«${movieTitle}» удалён`);
      void queryClient.invalidateQueries({ queryKey: movieKeys.all });
      setOpen(false);
      if (onSuccess) {
        onSuccess();
      } else {
        void navigate({ to: "/dashboard" });
      }
    },
    onError: () => {
      toast.error("Не удалось удалить фильм");
    },
  });

  return (
    <AlertDialog onOpenChange={setOpen} open={open}>
      <AlertDialogTrigger asChild>{trigger}</AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Удалить фильм?</AlertDialogTitle>
          <AlertDialogDescription>
            Фильм «{movieTitle}» и все связанные данные — сцены, кадры,
            транскрипты, аннотации и векторы — будут удалены безвозвратно.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Назад</AlertDialogCancel>
          <AlertDialogAction
            className="bg-destructive text-white hover:bg-destructive/90"
            disabled={mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? "Удаление..." : "Удалить"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
