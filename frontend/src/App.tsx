import { useEffect, useState } from "react";
import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { AppContextProvider, AuthProvider, useAppContext, useAuth } from "@/context";
import { AppLayout } from "@/components/AppLayout";
import { PortalLayout } from "@/components/PortalLayout";
import { PersonaRoute } from "@/components/PersonaRoute";
import { HomePage } from "@/pages/HomePage";
import { LoginPage } from "@/pages/LoginPage";
import { IntakePage } from "@/pages/IntakePage";
import { PortalPage } from "@/pages/PortalPage";
import { WorkbenchPage } from "@/pages/WorkbenchPage";
import { CounselPage } from "@/pages/CounselPage";
import { OpsPage } from "@/pages/OpsPage";
import { FirmAdminPage } from "@/pages/FirmAdminPage";
import { AdminPage } from "@/pages/AdminPage";
import { ParcelDetailPage } from "@/pages/ParcelDetailPage";
import { NotFoundPage } from "@/pages/NotFoundPage";

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
        <Outlet />
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
    </AuthProvider>
  );
}
