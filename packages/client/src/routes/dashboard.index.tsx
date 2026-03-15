import { createFileRoute } from "@tanstack/react-router";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "#/components/ui/tabs";
import { MovieTable } from "#/widgets/movie-table/MovieTable";
import { TaskTable } from "#/widgets/task-table/TaskTable";

export const Route = createFileRoute("/dashboard/")({
  component: DashboardIndexPage,
});

function DashboardIndexPage() {
  return (
    <Tabs defaultValue="movies">
      <TabsList className="mb-4">
        <TabsTrigger value="movies">Фильмы</TabsTrigger>
        <TabsTrigger value="tasks">Задачи</TabsTrigger>
      </TabsList>
      <TabsContent value="movies">
        <MovieTable />
      </TabsContent>
      <TabsContent value="tasks">
        <TaskTable />
      </TabsContent>
    </Tabs>
  );
}
