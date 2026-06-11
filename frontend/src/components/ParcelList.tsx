import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { type ColumnDef, type SortingState, type RowSelectionState } from "@tanstack/react-table";
import { Search, X, Bookmark, Trash2 } from "lucide-react";
import { listParcels, type ParcelItem } from "@/lib/api";
import { toCsv, downloadCsv } from "@/lib/csv";
import { formatDate } from "@/lib/format";
import {
  DataGrid,
  StageBadge,
  RiskBadge,
  Input,
  Select,
  Button,
  Badge,
  EmptyState,
  useToast,
  STAGE_ORDER,
  stageLabel,
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/components/ui";

type Props = {
  projectId?: string;
  onSelectParcel?: (parcelId: string) => void;
};

type SavedView = {
  name: string;
  q: string;
  stage: string;
  minRisk: string;
  sorting: SortingState;
  pageSize: number;
};

const VIEWS_KEY = "landgrant.parcels.views";

function loadViews(): SavedView[] {
  try {
    return JSON.parse(window.localStorage.getItem(VIEWS_KEY) ?? "[]");
  } catch {
    return [];
  }
}

export function ParcelList({ projectId, onSelectParcel }: Props) {
  const toast = useToast();
  const [searchParams] = useSearchParams();

  const [data, setData] = useState<ParcelItem[]>([]);
  const [total, setTotal] = useState(0);
  const [grandTotal, setGrandTotal] = useState<number | undefined>(undefined);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Initialize filters from deep-link query (e.g. KPI cards -> /workbench?stage=litigation).
  const [q, setQ] = useState(() => searchParams.get("q") ?? "");
  const [debouncedQ, setDebouncedQ] = useState(() => searchParams.get("q") ?? "");
  const [stage, setStage] = useState(() => searchParams.get("stage") ?? "");
  const [minRisk, setMinRisk] = useState(() => searchParams.get("minRisk") ?? "");

  const [sorting, setSorting] = useState<SortingState>([{ id: "updated_at", desc: true }]);
  const [pageIndex, setPageIndex] = useState(0);
  const [pageSize, setPageSize] = useState(50);
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [density, setDensity] = useState<"comfortable" | "compact">("comfortable");

  const [views, setViews] = useState<SavedView[]>(() => loadViews());

  // Debounce search.
  useEffect(() => {
    const id = window.setTimeout(() => setDebouncedQ(q), 300);
    return () => window.clearTimeout(id);
  }, [q]);

  // Reset to first page when filters change.
  useEffect(() => {
    setPageIndex(0);
  }, [debouncedQ, stage, minRisk, projectId, sorting, pageSize]);

  const sortParam = useMemo(() => {
    const s = sorting[0];
    if (!s) return undefined;
    return `${s.desc ? "-" : ""}${s.id}`;
  }, [sorting]);

  // Track the unfiltered grand total once per project for "filtered from X".
  const grandTotalProject = useRef<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listParcels({
        project_id: projectId || undefined,
        stage: stage || undefined,
        min_risk: minRisk && !Number.isNaN(Number(minRisk)) ? Number(minRisk) : undefined,
        q: debouncedQ || undefined,
        sort: sortParam,
        limit: pageSize,
        offset: pageIndex * pageSize,
      });
      setData(res.items);
      setTotal(res.total);

      const hasFilters = Boolean(debouncedQ || stage || minRisk);
      if (!hasFilters) {
        setGrandTotal(res.total);
        grandTotalProject.current = projectId ?? "";
      } else if (grandTotalProject.current !== (projectId ?? "")) {
        setGrandTotal(undefined);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setData([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [projectId, stage, minRisk, debouncedQ, sortParam, pageSize, pageIndex]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const columns = useMemo<ColumnDef<ParcelItem, unknown>[]>(
    () => [
      {
        id: "select",
        enableSorting: false,
        enableHiding: false,
        header: ({ table }) => (
          <input
            type="checkbox"
            aria-label="Select all rows on this page"
            checked={table.getIsAllRowsSelected()}
            ref={(el) => {
              if (el) el.indeterminate = table.getIsSomeRowsSelected();
            }}
            onChange={table.getToggleAllRowsSelectedHandler()}
            className="rounded border-slate-300 text-brand focus:ring-brand"
          />
        ),
        cell: ({ row }) => (
          <input
            type="checkbox"
            aria-label={`Select parcel ${row.original.id}`}
            checked={row.getIsSelected()}
            onChange={row.getToggleSelectedHandler()}
            onClick={(e) => e.stopPropagation()}
            className="rounded border-slate-300 text-brand focus:ring-brand"
          />
        ),
      },
      {
        accessorKey: "id",
        header: "Parcel ID",
        cell: ({ row, getValue }) => (
          <Link
            to={`/parcels/${encodeURIComponent(String(getValue()))}?projectId=${encodeURIComponent(row.original.project_id)}`}
            onClick={(e) => e.stopPropagation()}
            className="font-id font-medium text-brand hover:underline"
          >
            {String(getValue())}
          </Link>
        ),
      },
      {
        accessorKey: "owner",
        header: "Owner",
        enableSorting: false,
        cell: ({ getValue }) => (getValue() ? String(getValue()) : <span className="text-slate-400">&mdash;</span>),
      },
      {
        accessorKey: "county_fips",
        header: "County",
        cell: ({ getValue }) => <span className="font-id">{String(getValue() ?? "")}</span>,
      },
      {
        accessorKey: "stage",
        header: "Stage",
        cell: ({ getValue }) => <StageBadge stage={String(getValue())} />,
      },
      {
        accessorKey: "risk_score",
        header: "Risk",
        cell: ({ getValue }) => <RiskBadge score={Number(getValue() ?? 0)} />,
      },
      {
        accessorKey: "next_deadline_at",
        header: "Next deadline",
        cell: ({ getValue }) =>
          getValue() ? formatDate(String(getValue())) : <span className="text-slate-400">No deadline</span>,
      },
      {
        accessorKey: "updated_at",
        header: "Updated",
        cell: ({ getValue }) =>
          getValue() ? formatDate(String(getValue())) : <span className="text-slate-400">&mdash;</span>,
      },
    ],
    [],
  );

  const activeFilters = [
    debouncedQ && { key: "q", label: `Search: "${debouncedQ}"`, clear: () => setQ("") },
    stage && { key: "stage", label: `Stage: ${stageLabel(stage)}`, clear: () => setStage("") },
    minRisk && { key: "minRisk", label: `Risk >= ${minRisk}`, clear: () => setMinRisk("") },
  ].filter(Boolean) as { key: string; label: string; clear: () => void }[];

  async function exportCsv() {
    try {
      const res = await listParcels({
        project_id: projectId || undefined,
        stage: stage || undefined,
        min_risk: minRisk && !Number.isNaN(Number(minRisk)) ? Number(minRisk) : undefined,
        q: debouncedQ || undefined,
        sort: sortParam,
        limit: 500,
        offset: 0,
      });
      const csv = toCsv(res.items, [
        { header: "Parcel ID", value: (r) => r.id },
        { header: "Owner", value: (r) => r.owner ?? "" },
        { header: "County FIPS", value: (r) => r.county_fips ?? "" },
        { header: "Stage", value: (r) => stageLabel(r.stage) },
        { header: "Risk", value: (r) => r.risk_score },
        { header: "Next deadline", value: (r) => (r.next_deadline_at ? formatDate(r.next_deadline_at) : "") },
        { header: "Updated", value: (r) => (r.updated_at ? formatDate(r.updated_at) : "") },
      ]);
      const stamp = new Date().toISOString().slice(0, 10);
      downloadCsv(`parcels_${stamp}.csv`, csv);
      toast.success("Export ready", `${res.items.length} parcels exported to CSV.`);
    } catch (e) {
      toast.error("Export failed", e instanceof Error ? e.message : String(e));
    }
  }

  function saveCurrentView() {
    const name = window.prompt("Name this view");
    if (!name) return;
    const next = [
      ...views.filter((v) => v.name !== name),
      { name, q: debouncedQ, stage, minRisk, sorting, pageSize },
    ];
    setViews(next);
    window.localStorage.setItem(VIEWS_KEY, JSON.stringify(next));
    toast.success("View saved", `"${name}" is available in your saved views.`);
  }

  function applyView(v: SavedView) {
    setQ(v.q);
    setStage(v.stage);
    setMinRisk(v.minRisk);
    setSorting(v.sorting);
    setPageSize(v.pageSize);
  }

  function deleteView(name: string) {
    const next = views.filter((v) => v.name !== name);
    setViews(next);
    window.localStorage.setItem(VIEWS_KEY, JSON.stringify(next));
  }

  const selectedIds = Object.keys(rowSelection).filter((k) => rowSelection[k]);

  const toolbar = (
    <>
      <div className="relative">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search id, county, owner"
          className="h-8 w-56 pl-8"
          aria-label="Search parcels"
        />
      </div>
      <Select
        value={stage}
        onChange={(e) => setStage(e.target.value)}
        className="h-8 w-40"
        aria-label="Filter by stage"
      >
        <option value="">All stages</option>
        {STAGE_ORDER.map((s) => (
          <option key={s} value={s}>
            {stageLabel(s)}
          </option>
        ))}
      </Select>
      <Input
        type="number"
        value={minRisk}
        onChange={(e) => setMinRisk(e.target.value)}
        placeholder="Min risk"
        className="h-8 w-28"
        aria-label="Minimum risk score"
      />
      {activeFilters.map((f) => (
        <Badge key={f.key} variant="brand" className="gap-1">
          {f.label}
          <button onClick={f.clear} aria-label={`Clear ${f.label}`} className="hover:text-brand-dark">
            <X className="h-3 w-3" />
          </button>
        </Badge>
      ))}

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="sm">
            <Bookmark className="h-4 w-4" /> Views
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start">
          <DropdownMenuLabel>Saved views</DropdownMenuLabel>
          {views.length === 0 ? (
            <p className="px-2.5 py-2 text-caption text-slate-400">None yet</p>
          ) : (
            views.map((v) => (
              <DropdownMenuItem key={v.name} onSelect={() => applyView(v)} className="justify-between">
                <span>{v.name}</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteView(v.name);
                  }}
                  className="text-slate-400 hover:text-danger"
                  aria-label={`Delete ${v.name}`}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </DropdownMenuItem>
            ))
          )}
          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={saveCurrentView}>Save current view...</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </>
  );

  return (
    <div className="space-y-2">
      {error ? (
        <div className="rounded-control border border-danger-border bg-danger-bg px-3 py-2 text-small text-danger-fg">
          {error}
        </div>
      ) : null}
      <DataGrid<ParcelItem>
        data={data}
        columns={columns}
        rowId={(r) => r.id}
        total={total}
        grandTotal={grandTotal}
        loading={loading}
        noun="parcels"
        sorting={sorting}
        onSortingChange={setSorting}
        pageIndex={pageIndex}
        pageSize={pageSize}
        onPageChange={setPageIndex}
        onPageSizeChange={setPageSize}
        rowSelection={rowSelection}
        onRowSelectionChange={setRowSelection}
        density={density}
        onDensityChange={setDensity}
        onRowClick={onSelectParcel ? (r) => onSelectParcel(r.id) : undefined}
        onExport={exportCsv}
        toolbar={toolbar}
        bulkActions={
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              const rows = data.filter((r) => selectedIds.includes(r.id));
              const csv = toCsv(rows, [
                { header: "Parcel ID", value: (r) => r.id },
                { header: "Stage", value: (r) => stageLabel(r.stage) },
                { header: "Risk", value: (r) => r.risk_score },
              ]);
              downloadCsv(`parcels_selected_${new Date().toISOString().slice(0, 10)}.csv`, csv);
              toast.success("Exported selection", `${rows.length} parcels exported.`);
            }}
          >
            Export selected
          </Button>
        }
        emptyState={
          <EmptyState
            title={activeFilters.length ? "No parcels match these filters" : "No parcels yet"}
            message={
              activeFilters.length
                ? "Try clearing a filter or broadening your search."
                : "Create a parcel case from intake to populate this grid."
            }
          />
        }
      />
    </div>
  );
}
