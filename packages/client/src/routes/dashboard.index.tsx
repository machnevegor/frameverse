import { createFileRoute } from "@tanstack/react-router";
import { parseAsInteger, parseAsString, useQueryState } from "nuqs";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "#/components/ui/tabs";
import { MovieTable } from "#/widgets/movie-table/MovieTable";
import { TaskTable } from "#/widgets/task-table/TaskTable";

export const Route = createFileRoute("/dashboard/")({
  component: DashboardIndexPage,
});

function DashboardIndexPage() {
  const [tabParam, setTab] = useQueryState("tab", parseAsString);
  const [, setPage] = useQueryState("page", parseAsInteger);
  const [, setPerPage] = useQueryState("per_page", parseAsInteger);
  const tab = tabParam === "tasks" ? "tasks" : "movies";

  function handleTabChange(nextTab: string) {
    if (nextTab !== "movies" && nextTab !== "tasks") return;
    if (nextTab === tab) return;
    void setTab(nextTab === "movies" ? null : nextTab);
    void setPage(null);
    void setPerPage(null);
  }

  return (
    <Tabs onValueChange={handleTabChange} value={tab}>
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
