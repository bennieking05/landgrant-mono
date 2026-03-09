import { Navigate, Route, Routes } from "react-router-dom";
import { AppContextProvider } from "@/context";
import { AppLayout } from "@/components/AppLayout";
import { HomePage } from "@/pages/HomePage";
import { IntakePage } from "@/pages/IntakePage";
import { WorkbenchPage } from "@/pages/WorkbenchPage";
import { CounselPage } from "@/pages/CounselPage";
import { OpsPage } from "@/pages/OpsPage";
import { FirmAdminPage } from "@/pages/FirmAdminPage";
import { AdminPage } from "@/pages/AdminPage";

export function App() {
  return (
    <AppContextProvider>
      <AppLayout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/intake" element={<IntakePage />} />
          <Route path="/workbench" element={<WorkbenchPage />} />
          <Route path="/counsel" element={<CounselPage />} />
          <Route path="/ops" element={<OpsPage />} />
          <Route path="/firm-admin" element={<FirmAdminPage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppLayout>
    </AppContextProvider>
  );
}



