import {
  createFileRoute,
  Link,
  Outlet,
  useMatchRoute,
} from "@tanstack/react-router";

export const Route = createFileRoute("/dashboard")({
  component: DashboardLayout,
});

function DashboardLayout() {
  const matchRoute = useMatchRoute();
  const isUpload = matchRoute({ to: "/dashboard/upload" });

  return (
    <div className="page-wrap py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="font-semibold text-2xl">Дашборд</h1>
        <nav className="flex items-center gap-2">
          <Link
            className={`rounded-lg px-3 py-1.5 text-sm transition ${
              !isUpload
                ? "bg-accent font-medium"
                : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
            }`}
            to="/dashboard"
          >
            Задачи и фильмы
          </Link>
          <Link
            className={`rounded-lg px-3 py-1.5 text-sm transition ${
              isUpload
                ? "bg-accent font-medium"
                : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
            }`}
            to="/dashboard/upload"
          >
            Загрузить фильм
          </Link>
        </nav>
      </div>

      <Outlet />
    </div>
  );
}
