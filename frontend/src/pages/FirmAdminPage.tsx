import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { type ColumnDef, type SortingState } from "@tanstack/react-table";
import {
  getFirmDashboard,
  getFirmCases,
  getFirmActivity,
  type FirmMetrics,
  type FirmCaseItem,
  type FirmActivityItem,
} from "@/lib/api";
import { useTranslation } from "react-i18next";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { formatDate } from "@/lib/format";
import { Alert, DataGrid, EmptyState, StageBadge } from "@/components/ui";

const DEFAULT_PAGE = 50;

export function FirmAdminPage() {
  const { t } = useTranslation();
  useDocumentTitle("Firm admin");
  const [metrics, setMetrics] = useState<FirmMetrics | null>(null);
  const [cases, setCases] = useState<FirmCaseItem[]>([]);
  const [casesTotal, setCasesTotal] = useState(0);
  const [activities, setActivities] = useState<FirmActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [statusFilter, setStatusFilter] = useState<string>("");
  const [litigationFilter, setLitigationFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [pageIndex, setPageIndex] = useState(0);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE);
  const [sorting, setSorting] = useState<SortingState>([{ id: "updated_at", desc: true }]);

  useEffect(() => {
    setPageIndex(0);
  }, [statusFilter, litigationFilter, searchQuery, pageSize]);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const offset = pageIndex * pageSize;
      const [metricsData, casesData, activityData] = await Promise.all([
        getFirmDashboard(),
        getFirmCases({
          status: statusFilter || undefined,
          litigation_status: litigationFilter || undefined,
          search: searchQuery || undefined,
          limit: pageSize,
          offset,
        }),
        getFirmActivity(7, 20),
      ]);
      setMetrics(metricsData);
      setCases(casesData.cases);
      setCasesTotal(casesData.total);
      setActivities(activityData.activities);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, litigationFilter, searchQuery, pageIndex, pageSize]);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  const sortedCases = useMemo(() => {
    const copy = [...cases];
    const s = sorting[0];
    if (!s) return copy;
    const dir = s.desc ? -1 : 1;
    const id = s.id;
    copy.sort((a, b) => {
      let cmp = 0;
      if (id === "parcel_id") cmp = a.parcel_id.localeCompare(b.parcel_id);
      else if (id === "project_name")
        cmp = (a.project_name ?? a.project_id).localeCompare(b.project_name ?? b.project_id);
      else if (id === "parcel_stage") cmp = a.parcel_stage.localeCompare(b.parcel_stage);
      else if (id === "litigation_status")
        cmp = (a.litigation_status ?? "").localeCompare(b.litigation_status ?? "");
      else if (id === "offer_status") cmp = (a.offer_status ?? "").localeCompare(b.offer_status ?? "");
      else if (id === "payment_status") cmp = (a.payment_status ?? "").localeCompare(b.payment_status ?? "");
      else if (id === "updated_at") cmp = new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime();
      return cmp * dir;
    });
    return copy;
  }, [cases, sorting]);

  const columns = useMemo<ColumnDef<FirmCaseItem, unknown>[]>(
    () => [
      {
        accessorKey: "parcel_id",
        header: "Parcel ID",
        cell: ({ row, getValue }) => (
          <Link
            to={`/parcels/${encodeURIComponent(String(getValue()))}?projectId=${encodeURIComponent(row.original.project_id)}`}
            className="font-id font-medium text-brand hover:underline"
            onClick={(e) => e.stopPropagation()}
          >
            {String(getValue())}
          </Link>
        ),
      },
      {
        id: "project_name",
        accessorFn: (r) => r.project_name ?? r.project_id,
        header: "Project",
        cell: ({ row }) => row.original.project_name || row.original.project_id,
      },
      {
        accessorKey: "parcel_stage",
        header: "Stage",
        cell: ({ getValue }) => <StageBadge stage={String(getValue())} />,
      },
      {
        accessorKey: "litigation_status",
        header: "Litigation",
        enableSorting: true,
        cell: ({ getValue }) => (
          <span className="text-slate-600">{getValue() ? String(getValue()).replace(/_/g, " ") : "—"}</span>
        ),
      },
      {
        accessorKey: "offer_status",
        header: "Offer",
        cell: ({ getValue }) => (
          <span className="text-slate-600">{getValue() ? String(getValue()).replace(/_/g, " ") : "—"}</span>
        ),
      },
      {
        accessorKey: "payment_status",
        header: "Payment",
        cell: ({ getValue }) => (
          <span className="text-slate-600">{getValue() ? String(getValue()).replace(/_/g, " ") : "—"}</span>
        ),
      },
      {
        accessorKey: "updated_at",
        header: "Updated",
        cell: ({ getValue }) => formatDate(String(getValue())),
      },
    ],
    [],
  );

  const casesToolbar = (
    <>
      <input
        type="text"
        placeholder="Search by parcel ID…"
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        className="h-8 w-48 rounded-control border border-slate-300 px-3 text-small"
        aria-label="Search cases by parcel ID"
      />
      <select
        value={statusFilter}
        onChange={(e) => setStatusFilter(e.target.value)}
        className="h-8 rounded-control border border-slate-300 px-2 text-small"
        aria-label="Filter by stage"
      >
        <option value="">All stages</option>
        <option value="intake">Intake</option>
        <option value="appraisal">Appraisal</option>
        <option value="offer_pending">Offer pending</option>
        <option value="offer_sent">Offer sent</option>
        <option value="negotiation">Negotiation</option>
        <option value="closing">Closing</option>
        <option value="litigation">Litigation</option>
        <option value="closed">Closed</option>
      </select>
      <select
        value={litigationFilter}
        onChange={(e) => setLitigationFilter(e.target.value)}
        className="h-8 rounded-control border border-slate-300 px-2 text-small"
        aria-label="Filter by litigation status"
      >
        <option value="">All litigation status</option>
        <option value="filed">Filed</option>
        <option value="served">Served</option>
        <option value="commissioners_hearing">Commissioners hearing</option>
        <option value="trial">Trial</option>
        <option value="settled">Settled</option>
        <option value="closed">Closed</option>
      </select>
    </>
  );

  if (loading && !metrics) {
    return (
      <section className="space-y-6">
        <div className="flex items-center justify-center py-12">
          <div className="text-slate-500">Loading dashboard…</div>
        </div>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <div>
        <p className="text-sm uppercase tracking-wide text-brand">{t("pages.firmAdmin.eyebrow")}</p>
        <h1 className="mt-2 text-3xl font-semibold">{t("pages.firmAdmin.title")}</h1>
        <p className="mt-2 max-w-3xl text-slate-600">{t("pages.firmAdmin.subtitle")}</p>
      </div>

      {error && (
        <Alert
          variant="danger"
          title="Couldn't load firm dashboard"
          action={{ label: "Retry", onClick: () => void loadDashboard() }}
        >
          {error}
        </Alert>
      )}

      {metrics && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm text-slate-500">Total Projects</p>
            <p className="mt-1 text-3xl font-semibold text-slate-900">{metrics.total_projects}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm text-slate-500">Total Parcels</p>
            <p className="mt-1 text-3xl font-semibold text-slate-900">{metrics.total_parcels}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm text-slate-500">Litigation Cases</p>
            <p className="mt-1 text-3xl font-semibold text-red-600">{metrics.litigation_cases}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm text-slate-500">Completion Rate</p>
            <p className="mt-1 text-3xl font-semibold text-emerald-600">{metrics.completion_rate}%</p>
          </div>
        </div>
      )}

      {metrics && (
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm text-slate-500">Active Negotiations</p>
            <p className="mt-1 text-2xl font-semibold text-orange-600">{metrics.active_negotiations}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm text-slate-500">Pending Offers</p>
            <p className="mt-1 text-2xl font-semibold text-amber-600">{metrics.pending_offers}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm text-slate-500">Active ROEs</p>
            <p className="mt-1 text-2xl font-semibold text-blue-600">{metrics.active_roes}</p>
          </div>
        </div>
      )}

      {metrics && Object.keys(metrics.parcels_by_stage).length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-lg font-semibold">Parcels by Stage</h3>
          <div className="flex flex-wrap gap-2">
            {Object.entries(metrics.parcels_by_stage).map(([stage, count]) => (
              <span key={stage} className="inline-flex items-center gap-1.5">
                <StageBadge stage={stage} />
                <span className="text-small font-medium tabular-nums text-slate-700">{count}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-2">
        <h3 className="text-lg font-semibold text-slate-900">All cases</h3>
        <p className="text-sm text-slate-500">Cases across all firm projects</p>
        <DataGrid<FirmCaseItem>
          data={sortedCases}
          columns={columns}
          rowId={(r) => r.parcel_id}
          total={casesTotal}
          loading={loading}
          noun="cases"
          sorting={sorting}
          onSortingChange={setSorting}
          pageIndex={pageIndex}
          pageSize={pageSize}
          onPageChange={setPageIndex}
          onPageSizeChange={(n) => setPageSize(n)}
          toolbar={casesToolbar}
          virtualizeRows={false}
          emptyState={<EmptyState message="Try adjusting filters or search." title="No cases found" />}
        />
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="mb-4 text-lg font-semibold">Recent Activity</h3>
        {activities.length === 0 ? (
          <p className="text-slate-500">No recent activity</p>
        ) : (
          <ul className="space-y-3">
            {activities.map((activity) => (
              <li key={activity.id} className="flex items-start gap-3 rounded-lg bg-slate-50 p-3">
                <div className="mt-2 h-2 w-2 shrink-0 rounded-full bg-brand" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-slate-900">
                    {activity.action} on {activity.resource}
                  </p>
                  <p className="mt-0.5 text-xs text-slate-500">
                    {activity.actor_persona && (
                      <span className="capitalize">{activity.actor_persona.replace(/_/g, " ")}</span>
                    )}
                    {" · "}
                    {formatDate(activity.occurred_at)}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
