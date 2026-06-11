import { Link, useLocation } from "react-router-dom";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";

export function NotFoundPage() {
  const location = useLocation();
  useDocumentTitle("Page not found");

  return (
    <div
      className="flex h-full items-center justify-center px-4 py-16"
      data-testid="not-found-page"
      role="alert"
      aria-live="polite"
    >
      <div className="max-w-lg text-center">
        <p className="text-sm font-semibold uppercase tracking-wide text-brand">
          404
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-900">
          That page does not exist
        </h1>
        <p className="mt-3 text-slate-600">
          We couldn&apos;t find{" "}
          <code className="rounded bg-slate-100 px-1.5 py-0.5 text-sm">
            {location.pathname}
          </code>
          . Check the link or return to the dashboard to pick up where you left
          off.
        </p>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
          <Link
            to="/"
            className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-brand/90"
            data-testid="not-found-home"
          >
            Back to dashboard
          </Link>
          <a
            href="mailto:support@landgrantiq.com"
            className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:border-brand hover:text-brand"
          >
            Contact support
          </a>
        </div>
      </div>
    </div>
  );
}

export default NotFoundPage;
