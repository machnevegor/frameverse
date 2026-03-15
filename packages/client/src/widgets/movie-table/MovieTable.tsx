"use client";

import { useQuery } from "@tanstack/react-query";
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { parseAsInteger, useQueryState } from "nuqs";
import { Button } from "#/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "#/components/ui/select";
import { Skeleton } from "#/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "#/components/ui/table";
import { moviesQueryOptions } from "#/entities/movie/api";
import { movieColumns } from "./columns";

const DEFAULT_PAGE = 1;
const DEFAULT_PER_PAGE = 20;
const PER_PAGE_OPTIONS = [10, 20, 50];

export function MovieTable() {
  const [pageParam, setPage] = useQueryState("page", parseAsInteger);
  const [perPageParam, setPerPage] = useQueryState("per_page", parseAsInteger);
  const page = pageParam && pageParam > 0 ? pageParam : DEFAULT_PAGE;
  const perPage =
    perPageParam && PER_PAGE_OPTIONS.includes(perPageParam)
      ? perPageParam
      : DEFAULT_PER_PAGE;

  const { data, isLoading } = useQuery(moviesQueryOptions(page, perPage));

  function setPagination(nextPage: number, nextPerPage: number) {
    if (nextPage <= DEFAULT_PAGE) {
      void setPage(null);
      void setPerPage(null);
      return;
    }
    void setPage(nextPage);
    void setPerPage(nextPerPage);
  }

  const table = useReactTable({
    data: data?.data ?? [],
    columns: movieColumns,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    pageCount: data?.pagination.total_pages ?? -1,
  });

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((hg) => (
              <TableRow key={hg.id}>
                {hg.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                // biome-ignore lint/suspicious/noArrayIndexKey: loading skeleton
                <TableRow key={i}>
                  {movieColumns.map((_, j) => (
                    // biome-ignore lint/suspicious/noArrayIndexKey: loading skeleton
                    <TableCell key={j}>
                      <Skeleton className="h-5 w-full" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : table.getRowModel().rows.length === 0 ? (
              <TableRow>
                <TableCell
                  className="py-10 text-center text-muted-foreground"
                  colSpan={movieColumns.length}
                >
                  Фильмов не найдено
                </TableCell>
              </TableRow>
            ) : (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext(),
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {data && data.pagination.total_pages > 1 && (
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">На странице</span>
            <Select
              onValueChange={(v) => {
                setPagination(DEFAULT_PAGE, Number(v));
              }}
              value={String(perPage)}
            >
              <SelectTrigger className="h-8 w-20">
                <SelectValue />
              </SelectTrigger>
              <SelectContent align="end">
                {PER_PAGE_OPTIONS.map((n) => (
                  <SelectItem key={n} value={String(n)}>
                    {n}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-muted-foreground">
              Страница {data.pagination.page} из {data.pagination.total_pages}
            </span>
            <Button
              disabled={page <= 1}
              onClick={() => setPagination(page - 1, perPage)}
              size="sm"
              variant="outline"
            >
              Назад
            </Button>
            <Button
              disabled={!data.pagination.has_next}
              onClick={() => setPagination(page + 1, perPage)}
              size="sm"
              variant="outline"
            >
              Вперёд
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
