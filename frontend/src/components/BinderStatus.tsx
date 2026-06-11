import { useEffect, useState, useCallback } from "react";
import { apiGet, exportBinder } from "@/lib/api";
import { LoadingSpinner, ErrorMessage, EmptyState } from "@/components/ui";
import { FolderOpen } from "lucide-react";

type BinderSection = { name: string; status: string; detail?: string };

type Props = {
  projectId: string;
  parcelId?: string | null;
};

export function BinderStatus({ projectId, parcelId }: Props) {
  const [sections, setSections] = useState<BinderSection[] | null>(null);
  const [completenessPct, setCompletenessPct] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exportStatus, setExportStatus] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiGet<{
        sections: BinderSection[];
        completeness_pct?: number;
      }>(`/binder/status?project_id=${encodeURIComponent(projectId)}`);
      setSections(res.sections);
      setCompletenessPct(typeof res.completeness_pct === "number" ? res.completeness_pct : null);
    } catch (e) {
      setSections(null);
      setCompletenessPct(null);
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function handleExportBinder() {
    setExporting(true);
    setExportStatus(null);
    try {
      const data = await exportBinder({
        project_id: projectId,
        parcel_id: parcelId ?? undefined,
      });
      setExportStatus(`Bundle ${data.bundle_id} exported successfully`);
    } catch (err) {
      setExportStatus(`Export failed: ${String(err)}`);
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Good-Faith Binder</h3>
          {completenessPct !== null ? (
            <p className="mt-1 text-xs text-slate-500">Completeness: {completenessPct}%</p>
          ) : null}
        </div>
        <button
          type="button"
          onClick={handleExportBinder}
          disabled={exporting}
          className="rounded-md border border-brand px-3 py-1 text-sm text-brand hover:bg-brand/5 disabled:opacity-50"
        >
          {exporting ? "Exporting..." : "Export"}
        </button>
      </div>

      {loading && (
        <div className="mt-4">
          <LoadingSpinner text="Loading binder status..." />
        </div>
      )}

      {error && (
        <div className="mt-4">
          <ErrorMessage message="Failed to load binder status" onRetry={refresh} />
        </div>
      )}

      {!loading && !error && sections?.length === 0 && (
        <EmptyState
          icon={FolderOpen}
          message="No binder sections configured"
          className="mt-4"
        />
      )}

      {!loading && !error && sections && sections.length > 0 && (
        <ul className="mt-4 space-y-2 text-sm">
          {sections.map((section) => (
            <li key={section.name} className="flex flex-col gap-0.5 sm:flex-row sm:items-center sm:justify-between">
              <span>{section.name}</span>
              <div className="flex flex-col items-start gap-0.5 sm:items-end">
                <span
                  className={`text-xs font-medium ${
                    section.status === "Complete" ? "text-emerald-600" : "text-amber-600"
                  }`}
                >
                  {section.status}
                </span>
                {section.detail ? (
                  <span className="text-xs text-slate-500 sm:text-right">{section.detail}</span>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}

      {exportStatus ? (
        <p className={`mt-3 text-xs ${exportStatus.includes("failed") ? "text-rose-600" : "text-emerald-600"}`}>
          {exportStatus}
        </p>
      ) : null}
    </div>
  );
}
