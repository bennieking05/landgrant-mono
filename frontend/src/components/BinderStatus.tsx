"use client";

import { useEffect, useState, useCallback } from "react";
import { apiGet, apiPostJson } from "@/lib/api";
import { LoadingSpinner, ErrorMessage, EmptyState } from "@/components/ui";
import { FolderOpen } from "lucide-react";

type BinderSection = { name: string; status: string };

export function BinderStatus({ projectId }: { projectId: string }) {
  const [sections, setSections] = useState<BinderSection[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exportStatus, setExportStatus] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiGet<{ sections: BinderSection[] }>(
        `/binder/status?project_id=${encodeURIComponent(projectId)}`,
        "in_house_counsel",
      );
      setSections(res.sections);
    } catch (e) {
      setSections(null);
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function exportBinder() {
    setExporting(true);
    setExportStatus(null);
    try {
      const data = await apiPostJson<{ bundle_id: string; storage_path: string }>("/workflows/binder/export", {}, "in_house_counsel");
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
        <h3 className="text-lg font-semibold">Good-Faith Binder</h3>
        <button
          onClick={exportBinder}
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
            <li key={section.name} className="flex items-center justify-between">
              <span>{section.name}</span>
              <span className={`text-xs font-medium ${section.status === "Complete" ? "text-emerald-600" : "text-amber-600"}`}>
                {section.status}
              </span>
            </li>
          ))}
        </ul>
      )}

      {exportStatus && (
        <p className={`mt-3 text-xs ${exportStatus.includes("failed") ? "text-rose-600" : "text-emerald-600"}`}>
          {exportStatus}
        </p>
      )}
    </div>
  );
}



