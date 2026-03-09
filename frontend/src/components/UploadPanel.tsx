"use client";

import { useEffect, useState, useCallback } from "react";
import { apiGet, apiPostForm } from "@/lib/api";
import { LoadingSpinner, ErrorMessage, EmptyState } from "@/components/ui";
import { Upload, FileText } from "lucide-react";

type UploadItem = {
  id: string;
  filename: string;
  size_bytes: number;
  uploaded_at: string;
};

export function UploadPanel({ parcelId }: { parcelId: string }) {
  const [items, setItems] = useState<UploadItem[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiGet<{ items: UploadItem[] }>(`/portal/uploads?parcel_id=${encodeURIComponent(parcelId)}`, "landowner");
      setItems(res.items);
    } catch (e) {
      setError(String(e));
      setItems(null);
    } finally {
      setLoading(false);
    }
  }, [parcelId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function handleFiles(list: FileList | null) {
    if (!list) return;
    setUploading(true);
    setUploadStatus(null);
    try {
      for (const file of Array.from(list)) {
        const form = new FormData();
        form.set("parcel_id", parcelId);
        form.set("file", file);
        await apiPostForm("/portal/uploads", form, "landowner");
      }
      setUploadStatus("Upload complete");
      await refresh();
    } catch (e) {
      setUploadStatus(`Upload failed: ${String(e)}`);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h3 className="text-lg font-semibold">Chat & uploads</h3>
      <p className="mt-2 text-sm text-slate-600">POA, W-9, photos — virus scanned, hashed, exported to binder.</p>

      <label className={`mt-4 flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-4 py-8 text-sm transition-colors ${uploading ? "border-brand bg-brand/5" : "border-slate-300 hover:border-brand hover:bg-slate-50"}`}>
        <input type="file" multiple className="hidden" onChange={(e) => handleFiles(e.target.files)} disabled={uploading} />
        <Upload className={`h-6 w-6 mb-2 ${uploading ? "text-brand animate-pulse" : "text-slate-400"}`} />
        {uploading ? "Uploading..." : "Drop files or click to upload"}
      </label>

      {uploadStatus && (
        <p className={`mt-2 text-xs ${uploadStatus.includes("failed") ? "text-rose-600" : "text-emerald-600"}`}>
          {uploadStatus}
        </p>
      )}

      {loading && (
        <div className="mt-4">
          <LoadingSpinner text="Loading uploads..." />
        </div>
      )}

      {error && (
        <div className="mt-4">
          <ErrorMessage message="Failed to load uploads" onRetry={refresh} />
        </div>
      )}

      {!loading && !error && items?.length === 0 && (
        <EmptyState
          icon={FileText}
          message="No files uploaded yet"
          className="mt-4"
        />
      )}

      {!loading && !error && items && items.length > 0 && (
        <ul className="mt-4 space-y-2 text-sm">
          {items.map((item) => (
            <li key={item.id} className="flex items-center justify-between">
              <span className="truncate">{item.filename}</span>
              <span className="text-xs text-slate-500 flex-shrink-0 ml-2">{(item.size_bytes / 1_000_000).toFixed(1)} MB</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}



