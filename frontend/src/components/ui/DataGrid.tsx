import { useMemo, useRef } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
  type RowSelectionState,
  type VisibilityState,
  type OnChangeFn,
} from "@tanstack/react-table";
import {
  ArrowUp,
  ArrowDown,
  ChevronsUpDown,
  ChevronLeft,
  ChevronRight,
  Columns3,
  Download,
  Rows3,
  Rows4,
} from "lucide-react";
import { cn } from "@/lib/cn";
import { Button } from "./Button";
import { Select } from "./Input";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "./DropdownMenu";
import { SkeletonTable } from "./Skeleton";
import { formatNumber } from "@/lib/format";

export type DataGridProps<T> = {
  data: T[];
  columns: ColumnDef<T, unknown>[];
  rowId: (row: T) => string;
  total: number;
  grandTotal?: number;
  loading?: boolean;

  sorting: SortingState;
  onSortingChange: OnChangeFn<SortingState>;

  pageIndex: number;
  pageSize: number;
  onPageChange: (pageIndex: number) => void;
  onPageSizeChange: (pageSize: number) => void;

  rowSelection?: RowSelectionState;
  onRowSelectionChange?: OnChangeFn<RowSelectionState>;

  columnVisibility?: VisibilityState;
  onColumnVisibilityChange?: OnChangeFn<VisibilityState>;

  density?: "comfortable" | "compact";
  onDensityChange?: (d: "comfortable" | "compact") => void;

  onRowClick?: (row: T) => void;
  onExport?: () => void;

  toolbar?: React.ReactNode;
  bulkActions?: React.ReactNode;
  emptyState?: React.ReactNode;
  noun?: string;
  /** Force row virtualization; omit to auto-enable when the current page has about 30+ rows. */
  virtualizeRows?: boolean;
};

export function DataGrid<T>({
  data,
  columns,
  rowId,
  total,
  grandTotal,
  loading,
  sorting,
  onSortingChange,
  pageIndex,
  pageSize,
  onPageChange,
  onPageSizeChange,
  rowSelection,
  onRowSelectionChange,
  columnVisibility,
  onColumnVisibilityChange,
  density = "comfortable",
  onDensityChange,
  onRowClick,
  onExport,
  toolbar,
  bulkActions,
  emptyState,
  noun = "rows",
  virtualizeRows,
}: DataGridProps<T>) {
  const enableSelection = Boolean(onRowSelectionChange);
  const pageCount = Math.max(1, Math.ceil(total / pageSize));

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    manualSorting: true,
    manualPagination: true,
    pageCount,
    enableRowSelection: enableSelection,
    getRowId: (row) => rowId(row),
    state: {
      sorting,
      rowSelection: rowSelection ?? {},
      columnVisibility: columnVisibility ?? {},
    },
    onSortingChange,
    onRowSelectionChange,
    onColumnVisibilityChange,
  });

  const rows = table.getRowModel().rows;
  const scrollParentRef = useRef<HTMLDivElement>(null);
  const enableVirtual =
    Boolean(data.length) &&
    !loading &&
    (virtualizeRows ?? data.length >= 30);

  const rowVirtualizer = useVirtualizer({
    count: enableVirtual ? rows.length : 0,
    getScrollElement: () => scrollParentRef.current,
    estimateSize: () => (density === "compact" ? 36 : 44),
    overscan: 8,
  });

  const virtualItems = rowVirtualizer.getVirtualItems();
  const virtualTotal = rowVirtualizer.getTotalSize();
  const paddingTop = virtualItems.length > 0 ? virtualItems[0].start : 0;
  const paddingBottom =
    virtualItems.length > 0 ? virtualTotal - virtualItems[virtualItems.length - 1].end : 0;
  const colSpan = table.getVisibleLeafColumns().length;

  const selectedCount = Object.values(rowSelection ?? {}).filter(Boolean).length;
  const cellPad = density === "compact" ? "px-3 py-1.5" : "px-3 py-2.5";

  const start = total === 0 ? 0 : pageIndex * pageSize + 1;
  const end = Math.min(total, (pageIndex + 1) * pageSize);

  const hideableColumns = useMemo(
    () => table.getAllLeafColumns().filter((c) => c.getCanHide() && c.id !== "select"),
    [table],
  );

  return (
    <div className="rounded-card border border-slate-200 bg-white shadow-card">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 p-3">
        <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">{toolbar}</div>

        {onDensityChange ? (
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => onDensityChange(density === "compact" ? "comfortable" : "compact")}
            aria-label={density === "compact" ? "Comfortable density" : "Compact density"}
            title="Toggle density"
          >
            {density === "compact" ? <Rows4 className="h-4 w-4" /> : <Rows3 className="h-4 w-4" />}
          </Button>
        ) : null}

        {hideableColumns.length > 0 ? (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="secondary" size="sm">
                <Columns3 className="h-4 w-4" /> Columns
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuLabel>Toggle columns</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {hideableColumns.map((col) => (
                <label
                  key={col.id}
                  className="flex cursor-pointer items-center gap-2 rounded-control px-2.5 py-1.5 text-small text-slate-700 hover:bg-slate-100"
                >
                  <input
                    type="checkbox"
                    checked={col.getIsVisible()}
                    onChange={col.getToggleVisibilityHandler()}
                    className="rounded border-slate-300 text-brand focus:ring-brand"
                  />
                  {typeof col.columnDef.header === "string" ? col.columnDef.header : col.id}
                </label>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        ) : null}

        {onExport ? (
          <Button variant="secondary" size="sm" onClick={onExport}>
            <Download className="h-4 w-4" /> Export
          </Button>
        ) : null}
      </div>

      {/* Bulk action bar */}
      {enableSelection && selectedCount > 0 ? (
        <div className="flex items-center justify-between gap-2 border-b border-slate-200 bg-brand/5 px-3 py-2">
          <span className="text-small font-medium text-brand">{selectedCount} selected</span>
          <div className="flex items-center gap-2">{bulkActions}</div>
        </div>
      ) : null}

      {/* Table */}
      <div className="overflow-x-auto">
        {loading && data.length === 0 ? (
          <div className="p-4">
            <SkeletonTable rows={pageSize > 10 ? 8 : pageSize} cols={columns.length} />
          </div>
        ) : data.length === 0 ? (
          <div className="p-8">{emptyState}</div>
        ) : (
          <div
            ref={scrollParentRef}
            className={enableVirtual ? "max-h-[min(60vh,560px)] overflow-auto" : undefined}
          >
            <table className="w-full text-small">
              <thead
                className={
                  enableVirtual
                    ? "sticky top-0 z-10 border-b border-slate-200 bg-slate-50/95 shadow-sm backdrop-blur"
                    : "border-b border-slate-200 bg-slate-50/60"
                }
              >
                {table.getHeaderGroups().map((hg) => (
                  <tr key={hg.id} className={enableVirtual ? "" : "border-b border-slate-200"}>
                    {hg.headers.map((header) => {
                      const canSort = header.column.getCanSort();
                      const sortDir = header.column.getIsSorted();
                      return (
                        <th
                          key={header.id}
                          className={cn(
                            "whitespace-nowrap px-3 py-2 text-left text-caption font-semibold uppercase tracking-wide text-slate-500",
                          )}
                        >
                          {header.isPlaceholder ? null : canSort ? (
                            <button
                              type="button"
                              onClick={header.column.getToggleSortingHandler()}
                              className="inline-flex items-center gap-1 hover:text-slate-900"
                            >
                              {flexRender(header.column.columnDef.header, header.getContext())}
                              {sortDir === "asc" ? (
                                <ArrowUp className="h-3.5 w-3.5" />
                              ) : sortDir === "desc" ? (
                                <ArrowDown className="h-3.5 w-3.5" />
                              ) : (
                                <ChevronsUpDown className="h-3.5 w-3.5 opacity-40" />
                              )}
                            </button>
                          ) : (
                            flexRender(header.column.columnDef.header, header.getContext())
                          )}
                        </th>
                      );
                    })}
                  </tr>
                ))}
              </thead>
              <tbody>
                {enableVirtual ? (
                  <>
                    {paddingTop > 0 ? (
                      <tr aria-hidden="true">
                        <td style={{ height: paddingTop }} colSpan={colSpan} />
                      </tr>
                    ) : null}
                    {virtualItems.map((vi) => {
                      const row = rows[vi.index];
                      return (
                        <tr
                          key={row.id}
                          data-index={vi.index}
                          ref={(node) => rowVirtualizer.measureElement(node)}
                          className={cn(
                            "border-b border-slate-100 last:border-0",
                            onRowClick && "cursor-pointer hover:bg-slate-50",
                            row.getIsSelected() && "bg-brand/5",
                          )}
                          onClick={onRowClick ? () => onRowClick(row.original) : undefined}
                        >
                          {row.getVisibleCells().map((cell) => (
                            <td key={cell.id} className={cn(cellPad, "align-middle text-slate-700")}>
                              {flexRender(cell.column.columnDef.cell, cell.getContext())}
                            </td>
                          ))}
                        </tr>
                      );
                    })}
                    {paddingBottom > 0 ? (
                      <tr aria-hidden="true">
                        <td style={{ height: paddingBottom }} colSpan={colSpan} />
                      </tr>
                    ) : null}
                  </>
                ) : (
                  rows.map((row) => (
                    <tr
                      key={row.id}
                      className={cn(
                        "border-b border-slate-100 last:border-0",
                        onRowClick && "cursor-pointer hover:bg-slate-50",
                        row.getIsSelected() && "bg-brand/5",
                      )}
                      onClick={onRowClick ? () => onRowClick(row.original) : undefined}
                    >
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id} className={cn(cellPad, "align-middle text-slate-700")}>
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 px-3 py-2 text-small text-slate-600">
        <div aria-live="polite">
          {total === 0 ? (
            `No ${noun}`
          ) : (
            <>
              {formatNumber(start)}&ndash;{formatNumber(end)} of {formatNumber(total)} {noun}
              {grandTotal !== undefined && grandTotal !== total ? (
                <span className="text-slate-400"> &middot; filtered from {formatNumber(grandTotal)}</span>
              ) : null}
            </>
          )}
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1.5 text-caption text-slate-500">
            Rows
            <Select
              value={String(pageSize)}
              onChange={(e) => onPageSizeChange(Number(e.target.value))}
              className="h-8 w-[4.5rem]"
              aria-label="Rows per page"
            >
              {[25, 50, 100, 200].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </Select>
          </label>
          <div className="flex items-center gap-1">
            <Button
              variant="secondary"
              size="icon-sm"
              disabled={pageIndex === 0}
              onClick={() => onPageChange(pageIndex - 1)}
              aria-label="Previous page"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="px-1 tabular-nums">
              {pageIndex + 1} / {pageCount}
            </span>
            <Button
              variant="secondary"
              size="icon-sm"
              disabled={pageIndex + 1 >= pageCount}
              onClick={() => onPageChange(pageIndex + 1)}
              aria-label="Next page"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
