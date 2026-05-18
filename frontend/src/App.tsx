import { Route, Routes } from "react-router-dom";
import { AppContextProvider } from "@/context";
import { AppLayout } from "@/components/AppLayout";
import { PersonaRoute } from "@/components/PersonaRoute";
import { HomePage } from "@/pages/HomePage";
import { IntakePage } from "@/pages/IntakePage";
import { WorkbenchPage } from "@/pages/WorkbenchPage";
import { CounselPage } from "@/pages/CounselPage";
import { OpsPage } from "@/pages/OpsPage";
import { FirmAdminPage } from "@/pages/FirmAdminPage";
import { AdminPage } from "@/pages/AdminPage";
import { NotFoundPage } from "@/pages/NotFoundPage";

export function App() {
  return (
    <AppContextProvider>
      <AppLayout>
        <Routes>
          <Route path="/" element={<HomePage />} />
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
        </Routes>
      </AppLayout>
    </AppContextProvider>
  );
}



