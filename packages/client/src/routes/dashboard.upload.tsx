import { createFileRoute } from "@tanstack/react-router";
import { UploadMovieForm } from "#/features/upload-movie/UploadMovieForm";

export const Route = createFileRoute("/dashboard/upload")({
  component: DashboardUploadPage,
});

function DashboardUploadPage() {
  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6">
        <h2 className="font-semibold text-xl">Загрузить фильм</h2>
        <p className="mt-1 text-muted-foreground text-sm">
          Загрузите видеофайл — система обработает его и индексирует сцены для
          семантического поиска
        </p>
      </div>
      <UploadMovieForm />
    </div>
  );
}
