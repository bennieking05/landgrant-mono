import { useState, useEffect } from "react";
import {
  getFirmDashboard,
  getFirmCases,
  getFirmActivity,
  FirmMetrics,
  FirmCaseItem,
  FirmActivityItem,
} from "@/lib/api";

export function FirmAdminPage() {
  const [metrics, setMetrics] = useState<FirmMetrics | null>(null);
  const [cases, setCases] = useState<FirmCaseItem[]>([]);
  const [activities, setActivities] = useState<FirmActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [litigationFilter, setLitigationFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");

  async function loadDashboard() {
    setLoading(true);
    setError(null);
    try {
      const [metricsData, casesData, activityData] = await Promise.all([
        getFirmDashboard(),
        getFirmCases({ status: statusFilter || undefined, litigation_status: litigationFilter || undefined, search: searchQuery || undefined, limit: 50 }),
        getFirmActivity(7, 20),
      ]);
      setMetrics(metricsData);
      setCases(casesData.cases);
      setActivities(activityData.activities);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDashboard();
  }, [statusFilter, litigationFilter, searchQuery]);

  // Format date for display
  function formatDate(isoString: string): string {
    if (!isoString) return "-";
    const date = new Date(isoString);
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  // Status badge color
  function getStatusColor(status: string): string {
    const colors: Record<string, string> = {
      intake: "bg-slate-100 text-slate-700",
      appraisal: "bg-blue-100 text-blue-700",
      offer_pending: "bg-amber-100 text-amber-700",
      offer_sent: "bg-yellow-100 text-yellow-700",
      negotiation: "bg-orange-100 text-orange-700",
      closing: "bg-emerald-100 text-emerald-700",
      litigation: "bg-red-100 text-red-700",
      closed: "bg-green-100 text-green-700",
    };
    return colors[status] || "bg-slate-100 text-slate-700";
  }

  if (loading && !metrics) {
    return (
      <section className="space-y-6">
        <div className="flex items-center justify-center py-12">
          <div className="text-slate-500">Loading dashboard...</div>
        </div>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      {/* Header */}
      <div>
        <p className="text-sm uppercase tracking-wide text-brand">Firm Administration</p>
        <h1 className="mt-2 text-3xl font-semibold">Firm Dashboard</h1>
        <p className="mt-2 max-w-3xl text-slate-600">
          Rolled-up view of all cases across your firm's projects. Monitor progress, track litigation, and review activity.
        </p>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-red-700">
          {error}
          <button onClick={loadDashboard} className="ml-4 text-red-600 underline">
            Retry
          </button>
        </div>
      )}

      {/* Metrics Cards */}
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

      {/* Secondary Metrics */}
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

      {/* Stage Distribution */}
      {metrics && Object.keys(metrics.parcels_by_stage).length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-semibold mb-4">Parcels by Stage</h3>
          <div className="flex flex-wrap gap-2">
            {Object.entries(metrics.parcels_by_stage).map(([stage, count]) => (
              <div key={stage} className={`px-3 py-1.5 rounded-full text-sm font-medium ${getStatusColor(stage)}`}>
                {stage.replace(/_/g, " ")}: {count}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Cases Table */}
      <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="p-6 border-b border-slate-200">
          <h3 className="text-lg font-semibold">All Cases</h3>
          <p className="text-sm text-slate-500 mt-1">Cases across all firm projects</p>

          {/* Filters */}
          <div className="mt-4 flex flex-wrap gap-3">
            <input
              type="text"
              placeholder="Search by parcel ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="px-3 py-2 border border-slate-300 rounded-lg text-sm w-48"
            />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
            >
              <option value="">All Stages</option>
              <option value="intake">Intake</option>
              <option value="appraisal">Appraisal</option>
              <option value="offer_pending">Offer Pending</option>
              <option value="offer_sent">Offer Sent</option>
              <option value="negotiation">Negotiation</option>
              <option value="closing">Closing</option>
              <option value="litigation">Litigation</option>
              <option value="closed">Closed</option>
            </select>
            <select
              value={litigationFilter}
              onChange={(e) => setLitigationFilter(e.target.value)}
              className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
            >
              <option value="">All Litigation Status</option>
              <option value="filed">Filed</option>
              <option value="served">Served</option>
              <option value="commissioners_hearing">Commissioners Hearing</option>
              <option value="trial">Trial</option>
              <option value="settled">Settled</option>
              <option value="closed">Closed</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="text-left px-6 py-3 font-medium">Parcel ID</th>
                <th className="text-left px-6 py-3 font-medium">Project</th>
                <th className="text-left px-6 py-3 font-medium">Stage</th>
                <th className="text-left px-6 py-3 font-medium">Litigation</th>
                <th className="text-left px-6 py-3 font-medium">Offer</th>
                <th className="text-left px-6 py-3 font-medium">Payment</th>
                <th className="text-left px-6 py-3 font-medium">Updated</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {cases.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-8 text-center text-slate-500">
                    No cases found
                  </td>
                </tr>
              ) : (
                cases.map((c) => (
                  <tr key={c.parcel_id} className="hover:bg-slate-50">
                    <td className="px-6 py-4 font-medium text-slate-900">{c.parcel_id}</td>
                    <td className="px-6 py-4 text-slate-600">{c.project_name || c.project_id}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(c.parcel_stage)}`}>
                        {c.parcel_stage.replace(/_/g, " ")}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-600">{c.litigation_status?.replace(/_/g, " ") || "-"}</td>
                    <td className="px-6 py-4 text-slate-600">{c.offer_status?.replace(/_/g, " ") || "-"}</td>
                    <td className="px-6 py-4 text-slate-600">{c.payment_status?.replace(/_/g, " ") || "-"}</td>
                    <td className="px-6 py-4 text-slate-500">{formatDate(c.updated_at)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
        {activities.length === 0 ? (
          <p className="text-slate-500">No recent activity</p>
        ) : (
          <ul className="space-y-3">
            {activities.map((activity) => (
              <li key={activity.id} className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg">
                <div className="w-2 h-2 mt-2 rounded-full bg-brand"></div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-900">
                    {activity.action} on {activity.resource}
                  </p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {activity.actor_persona && <span className="capitalize">{activity.actor_persona.replace(/_/g, " ")}</span>}
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
