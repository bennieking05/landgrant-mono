import { useState, useEffect, useCallback } from "react";
import {
  getPlatformDashboard,
  getPlatformCases,
  getPlatformProjects,
  getPlatformHealth,
  globalSearch,
  PlatformMetrics,
  GlobalCaseItem,
  ProjectOverview,
  SearchResult,
  HealthStatus,
} from "@/lib/api";

type TabType = "cases" | "projects" | "health";

export function AdminPage() {
  const [activeTab, setActiveTab] = useState<TabType>("cases");
  const [metrics, setMetrics] = useState<PlatformMetrics | null>(null);
  const [cases, setCases] = useState<GlobalCaseItem[]>([]);
  const [casesTotal, setCasesTotal] = useState(0);
  const [projects, setProjects] = useState<ProjectOverview[]>([]);
  const [projectsTotal, setProjectsTotal] = useState(0);
  const [healthServices, setHealthServices] = useState<HealthStatus[]>([]);
  const [overallHealth, setOverallHealth] = useState<string>("unknown");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters for cases
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [projectFilter, setProjectFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [litigationFilter, setLitigationFilter] = useState<string>("");
  const [caseTypeFilter, setCaseTypeFilter] = useState<string>("");
  const [showSearchResults, setShowSearchResults] = useState(false);

  // Load dashboard metrics
  async function loadDashboard() {
    try {
      const data = await getPlatformDashboard();
      setMetrics(data);
    } catch (err) {
      console.error("Failed to load dashboard metrics:", err);
    }
  }

  // Load cases
  async function loadCases() {
    setLoading(true);
    setError(null);
    try {
      const data = await getPlatformCases({
        project_id: projectFilter || undefined,
        status: statusFilter || undefined,
        litigation_status: litigationFilter || undefined,
        case_type: caseTypeFilter || undefined,
        search: searchQuery || undefined,
        limit: 50,
      });
      setCases(data.cases);
      setCasesTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load cases");
    } finally {
      setLoading(false);
    }
  }

  // Load projects
  async function loadProjects() {
    setLoading(true);
    setError(null);
    try {
      const data = await getPlatformProjects({ limit: 50 });
      setProjects(data.projects);
      setProjectsTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load projects");
    } finally {
      setLoading(false);
    }
  }

  // Load health
  async function loadHealth() {
    setLoading(true);
    setError(null);
    try {
      const data = await getPlatformHealth();
      setHealthServices(data.services);
      setOverallHealth(data.overall_status);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load health status");
    } finally {
      setLoading(false);
    }
  }

  // Global search handler
  const handleSearch = useCallback(async (query: string) => {
    if (query.length < 2) {
      setSearchResults([]);
      setShowSearchResults(false);
      return;
    }
    try {
      const data = await globalSearch(query, 10);
      setSearchResults(data.results);
      setShowSearchResults(true);
    } catch (err) {
      console.error("Search failed:", err);
    }
  }, []);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchQuery) {
        handleSearch(searchQuery);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery, handleSearch]);

  // Initial load
  useEffect(() => {
    loadDashboard();
  }, []);

  // Load tab content
  useEffect(() => {
    if (activeTab === "cases") {
      loadCases();
    } else if (activeTab === "projects") {
      loadProjects();
    } else if (activeTab === "health") {
      loadHealth();
    }
  }, [activeTab, statusFilter, litigationFilter, projectFilter, caseTypeFilter]);

  // Format date
  function formatDate(isoString: string): string {
    if (!isoString) return "-";
    const date = new Date(isoString);
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  // Status colors
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

  function getHealthColor(status: string): string {
    if (status === "healthy") return "bg-green-500";
    if (status === "degraded") return "bg-amber-500";
    return "bg-red-500";
  }

  return (
    <section className="space-y-6">
      {/* Header */}
      <div>
        <p className="text-sm uppercase tracking-wide text-brand">Platform Administration</p>
        <h1 className="mt-2 text-3xl font-semibold">Admin Dashboard</h1>
        <p className="mt-2 max-w-3xl text-slate-600">
          System-wide view of all cases, projects, and services. Search across all data and monitor platform health.
        </p>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-red-700">
          {error}
        </div>
      )}

      {/* Global Search */}
      <div className="relative">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <input
            type="text"
            placeholder="Search cases, parcels, parties, cause numbers..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onFocus={() => searchResults.length > 0 && setShowSearchResults(true)}
            onBlur={() => setTimeout(() => setShowSearchResults(false), 200)}
            className="w-full px-4 py-3 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-brand focus:border-brand"
          />
        </div>

        {/* Search Results Dropdown */}
        {showSearchResults && searchResults.length > 0 && (
          <div className="absolute z-10 mt-1 w-full bg-white rounded-xl border border-slate-200 shadow-lg max-h-96 overflow-y-auto">
            {searchResults.map((result) => (
              <div
                key={`${result.result_type}-${result.id}`}
                className="px-4 py-3 hover:bg-slate-50 cursor-pointer border-b border-slate-100 last:border-b-0"
              >
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    result.result_type === "parcel" ? "bg-blue-100 text-blue-700" :
                    result.result_type === "case" ? "bg-red-100 text-red-700" :
                    "bg-slate-100 text-slate-700"
                  }`}>
                    {result.result_type}
                  </span>
                  <span className="font-medium text-slate-900">{result.title}</span>
                </div>
                {result.subtitle && (
                  <p className="text-sm text-slate-500 mt-0.5">{result.subtitle}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Metrics Cards */}
      {metrics && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm text-slate-500">Total Firms</p>
            <p className="mt-1 text-3xl font-semibold text-slate-900">{metrics.total_firms}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm text-slate-500">Total Parcels</p>
            <p className="mt-1 text-3xl font-semibold text-slate-900">{metrics.total_parcels}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm text-slate-500">Litigation Cases</p>
            <p className="mt-1 text-3xl font-semibold text-red-600">{metrics.total_cases}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm text-slate-500">Active Sessions</p>
            <p className="mt-1 text-3xl font-semibold text-blue-600">{metrics.active_portal_sessions}</p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-slate-200">
        <nav className="flex gap-6">
          <button
            onClick={() => setActiveTab("cases")}
            className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === "cases"
                ? "border-brand text-brand"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            All Cases
          </button>
          <button
            onClick={() => setActiveTab("projects")}
            className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === "projects"
                ? "border-brand text-brand"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            Projects
          </button>
          <button
            onClick={() => setActiveTab("health")}
            className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === "health"
                ? "border-brand text-brand"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            System Health
          </button>
        </nav>
      </div>

      {/* Cases Tab */}
      {activeTab === "cases" && (
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="p-6 border-b border-slate-200">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold">All Cases</h3>
                <p className="text-sm text-slate-500">{casesTotal} total cases across all firms</p>
              </div>
            </div>

            {/* Filters */}
            <div className="flex flex-wrap gap-3">
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
                <option value="">All Litigation</option>
                <option value="filed">Filed</option>
                <option value="served">Served</option>
                <option value="commissioners_hearing">Commissioners Hearing</option>
                <option value="trial">Trial</option>
                <option value="settled">Settled</option>
                <option value="closed">Closed</option>
              </select>
              <select
                value={caseTypeFilter}
                onChange={(e) => setCaseTypeFilter(e.target.value)}
                className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
              >
                <option value="">All Types</option>
                <option value="standard">Standard</option>
                <option value="quick_take">Quick Take</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="text-left px-6 py-3 font-medium">Parcel ID</th>
                  <th className="text-left px-6 py-3 font-medium">Project</th>
                  <th className="text-left px-6 py-3 font-medium">Jurisdiction</th>
                  <th className="text-left px-6 py-3 font-medium">Stage</th>
                  <th className="text-left px-6 py-3 font-medium">Litigation</th>
                  <th className="text-left px-6 py-3 font-medium">Cause #</th>
                  <th className="text-left px-6 py-3 font-medium">Landowner</th>
                  <th className="text-left px-6 py-3 font-medium">Updated</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading ? (
                  <tr>
                    <td colSpan={8} className="px-6 py-8 text-center text-slate-500">
                      Loading cases...
                    </td>
                  </tr>
                ) : cases.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-6 py-8 text-center text-slate-500">
                      No cases found
                    </td>
                  </tr>
                ) : (
                  cases.map((c) => (
                    <tr key={c.parcel_id} className="hover:bg-slate-50">
                      <td className="px-6 py-4 font-medium text-slate-900">{c.parcel_id}</td>
                      <td className="px-6 py-4 text-slate-600">{c.project_name || c.project_id}</td>
                      <td className="px-6 py-4 text-slate-600">{c.jurisdiction || "-"}</td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(c.parcel_stage)}`}>
                          {c.parcel_stage.replace(/_/g, " ")}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-slate-600">{c.litigation_status?.replace(/_/g, " ") || "-"}</td>
                      <td className="px-6 py-4 text-slate-600">{c.cause_number || "-"}</td>
                      <td className="px-6 py-4 text-slate-600">{c.landowner_name || "-"}</td>
                      <td className="px-6 py-4 text-slate-500">{formatDate(c.updated_at)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Projects Tab */}
      {activeTab === "projects" && (
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="p-6 border-b border-slate-200">
            <h3 className="text-lg font-semibold">All Projects</h3>
            <p className="text-sm text-slate-500">{projectsTotal} total projects</p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="text-left px-6 py-3 font-medium">Project</th>
                  <th className="text-left px-6 py-3 font-medium">Jurisdiction</th>
                  <th className="text-left px-6 py-3 font-medium">Stage</th>
                  <th className="text-left px-6 py-3 font-medium">Parcels</th>
                  <th className="text-left px-6 py-3 font-medium">Litigation</th>
                  <th className="text-left px-6 py-3 font-medium">Completion</th>
                  <th className="text-left px-6 py-3 font-medium">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-8 text-center text-slate-500">
                      Loading projects...
                    </td>
                  </tr>
                ) : projects.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-8 text-center text-slate-500">
                      No projects found
                    </td>
                  </tr>
                ) : (
                  projects.map((p) => (
                    <tr key={p.project_id} className="hover:bg-slate-50">
                      <td className="px-6 py-4">
                        <div className="font-medium text-slate-900">{p.project_name}</div>
                        <div className="text-xs text-slate-500">{p.project_id}</div>
                      </td>
                      <td className="px-6 py-4 text-slate-600">{p.jurisdiction}</td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(p.stage)}`}>
                          {p.stage}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-slate-900 font-medium">{p.parcel_count}</td>
                      <td className="px-6 py-4 text-red-600 font-medium">{p.litigation_count}</td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-2 bg-slate-200 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-emerald-500 rounded-full"
                              style={{ width: `${p.completion_rate}%` }}
                            ></div>
                          </div>
                          <span className="text-slate-600">{p.completion_rate}%</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-slate-500">{formatDate(p.created_at)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Health Tab */}
      {activeTab === "health" && (
        <div className="space-y-6">
          {/* Overall Status */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-4">
              <div className={`w-4 h-4 rounded-full ${getHealthColor(overallHealth)}`}></div>
              <div>
                <h3 className="text-lg font-semibold">Overall System Status</h3>
                <p className="text-sm text-slate-500 capitalize">{overallHealth}</p>
              </div>
            </div>
          </div>

          {/* Service Status */}
          <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="p-6 border-b border-slate-200">
              <h3 className="text-lg font-semibold">Service Health</h3>
            </div>

            <div className="divide-y divide-slate-100">
              {loading ? (
                <div className="px-6 py-8 text-center text-slate-500">
                  Loading health status...
                </div>
              ) : healthServices.length === 0 ? (
                <div className="px-6 py-8 text-center text-slate-500">
                  No health data available
                </div>
              ) : (
                healthServices.map((service) => (
                  <div key={service.service} className="px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`w-3 h-3 rounded-full ${getHealthColor(service.status)}`}></div>
                      <div>
                        <p className="font-medium text-slate-900">{service.service}</p>
                        <p className="text-xs text-slate-500 capitalize">{service.status}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      {service.latency_ms !== null && service.latency_ms !== undefined && (
                        <p className="text-sm text-slate-600">{service.latency_ms}ms</p>
                      )}
                      <p className="text-xs text-slate-500">{formatDate(service.last_check)}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
