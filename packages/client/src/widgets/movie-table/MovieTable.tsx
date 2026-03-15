"use client";

import { useQuery } from "@tanstack/react-query";
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { ReactTableDevtools } from "@tanstack/react-table-devtools";
import { parseAsInteger, useQueryState } from "nuqs";
import { Button } from "#/components/ui/button";
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

const PER_PAGE = 20;

export function MovieTable() {
  const [page, setPage] = useQueryState(
    "moviePage",
    parseAsInteger.withDefault(1),
  );
  const { data, isLoading } = useQuery(moviesQueryOptions(page, PER_PAGE));

  const table = useReactTable({
    data: data?.data ?? [],
    columns: movieColumns,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    pageCount: data?.pagination.total_pages ?? -1,
  });

  return (
    <div className="space-y-4">
      <div className="rounded-md border">
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
          <span className="text-muted-foreground">
            Страница {data.pagination.page} из {data.pagination.total_pages}
          </span>
          <div className="flex gap-1">
            <Button
              disabled={page <= 1}
              onClick={() => void setPage(page - 1)}
              size="sm"
              variant="outline"
            >
              Назад
            </Button>
            <Button
              disabled={!data.pagination.has_next}
              onClick={() => void setPage(page + 1)}
              size="sm"
              variant="outline"
            >
              Вперёд
            </Button>
          </div>
        </div>
      )}
      <ReactTableDevtools table={table} />
    </div>
  );
}
