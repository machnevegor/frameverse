import { createFileRoute } from "@tanstack/react-router";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "#/components/ui/tabs";
import { MovieTable } from "#/widgets/movie-table/MovieTable";
import { TaskTable } from "#/widgets/task-table/TaskTable";

export const Route = createFileRoute("/dashboard/")({
  component: DashboardIndexPage,
});

function DashboardIndexPage() {
  return (
    <Tabs defaultValue="tasks">
      <TabsList className="mb-4">
        <TabsTrigger value="tasks">Задачи</TabsTrigger>
        <TabsTrigger value="movies">Фильмы</TabsTrigger>
      </TabsList>
      <TabsContent value="tasks">
        <TaskTable />
      </TabsContent>
      <TabsContent value="movies">
        <MovieTable />
      </TabsContent>
    </Tabs>
  );
}
