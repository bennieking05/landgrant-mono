import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { type ColumnDef, type SortingState } from "@tanstack/react-table";
import { CalendarDays, ChevronLeft, ChevronRight, LayoutList } from "lucide-react";
import {
  listDeadlines,
  createDeadline,
  getDeadlinesIcal,
  deriveDeadlines,
  type DeadlineItem,
  type DerivedDeadlineItem,
} from "@/lib/api";
import { formatDate } from "@/lib/format";
import { Button, DataGrid, EmptyState, Input, Select, useToast } from "@/components/ui";
import { cn } from "@/lib/cn";

type Props = {
  projectId: string;
};

type ViewMode = "list" | "calendar";

// Indiana anchor events for the derive form
const IN_ANCHOR_EVENTS = [
  { key: "offer_served", label: "Offer Served", citation: "IC 32-24-1-5" },
  { key: "complaint_filed", label: "Complaint Filed", citation: "IC 32-24-1-5" },
  { key: "notice_served", label: "Notice Served", citation: "IC 32-24-1-6" },
  { key: "appraisers_report_mailed", label: "Appraisers Report Mailed", citation: "IC 32-24-1-11" },
  { key: "trial_date_set", label: "Trial Date Set", citation: "IC 32-24-1-12" },
];

const TX_ANCHOR_EVENTS = [
  { key: "offer_served", label: "Offer Served", citation: "Tex. Prop. Code Ch. 21" },
  { key: "final_offer_served", label: "Final Offer Served", citation: "Tex. Prop. Code §21.0113" },
  { key: "commissioners_award", label: "Commissioners Award", citation: "Tex. Prop. Code Ch. 21" },
];

function daysUntil(isoDate: string): number {
  const due = new Date(isoDate);
  const now = new Date();
  const msPerDay = 86_400_000;
  const dayStart = (t: Date) => new Date(t.getFullYear(), t.getMonth(), t.getDate()).getTime();
  return Math.round((dayStart(due) - dayStart(now)) / msPerDay);
}

function urgencyClass(days: number): string {
  if (days <= 3) return "text-rose-600 bg-rose-50";
  if (days <= 7) return "text-amber-600 bg-amber-50";
  return "text-emerald-600 bg-emerald-50";
}

function startOfCalendarGrid(monthStart: Date): Date {
  const d = new Date(monthStart.getFullYear(), monthStart.getMonth(), 1);
  const dow = d.getDay(); // 0 Sun
  d.setDate(d.getDate() - dow);
  return d;
}

function DeadlineCalendar({
  deadlines,
  month,
  onPrevMonth,
  onNextMonth,
  projectId,
}: {
  deadlines: DeadlineItem[];
  month: Date;
  onPrevMonth: () => void;
  onNextMonth: () => void;
  projectId: string;
}) {
  const monthStart = new Date(month.getFullYear(), month.getMonth(), 1);
  const gridStart = startOfCalendarGrid(monthStart);
  const labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  // Bucket deadlines by calendar day. This is a cheap derivation over a small
  // list rebuilt only while the calendar view is mounted, so it's computed
  // inline rather than memoized.
  const byDay = new Map<string, DeadlineItem[]>();
  for (const d of deadlines) {
    const x = new Date(d.due_at);
    if (Number.isNaN(x.getTime())) continue;
    const key = `${x.getFullYear()}-${x.getMonth()}-${x.getDate()}`;
    const arr = byDay.get(key) ?? [];
    arr.push(d);
    byDay.set(key, arr);
  }

  const cells: { date: Date; inMonth: boolean }[] = [];
  for (let i = 0; i < 42; i++) {
    const d = new Date(gridStart);
    d.setDate(gridStart.getDate() + i);
    cells.push({
      date: d,
      inMonth: d.getMonth() === monthStart.getMonth(),
    });
  }

  const title = monthStart.toLocaleDateString("en-US", { month: "long", year: "numeric" });

  return (
    <div className="rounded-card border border-slate-200 bg-white p-4 shadow-card">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h4 className="text-sm font-semibold text-slate-900">{title}</h4>
        <div className="flex items-center gap-1">
          <Button type="button" variant="secondary" size="icon-sm" onClick={onPrevMonth} aria-label="Previous month">
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button type="button" variant="secondary" size="icon-sm" onClick={onNextMonth} aria-label="Next month">
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
      <div className="grid grid-cols-7 gap-px rounded-control bg-slate-200 text-caption">
        {labels.map((lb) => (
          <div key={lb} className="bg-slate-50 px-1 py-2 text-center font-medium text-slate-500">
            {lb}
          </div>
        ))}
        {cells.map(({ date, inMonth }) => {
          const key = `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`;
          const items = byDay.get(key) ?? [];
          const today = new Date();
          const isToday =
            date.getDate() === today.getDate() &&
            date.getMonth() === today.getMonth() &&
            date.getFullYear() === today.getFullYear();
          return (
            <div
              key={key}
              className={cn(
                "min-h-[5.5rem] bg-white p-1",
                !inMonth && "bg-slate-50/80 text-slate-400",
                isToday && "ring-1 ring-inset ring-brand",
              )}
            >
              <div className="text-right text-caption font-medium tabular-nums">{date.getDate()}</div>
              <ul className="mt-1 space-y-0.5">
                {items.slice(0, 3).map((d) => (
                  <li key={d.id}>
                    {d.parcel_id ? (
                      <Link
                        to={`/parcels/${encodeURIComponent(d.parcel_id)}?projectId=${encodeURIComponent(projectId)}`}
                        className="block truncate rounded px-0.5 text-caption text-brand hover:underline"
                        title={d.title}
                      >
                        {d.title}
                      </Link>
                    ) : (
                      <span className="block truncate text-caption text-slate-700" title={d.title}>
                        {d.title}
                      </span>
                    )}
                  </li>
                ))}
                {items.length > 3 ? (
                  <li className="text-caption text-slate-400">+{items.length - 3} more</li>
                ) : null}
              </ul>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function DeadlineManager({ projectId }: Props) {
  const toast = useToast();
  const [deadlines, setDeadlines] = useState<DeadlineItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState<ViewMode>("list");
  const [calendarMonth, setCalendarMonth] = useState(() => new Date());

  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [parcelId, setParcelId] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const [showDeriveForm, setShowDeriveForm] = useState(false);
  const [deriveJurisdiction, setDeriveJurisdiction] = useState("IN");
  const [deriveParcelId, setDeriveParcelId] = useState("");
  const [anchorEvents, setAnchorEvents] = useState<Record<string, string>>({});
  const [deriving, setDeriving] = useState(false);
  const [deriveResult, setDeriveResult] = useState<DerivedDeadlineItem[] | null>(null);

  const [sorting, setSorting] = useState<SortingState>([{ id: "due_at", desc: false }]);
  const [pageIndex, setPageIndex] = useState(0);
  const [gridPageSize, setGridPageSize] = useState(50);

  const anchorFields = useMemo(
    () => (deriveJurisdiction === "TX" ? TX_ANCHOR_EVENTS : IN_ANCHOR_EVENTS),
    [deriveJurisdiction],
  );

  useEffect(() => {
    setAnchorEvents({});
  }, [deriveJurisdiction]);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listDeadlines(projectId);
      setDeadlines(res.items);
    } catch (e) {
      setError(String(e));
      setDeadlines(null);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    setPageIndex(0);
  }, [sorting]);

  const orderedDeadlines = useMemo(() => {
    const base = [...(deadlines ?? [])];
    const s = sorting[0];
    if (!s) {
      return base.sort((a, b) => new Date(a.due_at).getTime() - new Date(b.due_at).getTime());
    }
    const dir = s.desc ? -1 : 1;
    const id = s.id;
    base.sort((a, b) => {
      let cmp = 0;
      if (id === "due_at") {
        cmp = new Date(a.due_at).getTime() - new Date(b.due_at).getTime();
      } else if (id === "title") {
        cmp = a.title.localeCompare(b.title);
      } else if (id === "parcel_id") {
        cmp = (a.parcel_id ?? "").localeCompare(b.parcel_id ?? "");
      } else if (id === "updated_at") {
        cmp = (a.id ?? "").localeCompare(b.id ?? "");
      }
      return cmp * dir;
    });
    return base;
  }, [deadlines, sorting]);

  const total = orderedDeadlines.length;
  const pageRows = useMemo(
    () => orderedDeadlines.slice(pageIndex * gridPageSize, (pageIndex + 1) * gridPageSize),
    [orderedDeadlines, pageIndex, gridPageSize],
  );

  const columns = useMemo<ColumnDef<DeadlineItem, unknown>[]>(
    () => [
      {
        accessorKey: "title",
        header: "Title",
        cell: ({ getValue }) => <span className="font-medium text-slate-900">{String(getValue())}</span>,
      },
      {
        accessorKey: "parcel_id",
        header: "Parcel",
        cell: ({ getValue }) => {
          const pid = getValue() as string | undefined;
          if (!pid) return <span className="text-slate-400">&mdash;</span>;
          return (
            <Link
              to={`/parcels/${encodeURIComponent(pid)}?projectId=${encodeURIComponent(projectId)}`}
              className="font-id text-brand hover:underline"
              onClick={(e) => e.stopPropagation()}
            >
              {pid}
            </Link>
          );
        },
      },
      {
        accessorKey: "due_at",
        id: "due_at",
        header: "Due",
        cell: ({ row }) => {
          const d = row.original;
          const days = daysUntil(d.due_at);
          return (
            <div className="text-right">
              <p className="text-small text-slate-800">{formatDate(d.due_at)}</p>
              <span
                className={`mt-1 inline-block rounded-full px-2 py-0.5 text-caption font-medium ${urgencyClass(days)}`}
              >
                {days <= 0 ? "Overdue" : `${days} days`}
              </span>
            </div>
          );
        },
      },
      {
        accessorKey: "timezone",
        header: "TZ",
        enableSorting: false,
        cell: ({ getValue }) => <span className="text-caption text-slate-500">{String(getValue())}</span>,
      },
      {
        accessorKey: "deadline_type",
        header: "Type",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-caption text-slate-600">
            {row.original.deadline_type ?? row.original.source_kind ?? "—"}
          </span>
        ),
      },
    ],
    [projectId],
  );

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title || !dueAt) return;

    setSubmitting(true);
    try {
      await createDeadline({
        project_id: projectId,
        title,
        due_at: new Date(dueAt).toISOString(),
        parcel_id: parcelId || undefined,
        timezone: "America/Chicago",
      });
      setTitle("");
      setDueAt("");
      setParcelId("");
      setShowForm(false);
      await refresh();
      toast.success("Deadline saved", "The list has been refreshed.");
    } catch (e) {
      setError(String(e));
      toast.error("Save failed", String(e));
    } finally {
      setSubmitting(false);
    }
  }

  async function downloadIcal() {
    try {
      const res = await getDeadlinesIcal(projectId);
      const blob = new Blob([res.ical], { type: "text/calendar" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${projectId}-deadlines.ics`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("iCal export", "Download started.");
    } catch (e) {
      setError(String(e));
      toast.error("Export failed", String(e));
    }
  }

  async function handleDerive(e: React.FormEvent) {
    e.preventDefault();
    const filteredAnchors: Record<string, string> = {};
    for (const [key, value] of Object.entries(anchorEvents)) {
      if (value) {
        filteredAnchors[key] = value;
      }
    }

    if (Object.keys(filteredAnchors).length === 0) {
      setError("Please enter at least one anchor date");
      return;
    }

    setDeriving(true);
    setError(null);
    setDeriveResult(null);

    try {
      const res = await deriveDeadlines({
        project_id: projectId,
        parcel_id: deriveParcelId || undefined,
        jurisdiction: deriveJurisdiction,
        anchor_events: filteredAnchors,
        persist: true,
        timezone: "America/Indiana/Indianapolis",
      });

      setDeriveResult(res.deadlines);

      if (res.errors.length > 0) {
        setError(res.errors.join("; "));
      }

      await refresh();
      if (res.errors.length === 0) {
        toast.success("Deadlines generated", `${res.deadlines.length} deadline(s) saved.`);
      }
    } catch (e) {
      setError(String(e));
      toast.error("Derive failed", String(e));
    } finally {
      setDeriving(false);
    }
  }

  function updateAnchorEvent(key: string, value: string) {
    setAnchorEvents((prev) => ({ ...prev, [key]: value }));
  }

  function resetDeriveForm() {
    setShowDeriveForm(false);
    setAnchorEvents({});
    setDeriveParcelId("");
    setDeriveResult(null);
  }


  return (
    <div className="rounded-card border border-slate-200 bg-white p-6 shadow-card">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">Deadlines</h3>
          <p className="text-sm text-slate-500">Project: {projectId}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <div className="flex items-center gap-1 rounded-control border border-slate-200 p-0.5">
            <Button
              type="button"
              variant={view === "list" ? "secondary" : "ghost"}
              size="sm"
              className="h-7"
              onClick={() => setView("list")}
              aria-pressed={view === "list"}
            >
              <LayoutList className="mr-1 h-3.5 w-3.5" /> List
            </Button>
            <Button
              type="button"
              variant={view === "calendar" ? "secondary" : "ghost"}
              size="sm"
              className="h-7"
              onClick={() => setView("calendar")}
              aria-pressed={view === "calendar"}
            >
              <CalendarDays className="mr-1 h-3.5 w-3.5" /> Calendar
            </Button>
          </div>
          <Button type="button" variant="ghost" size="sm" onClick={() => void refresh()} disabled={loading}>
            Refresh
          </Button>
          <Button type="button" variant="ghost" size="sm" onClick={() => void downloadIcal()}>
            Export iCal
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => {
              setShowDeriveForm(!showDeriveForm);
              if (showForm) setShowForm(false);
            }}
          >
            {showDeriveForm ? "Cancel" : "Generate statutory"}
          </Button>
          <Button
            type="button"
            variant="primary"
            size="sm"
            onClick={() => {
              setShowForm(!showForm);
              if (showDeriveForm) setShowDeriveForm(false);
            }}
          >
            {showForm ? "Cancel" : "+ Add"}
          </Button>
        </div>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="mb-4 space-y-3 rounded-control border border-slate-200 bg-slate-50 p-4">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <Input type="text" placeholder="Deadline title" value={title} onChange={(e) => setTitle(e.target.value)} required />
            <Input type="datetime-local" value={dueAt} onChange={(e) => setDueAt(e.target.value)} required />
          </div>
          <div className="flex flex-wrap gap-3">
            <Input
              type="text"
              placeholder="Parcel ID (optional)"
              value={parcelId}
              onChange={(e) => setParcelId(e.target.value)}
              className="min-w-[12rem] flex-1"
            />
            <Button type="submit" disabled={submitting}>
              {submitting ? "Saving…" : "Save"}
            </Button>
          </div>
        </form>
      )}

      {showDeriveForm && (
        <form onSubmit={handleDerive} className="mb-4 space-y-4 rounded-control border border-slate-200 bg-slate-50 p-4">
          <div className="flex items-center justify-between">
            <h4 className="font-medium text-slate-900">Generate statutory deadlines</h4>
            <span className="rounded-full bg-slate-200 px-2 py-0.5 text-caption text-slate-700">
              {deriveJurisdiction === "IN" ? "Indiana" : deriveJurisdiction}
            </span>
          </div>
          <p className="text-caption text-slate-600">
            Enter key procedural dates to calculate statutory deadlines for{" "}
            {deriveJurisdiction === "IN" ? "Indiana (IC Title 32 Art. 24)" : "Texas (Prop. Code Ch. 21)"}.
          </p>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-caption text-slate-600">Jurisdiction</label>
              <Select value={deriveJurisdiction} onChange={(e) => setDeriveJurisdiction(e.target.value)} className="w-full">
                <option value="IN">Indiana (IN)</option>
                <option value="TX">Texas (TX)</option>
              </Select>
            </div>
            <div>
              <label className="mb-1 block text-caption text-slate-600">Parcel ID (optional)</label>
              <Input
                type="text"
                placeholder="Parcel ID"
                value={deriveParcelId}
                onChange={(e) => setDeriveParcelId(e.target.value)}
              />
            </div>
          </div>

          <div className="border-t border-slate-200 pt-3">
            <p className="mb-2 text-caption font-medium text-slate-700">Anchor events (enter dates as they occur)</p>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {anchorFields.map((anchor) => (
                <div key={anchor.key}>
                  <label className="mb-1 block text-caption text-slate-600">
                    {anchor.label}
                    <span className="ml-1 text-slate-400">({anchor.citation})</span>
                  </label>
                  <Input
                    type="date"
                    value={anchorEvents[anchor.key] || ""}
                    onChange={(e) => updateAnchorEvent(anchor.key, e.target.value)}
                  />
                </div>
              ))}
            </div>
          </div>

          <div className="flex flex-wrap gap-3 pt-2">
            <Button type="button" variant="secondary" onClick={resetDeriveForm}>
              Cancel
            </Button>
            <Button type="submit" className="flex-1" disabled={deriving}>
              {deriving ? "Generating…" : "Generate & save deadlines"}
            </Button>
          </div>

          {deriveResult && deriveResult.length > 0 && (
            <div className="mt-4 border-t border-slate-200 pt-3">
              <p className="mb-2 text-caption font-medium text-emerald-800">Generated {deriveResult.length} deadline(s)</p>
              <ul className="max-h-32 space-y-1 overflow-y-auto text-caption text-slate-600">
                {deriveResult.map((d) => (
                  <li key={d.id} className="flex justify-between gap-2">
                    <span>{d.title}</span>
                    <span className="shrink-0 text-slate-500">
                      {d.due_date} · {d.citation}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </form>
      )}

      {error ? <p className="mb-3 text-small text-danger-fg">{error}</p> : null}

      {view === "calendar" ? (
        <DeadlineCalendar
          deadlines={deadlines ?? []}
          month={calendarMonth}
          projectId={projectId}
          onPrevMonth={() =>
            setCalendarMonth((m) => new Date(m.getFullYear(), m.getMonth() - 1, 1))
          }
          onNextMonth={() =>
            setCalendarMonth((m) => new Date(m.getFullYear(), m.getMonth() + 1, 1))
          }
        />
      ) : (
        <DataGrid<DeadlineItem>
          data={pageRows}
          columns={columns}
          rowId={(r) => r.id}
          total={total}
          loading={loading}
          noun="deadlines"
          sorting={sorting}
          onSortingChange={setSorting}
          pageIndex={pageIndex}
          pageSize={gridPageSize}
          onPageChange={setPageIndex}
          onPageSizeChange={(n) => {
            setGridPageSize(n);
            setPageIndex(0);
          }}
          emptyState={<EmptyState message="No deadlines for this project yet." />}
        />
      )}
    </div>
  );
}
