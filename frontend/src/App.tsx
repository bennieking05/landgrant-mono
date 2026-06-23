import { lazy, Suspense, useEffect, useState } from "react";
import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { AppContextProvider, AuthProvider, useAppContext, useAuth } from "@/context";
import { AppLayout } from "@/components/AppLayout";
import { PortalLayout } from "@/components/PortalLayout";
import { PersonaRoute } from "@/components/PersonaRoute";
import { HomePage } from "@/pages/HomePage";

// Route-level code splitting: each page (and its heavy deps — Recharts on the
// dashboards, the data grid, etc.) loads on demand instead of bloating the
// initial bundle. HomePage stays eager since it's just the post-login redirect.
const LoginPage = lazy(() => import("@/pages/LoginPage").then((m) => ({ default: m.LoginPage })));
const IntakePage = lazy(() => import("@/pages/IntakePage").then((m) => ({ default: m.IntakePage })));
const PortalPage = lazy(() => import("@/pages/PortalPage").then((m) => ({ default: m.PortalPage })));
const WorkbenchPage = lazy(() => import("@/pages/WorkbenchPage").then((m) => ({ default: m.WorkbenchPage })));
const CounselPage = lazy(() => import("@/pages/CounselPage").then((m) => ({ default: m.CounselPage })));
const OpsPage = lazy(() => import("@/pages/OpsPage").then((m) => ({ default: m.OpsPage })));
const FirmAdminPage = lazy(() => import("@/pages/FirmAdminPage").then((m) => ({ default: m.FirmAdminPage })));
const AdminPage = lazy(() => import("@/pages/AdminPage").then((m) => ({ default: m.AdminPage })));
const ParcelDetailPage = lazy(() => import("@/pages/ParcelDetailPage").then((m) => ({ default: m.ParcelDetailPage })));
const NotFoundPage = lazy(() => import("@/pages/NotFoundPage").then((m) => ({ default: m.NotFoundPage })));

function PageLoading() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center text-slate-500" role="status">
      Loading…
    </div>
  );
}

function ProtectedShell() {
  const { isAuthenticated, me } = useAuth();
  const location = useLocation();
  const [authSlow, setAuthSlow] = useState(false);

  useEffect(() => {
    if (!isAuthenticated || me) {
      setAuthSlow(false);
      return;
    }
    const id = window.setTimeout(() => setAuthSlow(true), 20_000);
    return () => window.clearTimeout(id);
  }, [isAuthenticated, me]);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  // Wait for /auth/me before rendering persona-gated routes; otherwise the
  // persona defaults to ``land_agent`` and PersonaRoute can wrongly redirect a
  // deep-linked/refreshed page (e.g. /portal, /intake, /admin) before the real persona
  // resolves.
  if (!me) {
    if (authSlow) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-6 text-center text-slate-700">
          <p className="font-medium">We couldn&apos;t finish loading your session in time.</p>
          <p className="max-w-md text-sm text-slate-600">
            The server may be slow or unreachable. You can retry or sign in again.
          </p>
          <div className="flex gap-3">
            <button
              type="button"
              className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-dark"
              onClick={() => window.location.reload()}
            >
              Retry
            </button>
            <a
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              href="/login"
            >
              Sign in
            </a>
          </div>
        </div>
      );
    }
    return (
      <div className="flex min-h-screen items-center justify-center text-slate-500">
        Loading…
      </div>
    );
  }
  return (
    <AppContextProvider>
      <ShellChrome>
        <Suspense fallback={<PageLoading />}>
          <Outlet />
        </Suspense>
      </ShellChrome>
    </AppContextProvider>
  );
}

/**
 * Picks the chrome based on persona: landowners get the calm, mobile-first
 * consumer portal; everyone else gets the enterprise sidebar shell.
 */
function ShellChrome({ children }: { children: React.ReactNode }) {
  const { persona } = useAppContext();
  if (persona === "landowner") {
    return <PortalLayout>{children}</PortalLayout>;
  }
  return <AppLayout>{children}</AppLayout>;
}

/** Landowners see the consumer portal flow; staff visiting /portal see intake. */
function PortalEntry() {
  const { persona } = useAppContext();
  return persona === "landowner" ? <PortalPage /> : <IntakePage />;
}

export function App() {
  return (
    <AuthProvider>
      <Suspense fallback={<PageLoading />}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedShell />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/parcels/:parcelId" element={<ParcelDetailPage />} />
          <Route
            path="/portal"
            element={
              <PersonaRoute path="/portal">
                <PortalEntry />
              </PersonaRoute>
            }
          />
          <Route
            path="/intake"
            element={
              <PersonaRoute path="/intake">
                <IntakePage />
              </PersonaRoute>
            }
          />
          <Route
            path="/workbench"
            element={
              <PersonaRoute path="/workbench">
                <WorkbenchPage />
              </PersonaRoute>
            }
          />
          <Route
            path="/counsel"
            element={
              <PersonaRoute path="/counsel">
                <CounselPage />
              </PersonaRoute>
            }
          />
          <Route
            path="/ops"
            element={
              <PersonaRoute path="/ops">
                <OpsPage />
              </PersonaRoute>
            }
          />
          <Route
            path="/firm-admin"
            element={
              <PersonaRoute path="/firm-admin">
                <FirmAdminPage />
              </PersonaRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <PersonaRoute path="/admin">
                <AdminPage />
              </PersonaRoute>
            }
          />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
        </Routes>
      </Suspense>
    </AuthProvider>
  );
}
