import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAppContext, useAuth, type Persona } from "@/context";
import { personaNavMap } from "@/constants/personaNav";
import { NotificationBell } from "@/components/NotificationBell";
import {
  Home,
  FileInput,
  Briefcase,
  Scale,
  Settings,
  Building2,
  ShieldCheck,
  LogOut,
} from "lucide-react";

const navItems = [
  { path: "/", label: "Home", icon: Home },
  { path: "/intake", label: "Intake", icon: FileInput },
  { path: "/workbench", label: "Workbench", icon: Briefcase },
  { path: "/counsel", label: "Counsel", icon: Scale },
  { path: "/ops", label: "Operations", icon: Settings },
  { path: "/firm-admin", label: "Firm Admin", icon: Building2 },
  { path: "/admin", label: "Admin", icon: ShieldCheck },
];

const personaLabels: Record<Persona, string> = {
  landowner: "Landowner",
  land_agent: "Land Agent",
  in_house_counsel: "In-House Counsel",
  outside_counsel: "Outside Counsel",
  firm_admin: "Firm Admin",
  platform_admin: "Platform Admin",
};

type Props = {
  children: React.ReactNode;
};

export function AppLayout({ children }: Props) {
  const location = useLocation();
  const navigate = useNavigate();
  const { logout, me } = useAuth();
  const {
    projects,
    projectId,
    setProjectId,
    parcels,
    parcelId,
    setParcelId,
    persona,
    loading,
  } = useAppContext();

  const allowedPaths = personaNavMap[persona];
  const filteredNav = navItems.filter((item) => allowedPaths.includes(item.path));

  const isHome = location.pathname === "/";

  const isLandownerShell = persona === "landowner";

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Navigation Bar */}
      <nav className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-6xl px-6">
          <div className="flex h-16 items-center justify-between">
            {/* Logo and Nav Links */}
            <div className="flex items-center gap-8">
              <Link to="/" className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand text-white font-bold text-sm">
                  LR
                </div>
                <span className="font-semibold text-slate-900">LandGrant</span>
              </Link>

              <div className="hidden md:flex items-center gap-1">
                {filteredNav.map((item) => {
                  const isActive = location.pathname === item.path;
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                        isActive
                          ? "bg-brand/10 text-brand"
                          : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                      }`}
                    >
                      <Icon className="h-4 w-4" />
                      {item.label}
                    </Link>
                  );
                })}
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="hidden text-right sm:block">
                <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  {personaLabels[persona]}
                </div>
                <div className="max-w-[14rem] truncate text-sm text-slate-800">
                  {me?.email ?? me?.sub ?? ""}
                </div>
              </div>

              {/* Project/Parcel Selector — internal users only */}
              {!isHome && !isLandownerShell && (
                <>
                  <div className="relative">
                    <select
                      value={projectId}
                      onChange={(e) => setProjectId(e.target.value)}
                      className="appearance-none rounded-md border border-slate-300 bg-white pl-3 pr-8 py-1.5 text-sm font-medium text-slate-700 focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand"
                    >
                      {projects.length === 0 && (
                        <option value="">No projects</option>
                      )}
                      {projects.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="relative">
                    <select
                      value={parcelId ?? ""}
                      onChange={(e) => setParcelId(e.target.value || null)}
                      disabled={loading || parcels.length === 0}
                      className="appearance-none rounded-md border border-slate-300 bg-white pl-3 pr-8 py-1.5 text-sm font-medium text-slate-700 focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand disabled:bg-slate-100 disabled:text-slate-400"
                    >
                      {parcels.length === 0 ? (
                        <option value="">
                          {loading ? "Loading..." : "No parcels"}
                        </option>
                      ) : (
                        parcels.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.id}
                          </option>
                        ))
                      )}
                    </select>
                  </div>
                </>
              )}

              <NotificationBell />

              <button
                type="button"
                onClick={() => {
                  logout();
                  navigate("/login", { replace: true });
                }}
                className="inline-flex items-center gap-1 rounded-md border border-slate-300 px-2 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
                title="Sign out"
              >
                <LogOut className="h-4 w-4" />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Navigation */}
        <div className="md:hidden border-t border-slate-200 px-4 py-2">
          <div className="flex gap-1 overflow-x-auto">
            {filteredNav.map((item) => {
              const isActive = location.pathname === item.path;
              const Icon = item.icon;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-1.5 rounded-md px-3 py-2 text-xs font-medium whitespace-nowrap transition-colors ${
                    isActive
                      ? "bg-brand/10 text-brand"
                      : "text-slate-600 hover:bg-slate-100"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>
      </nav>

      {/* Page Content */}
      <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
    </div>
  );
}
