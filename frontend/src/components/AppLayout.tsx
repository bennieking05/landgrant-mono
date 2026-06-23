import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Menu,
  X,
  PanelLeftClose,
  PanelLeft,
  Search,
  LogOut,
  ChevronDown,
} from "lucide-react";
import { useAppContext, useAuth, type Persona } from "@/context";
import { navForPersona } from "@/constants/navConfig";
import { NotificationBell } from "@/components/NotificationBell";
import { CommandPalette } from "@/components/CommandPalette";
import { AppFooter } from "@/components/AppFooter";
import { setStoredLocale } from "@/i18n";
import { cn } from "@/lib/cn";
import {
  Logo,
  Tooltip,
  Select,
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/components/ui";

const personaLabels: Record<Persona, string> = {
  landowner: "Landowner",
  land_agent: "Land Agent",
  in_house_counsel: "In-House Counsel",
  outside_counsel: "Outside Counsel",
  firm_admin: "Firm Admin",
  platform_admin: "Platform Admin",
};

const COLLAPSE_KEY = "landgrant.sidebar.collapsed";

type Props = { children: React.ReactNode };

export function AppLayout({ children }: Props) {
  const { t, i18n } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const { logout, me } = useAuth();
  const { projects, projectId, setProjectId, persona, loading } = useAppContext();

  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      return window.localStorage.getItem(COLLAPSE_KEY) === "1";
    } catch {
      return false;
    }
  });
  const [mobileOpen, setMobileOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  const navItems = navForPersona(persona);
  const isLandowner = persona === "landowner";
  const activeItem = navItems.find((i) =>
    i.path === "/" ? location.pathname === "/" : location.pathname.startsWith(i.path),
  );

  // Cmd-K opens global search.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((o) => !o);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // Close the mobile drawer on navigation.
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  function toggleCollapsed() {
    setCollapsed((c) => {
      const next = !c;
      try {
        window.localStorage.setItem(COLLAPSE_KEY, next ? "1" : "0");
      } catch {
        /* ignore */
      }
      return next;
    });
  }

  const workspaceItems = navItems.filter((i) => i.section === "workspace");
  const adminItems = navItems.filter((i) => i.section === "administration");

  function NavLink({ item }: { item: (typeof navItems)[number] }) {
    const Icon = item.icon;
    const active =
      item.path === "/" ? location.pathname === "/" : location.pathname.startsWith(item.path);
    const label = t(item.labelKey, { defaultValue: item.fallbackLabel });
    const link = (
      <Link
        to={item.path}
        className={cn(
          "flex items-center gap-3 rounded-control px-3 py-2 text-small font-medium transition-colors duration-fast",
          collapsed && "justify-center px-0",
          active
            ? "bg-brand/10 text-brand"
            : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
        )}
        aria-current={active ? "page" : undefined}
      >
        <Icon className="h-[18px] w-[18px] shrink-0" />
        {!collapsed && <span className="truncate">{label}</span>}
      </Link>
    );
    return collapsed ? (
      <Tooltip content={label} side="right">
        <span>{link}</span>
      </Tooltip>
    ) : (
      link
    );
  }

  const sidebarContent = (
    <>
      <div className={cn("flex h-16 items-center border-b border-slate-200 px-4", collapsed && "justify-center px-0")}>
        <Link to="/" aria-label="LandGrantIQ home">
          {collapsed ? <Logo variant="mark" size={28} /> : <Logo size={26} />}
        </Link>
      </div>
      <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-4" aria-label="Primary">
        <div className="space-y-1">
          {!collapsed && (
            <p className="px-3 pb-1 text-caption font-semibold uppercase text-slate-500">Workspace</p>
          )}
          {workspaceItems.map((item) => (
            <NavLink key={item.path} item={item} />
          ))}
        </div>
        {adminItems.length > 0 && (
          <div className="space-y-1">
            {!collapsed && (
              <p className="px-3 pb-1 text-caption font-semibold uppercase text-slate-500">
                Administration
              </p>
            )}
            {adminItems.map((item) => (
              <NavLink key={item.path} item={item} />
            ))}
          </div>
        )}
      </nav>
      <div className="hidden border-t border-slate-200 p-2 md:block">
        <button
          type="button"
          onClick={toggleCollapsed}
          className={cn(
            "flex w-full items-center gap-3 rounded-control px-3 py-2 text-small font-medium text-slate-500 hover:bg-slate-100",
            collapsed && "justify-center px-0",
          )}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <PanelLeft className="h-[18px] w-[18px]" /> : <PanelLeftClose className="h-[18px] w-[18px]" />}
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </>
  );

  return (
    <div className="flex min-h-screen bg-slate-50">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[120] focus:rounded-control focus:bg-brand focus:px-4 focus:py-2 focus:text-white"
      >
        Skip to content
      </a>

      {/* Desktop sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-30 hidden flex-col border-r border-slate-200 bg-white transition-[width] duration-base md:flex",
          collapsed ? "w-16" : "w-60",
        )}
      >
        {sidebarContent}
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div
            className="absolute inset-0 bg-navy-950/40"
            onClick={() => setMobileOpen(false)}
            aria-hidden
          />
          <aside className="absolute inset-y-0 left-0 flex w-64 flex-col border-r border-slate-200 bg-white">
            <button
              type="button"
              className="absolute right-2 top-4 rounded-control p-1 text-slate-400 hover:bg-slate-100"
              onClick={() => setMobileOpen(false)}
              aria-label="Close menu"
            >
              <X className="h-5 w-5" />
            </button>
            {sidebarContent}
          </aside>
        </div>
      )}

      {/* Content column */}
      <div className={cn("flex min-h-screen flex-1 flex-col", collapsed ? "md:pl-16" : "md:pl-60")}>
        <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-slate-200 bg-white/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-white/80">
          <button
            type="button"
            className="rounded-control p-2 text-slate-500 hover:bg-slate-100 md:hidden"
            onClick={() => setMobileOpen(true)}
            aria-label="Open menu"
          >
            <Menu className="h-5 w-5" />
          </button>

          <div className="min-w-0 flex-1">
            <p className="truncate text-h3 text-slate-900">
              {activeItem ? t(activeItem.labelKey, { defaultValue: activeItem.fallbackLabel }) : "LandGrantIQ"}
            </p>
          </div>

          {/* Global search trigger */}
          <button
            type="button"
            onClick={() => setPaletteOpen(true)}
            className="hidden items-center gap-2 rounded-control border border-slate-300 bg-white px-3 py-1.5 text-small text-slate-500 hover:bg-slate-50 sm:flex"
          >
            <Search className="h-4 w-4" />
            <span>Search</span>
            <kbd className="rounded bg-slate-100 px-1.5 py-0.5 text-caption text-slate-600">&#8984;K</kbd>
          </button>
          <button
            type="button"
            onClick={() => setPaletteOpen(true)}
            className="rounded-control p-2 text-slate-500 hover:bg-slate-100 sm:hidden"
            aria-label="Search"
          >
            <Search className="h-5 w-5" />
          </button>

          {/* Project context */}
          {!isLandowner && (
            <Select
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              disabled={loading}
              className="w-full min-w-0 max-w-[10rem] flex-shrink-0 sm:max-w-[11rem] sm:w-44"
              aria-label="Active project"
            >
              {projects.length === 0 && <option value="">No projects</option>}
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </Select>
          )}

          <label className="hidden md:block">
            <span className="sr-only">{t("app.language")}</span>
            <Select
              value={i18n.language.startsWith("es") ? "es" : "en"}
              onChange={(e) => {
                void i18n.changeLanguage(e.target.value);
                setStoredLocale(e.target.value);
              }}
              className="w-[5.5rem]"
              aria-label={t("app.language")}
            >
              <option value="en">{t("app.english")}</option>
              <option value="es">{t("app.spanish")}</option>
            </Select>
          </label>

          <NotificationBell />

          {/* User menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                className="flex items-center gap-2 rounded-control px-2 py-1.5 text-left hover:bg-slate-100"
              >
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand/10 text-caption font-semibold text-brand">
                  {(me?.email ?? me?.sub ?? "U").slice(0, 2).toUpperCase()}
                </span>
                <ChevronDown className="hidden h-4 w-4 text-slate-400 sm:block" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuLabel>
                <span className="block truncate text-small font-medium text-slate-900">
                  {me?.email ?? me?.sub ?? "Signed in"}
                </span>
                <span className="text-caption text-slate-500">{personaLabels[persona]}</span>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onSelect={() => {
                  logout();
                  navigate("/login", { replace: true });
                }}
              >
                <LogOut className="h-4 w-4" /> Sign out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>

        <main id="main-content" className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
          {children}
        </main>

        <AppFooter />
      </div>

      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
    </div>
  );
}
