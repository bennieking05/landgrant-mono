import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { AppContextProvider, AuthProvider, useAuth } from "@/context";
import { AppLayout } from "@/components/AppLayout";
import { PersonaRoute } from "@/components/PersonaRoute";
import { HomePage } from "@/pages/HomePage";
import { LoginPage } from "@/pages/LoginPage";
import { IntakePage } from "@/pages/IntakePage";
import { WorkbenchPage } from "@/pages/WorkbenchPage";
import { CounselPage } from "@/pages/CounselPage";
import { OpsPage } from "@/pages/OpsPage";
import { FirmAdminPage } from "@/pages/FirmAdminPage";
import { AdminPage } from "@/pages/AdminPage";
import { NotFoundPage } from "@/pages/NotFoundPage";

function ProtectedShell() {
  const { isAuthenticated, me } = useAuth();
  const location = useLocation();
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  // Wait for /auth/me before rendering persona-gated routes; otherwise the
  // persona defaults to ``land_agent`` and PersonaRoute can wrongly redirect a
  // deep-linked/refreshed page (e.g. /portal, /intake, /admin) before the real persona
  // resolves.
  if (!me) {
    return (
      <div className="flex min-h-screen items-center justify-center text-slate-500">
        Loading…
      </div>
    );
  }
  return (
    <AppContextProvider>
      <AppLayout>
        <Outlet />
      </AppLayout>
    </AppContextProvider>
  );
}

export function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedShell />}>
          <Route path="/" element={<HomePage />} />
          <Route
            path="/portal"
            element={
              <PersonaRoute path="/portal">
                <IntakePage />
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
