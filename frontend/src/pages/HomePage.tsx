import { Navigate } from "react-router-dom";
import { useAppContext } from "@/context";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { DashboardPage } from "@/pages/DashboardPage";

/**
 * Post-login landing (UX-2 / UX-3). A signed-in user lands on their dashboard,
 * not a feature index. Landowners go straight to their portal - their role is
 * the workspace.
 */
export function HomePage() {
  const { persona } = useAppContext();
  useDocumentTitle("Dashboard");

  if (persona === "landowner") {
    return <Navigate to="/portal" replace />;
  }

  return <DashboardPage />;
}
