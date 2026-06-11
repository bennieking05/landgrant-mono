import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  type ColumnDef,
  type SortingState,
  type RowSelectionState,
  type VisibilityState,
} from "@tanstack/react-table";
import { Search, X, Bookmark, Trash2 } from "lucide-react";
import {
  listParcels,
  exportParcelsCsv,
  listParcelGridViews,
  createParcelGridView,
  deleteParcelGridView,
  listFirmAssignees,
  type FirmAssignee,
  type ParcelGridSavedView,
  type ParcelItem,
} from "@/lib/api";
import { useAppContext } from "@/context";
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

const VIEWS_KEY = "landgrant.parcels.views";

const OFFER_STATUS_OPTIONS = [
  "",
  "draft",
  "sent",
  "received",
  "accepted",
  "rejected",
  "expired",
  "superseded",
] as const;

type LegacySavedView = {
  name: string;
  q: string;
  stage: string;
  minRisk: string;
  sorting: SortingState;
  pageSize: number;
};

function loadLegacyViews(): LegacySavedView[] {
  try {
    return JSON.parse(window.localStorage.getItem(VIEWS_KEY) ?? "[]");
  } catch {
    return [];
  }
}

function NextDeadlineCell({ iso }: { iso: string }) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) {
    return <span className="text-slate-400">&mdash;</span>;
  }
  const now = new Date();
  const msPerDay = 86_400_000;
  const dayStart = (t: Date) => new Date(t.getFullYear(), t.getMonth(), t.getDate()).getTime();
  const days = Math.round((dayStart(d) - dayStart(now)) / msPerDay);
  const urgent = days >= 0 && days <= 7;
  const overdue = days < 0;
  const rel =
    days < 0
      ? `${Math.abs(days)} day${Math.abs(days) === 1 ? "" : "s"} overdue`
      : days === 0
        ? "Due today"
        : days === 1
          ? "Due tomorrow"
          : `Due in ${days} days`;
  return (
    <span
      title={`${formatDate(iso)} (${rel})`}
      className={urgent || overdue ? "font-medium text-danger-fg" : undefined}
    >
      {formatDate(iso)}
      <span className="ml-1 text-caption text-slate-500">({rel})</span>
    </span>
  );
}

export function ParcelList({ projectId, onSelectParcel }: Props) {
  const toast = useToast();
  const navigate = useNavigate();
  const { persona } = useAppContext();
  const [searchParams] = useSearchParams();

  const [data, setData] = useState<ParcelItem[]>([]);
  const [total, setTotal] = useState(0);
  const [grandTotal, setGrandTotal] = useState<number | undefined>(undefined);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [q, setQ] = useState(() => searchParams.get("q") ?? "");
  const [debouncedQ, setDebouncedQ] = useState(() => searchParams.get("q") ?? "");
  const [stage, setStage] = useState(() => searchParams.get("stage") ?? "");
  const [minRisk, setMinRisk] = useState(() => searchParams.get("minRisk") ?? "");
  const [deadlineBefore, setDeadlineBefore] = useState(() => searchParams.get("deadline_before") ?? "");
  const [county, setCounty] = useState(() => searchParams.get("county") ?? "");
  const [offerStatus, setOfferStatus] = useState(() => searchParams.get("offer_status") ?? "");
  const [assignedTo, setAssignedTo] = useState(() => searchParams.get("assigned_to") ?? "");
  const [assignees, setAssignees] = useState<FirmAssignee[]>([]);

  const [sorting, setSorting] = useState<SortingState>([{ id: "updated_at", desc: true }]);
  const [pageIndex, setPageIndex] = useState(0);
  const [pageSize, setPageSize] = useState(50);
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [density, setDensity] = useState<"comfortable" | "compact">("comfortable");
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({
    project_name: true,
    alignment_label: false,
    segment_label: false,
    offer_status: true,
    assignee_name: true,
  });

  const [savedViews, setSavedViews] = useState<ParcelGridSavedView[]>([]);
  const viewsLoaded = useRef(false);

  useEffect(() => {
    const id = window.setTimeout(() => setDebouncedQ(q), 300);
    return () => window.clearTimeout(id);
  }, [q]);

  useEffect(() => {
    setPageIndex(0);
  }, [debouncedQ, stage, minRisk, deadlineBefore, county, offerStatus, assignedTo, projectId, sorting, pageSize]);

  useEffect(() => {
    if (persona === "landowner") {
      setAssignees([]);
      return;
    }
    let canceled = false;
    void (async () => {
      try {
        const res = await listFirmAssignees();
        if (!canceled) setAssignees(res.items);
      } catch {
        if (!canceled) setAssignees([]);
      }
    })();
    return () => {
      canceled = true;
    };
  }, [persona]);

  const sortParam = useMemo(() => {
    const s = sorting[0];
    if (!s) return undefined;
    return `${s.desc ? "-" : ""}${s.id}`;
  }, [sorting]);

  const grandTotalProject = useRef<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listParcels({
        project_id: projectId || undefined,
        stage: stage || undefined,
        min_risk: minRisk && !Number.isNaN(Number(minRisk)) ? Number(minRisk) : undefined,
        deadline_before: deadlineBefore || undefined,
        q: debouncedQ || undefined,
        county: county.trim() || undefined,
        offer_status: offerStatus || undefined,
        assigned_to: assignedTo || undefined,
        sort: sortParam,
        limit: pageSize,
        offset: pageIndex * pageSize,
      });
      setData(res.items);
      setTotal(res.total);

      const hasFilters = Boolean(
        debouncedQ ||
          stage ||
          minRisk ||
          deadlineBefore ||
          county.trim() ||
          offerStatus ||
          assignedTo,
      );
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
  }, [
    projectId,
    stage,
    minRisk,
    deadlineBefore,
    debouncedQ,
    county,
    offerStatus,
    assignedTo,
    sortParam,
    pageSize,
    pageIndex,
  ]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (viewsLoaded.current) return;
    viewsLoaded.current = true;
    let canceled = false;
    (async () => {
      try {
        const first = await listParcelGridViews();
        if (canceled) return;
        if (first.items.length === 0) {
          const legacy = loadLegacyViews();
          for (const v of legacy) {
            try {
              await createParcelGridView({
                name: v.name,
                payload: {
                  q: v.q ?? "",
                  stage: v.stage ?? "",
                  minRisk: v.minRisk ?? "",
                  deadlineBefore: "",
                  county: "",
                  offerStatus: "",
                  assignedTo: "",
                  sorting: v.sorting ?? [{ id: "updated_at", desc: true }],
                  pageSize: v.pageSize ?? 50,
                },
              });
            } catch {
              /** duplicate name or offline */
            }
          }
          if (legacy.length) window.localStorage.removeItem(VIEWS_KEY);
          const second = await listParcelGridViews();
          if (!canceled) setSavedViews(second.items);
          return;
        }
        setSavedViews(first.items);
      } catch {
        if (!canceled) setSavedViews([]);
      }
    })();
    return () => {
      canceled = true;
    };
  }, []);

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
        id: "project_name",
        accessorKey: "project_name",
        header: "Project",
        enableSorting: false,
        cell: ({ row }) =>
          row.original.project_name ? (
            String(row.original.project_name)
          ) : (
            <span className="text-slate-400">&mdash;</span>
          ),
      },
      {
        accessorKey: "owner",
        header: "Owner",
        enableSorting: false,
        cell: ({ getValue }) => (getValue() ? String(getValue()) : <span className="text-slate-400">&mdash;</span>),
      },
      {
        id: "alignment_label",
        accessorKey: "alignment_label",
        header: "Alignment",
        enableSorting: false,
        cell: ({ row }) =>
          row.original.alignment_label ? (
            String(row.original.alignment_label)
          ) : (
            <span className="text-slate-400">&mdash;</span>
          ),
      },
      {
        id: "segment_label",
        accessorKey: "segment_label",
        header: "Segment",
        enableSorting: false,
        cell: ({ row }) =>
          row.original.segment_label ? (
            <span className="font-id">{String(row.original.segment_label)}</span>
          ) : (
            <span className="text-slate-400">&mdash;</span>
          ),
      },
      {
        id: "county",
        header: "County",
        enableSorting: false,
        cell: ({ row }) => {
          const r = row.original;
          const label = [r.county, r.parcel_state].filter(Boolean).join(", ") || r.county_fips || "";
          return label ? (
            <span>
              {label}
              {r.county_fips ? (
                <span className="ml-1 text-caption text-slate-400">({r.county_fips})</span>
              ) : null}
            </span>
          ) : (
            <span className="text-slate-400">&mdash;</span>
          );
        },
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
        id: "offer_status",
        accessorKey: "offer_status",
        header: "Offer status",
        enableSorting: false,
        cell: ({ row }) =>
          row.original.offer_status ? (
            <span className="text-caption uppercase text-slate-600">{row.original.offer_status}</span>
          ) : (
            <span className="text-slate-400">&mdash;</span>
          ),
      },
      {
        id: "assignee_name",
        accessorKey: "assignee_name",
        header: "Assignee",
        enableSorting: false,
        cell: ({ row }) =>
          row.original.assignee_name ? (
            String(row.original.assignee_name)
          ) : (
            <span className="text-slate-400">&mdash;</span>
          ),
      },
      {
        accessorKey: "next_deadline_at",
        header: "Next deadline",
        enableSorting: true,
        cell: ({ getValue }) =>
          getValue() ? (
            <NextDeadlineCell iso={String(getValue())} />
          ) : (
            <span className="text-slate-400">No deadline</span>
          ),
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
    deadlineBefore && {
      key: "deadline_before",
      label: `Deadline before ${formatDate(deadlineBefore)}`,
      clear: () => setDeadlineBefore(""),
    },
    county.trim() && {
      key: "county",
      label: `County contains "${county.trim()}"`,
      clear: () => setCounty(""),
    },
    offerStatus && {
      key: "offer_status",
      label: `Offer status: ${offerStatus}`,
      clear: () => setOfferStatus(""),
    },
    assignedTo && {
      key: "assigned_to",
      label: `Assignee: ${assignees.find((a) => a.id === assignedTo)?.full_name || assignees.find((a) => a.id === assignedTo)?.email || assignedTo}`,
      clear: () => setAssignedTo(""),
    },
  ].filter(Boolean) as { key: string; label: string; clear: () => void }[];

  async function exportCsv() {
    try {
      const blob = await exportParcelsCsv({
        project_id: projectId || undefined,
        stage: stage || undefined,
        min_risk: minRisk && !Number.isNaN(Number(minRisk)) ? Number(minRisk) : undefined,
        deadline_before: deadlineBefore || undefined,
        q: debouncedQ || undefined,
        county: county.trim() || undefined,
        offer_status: offerStatus || undefined,
        assigned_to: assignedTo || undefined,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `parcels_export_${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Export ready", "Server-generated CSV download started.");
    } catch (e) {
      toast.error("Export failed", e instanceof Error ? e.message : String(e));
    }
  }

  function buildViewPayload(): Record<string, unknown> {
    return {
      q: debouncedQ,
      stage,
      minRisk,
      deadlineBefore,
      county,
      offerStatus,
      assignedTo,
      sorting,
      pageSize,
      columnVisibility,
    };
  }

  async function saveCurrentView() {
    const name = window.prompt("Name this view");
    if (!name?.trim()) return;
    try {
      await createParcelGridView({ name: name.trim(), payload: buildViewPayload() });
      const res = await listParcelGridViews();
      setSavedViews(res.items);
      toast.success("View saved", `"${name.trim()}" is synced to your account.`);
    } catch (e) {
      toast.error("Could not save view", e instanceof Error ? e.message : String(e));
    }
  }

  function applyServerView(v: ParcelGridSavedView) {
    const p = v.payload;
    setQ(String(p.q ?? ""));
    setStage(String(p.stage ?? ""));
    setMinRisk(String(p.minRisk ?? ""));
    setDeadlineBefore(String(p.deadlineBefore ?? ""));
    setCounty(String(p.county ?? ""));
    setOfferStatus(String(p.offerStatus ?? ""));
    setAssignedTo(String(p.assignedTo ?? ""));
    const rawSort = p.sorting;
    if (Array.isArray(rawSort) && rawSort.length) setSorting(rawSort as SortingState);
    if (typeof p.pageSize === "number" && p.pageSize > 0) setPageSize(p.pageSize);
    const cv = p.columnVisibility;
    if (cv && typeof cv === "object" && !Array.isArray(cv)) {
      setColumnVisibility((prev) => ({ ...prev, ...(cv as VisibilityState) }));
    }
  }

  async function removeServerView(id: string, name: string) {
    try {
      await deleteParcelGridView(id);
      setSavedViews((prev) => prev.filter((v) => v.id !== id));
      toast.success("View removed", `"${name}" was deleted.`);
    } catch (e) {
      toast.error("Could not delete view", e instanceof Error ? e.message : String(e));
    }
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
        value={county}
        onChange={(e) => setCounty(e.target.value)}
        placeholder="County"
        className="h-8 w-32"
        aria-label="Filter by county name"
      />
      <Select
        value={offerStatus}
        onChange={(e) => setOfferStatus(e.target.value)}
        className="h-8 w-36"
        aria-label="Filter by offer status"
      >
        {OFFER_STATUS_OPTIONS.map((s) => (
          <option key={s || "any"} value={s}>
            {s ? s.replaceAll("_", " ") : "Any offer status"}
          </option>
        ))}
      </Select>
      {persona !== "landowner" ? (
        <Select
          value={assignedTo}
          onChange={(e) => setAssignedTo(e.target.value)}
          className="h-8 min-w-[10rem] max-w-[14rem]"
          aria-label="Filter by assignee"
        >
          <option value="">Any assignee</option>
          {assignees.map((a) => (
            <option key={a.id} value={a.id}>
              {a.full_name?.trim() || a.email}
            </option>
          ))}
        </Select>
      ) : null}
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
          <button type="button" onClick={f.clear} aria-label={`Clear ${f.label}`} className="hover:text-brand-dark">
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
          {savedViews.length === 0 ? (
            <p className="px-2.5 py-2 text-caption text-slate-400">None yet</p>
          ) : (
            savedViews.map((v) => (
              <DropdownMenuItem key={v.id} onSelect={() => applyServerView(v)} className="justify-between">
                <span>{v.name}</span>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    void removeServerView(v.id, v.name);
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
          <DropdownMenuItem onSelect={() => void saveCurrentView()}>Save current view...</DropdownMenuItem>
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
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
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
            action={
              activeFilters.length
                ? undefined
                : {
                    label: "Go to intake",
                    onClick: () => navigate("/intake"),
                  }
            }
          />
        }
      />
    </div>
  );
}
