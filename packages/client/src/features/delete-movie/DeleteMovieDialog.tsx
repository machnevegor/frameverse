import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
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
import { movieKeys } from "#/entities/movie/api";
import { deleteMovie } from "#/shared/api/client";

interface DeleteMovieDialogProps {
  movieId: string;
  movieTitle: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function DeleteMovieDialog({
  movieId,
  movieTitle,
  open,
  onOpenChange,
  onSuccess,
}: DeleteMovieDialogProps) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const mutation = useMutation({
    mutationFn: () => deleteMovie(movieId),
    onSuccess: () => {
      toast.success(`«${movieTitle}» удалён`);
      void queryClient.invalidateQueries({ queryKey: movieKeys.all });
      onOpenChange(false);
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
    <AlertDialog onOpenChange={onOpenChange} open={open}>
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
            disabled={mutation.isPending}
            onClick={() => mutation.mutate()}
            variant="destructive"
          >
            {mutation.isPending ? "Удаление..." : "Удалить"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
