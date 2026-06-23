import { lazy } from "react";
import { Navigate } from "react-router-dom";
import { useAppContext } from "@/context";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";

// Lazy so Recharts (and the rest of the dashboard) stays out of the initial
// bundle; the shell's Suspense boundary renders the fallback while it loads.
const DashboardPage = lazy(() =>
  import("@/pages/DashboardPage").then((m) => ({ default: m.DashboardPage })),
);

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
