"use client";

import { useEffect, useState, useCallback } from "react";
import { apiGet } from "@/lib/api";
import { LoadingSpinner, ErrorMessage, EmptyState } from "@/components/ui";
import { ListChecks } from "lucide-react";

type ChecklistItem = { label: string; done: boolean };

export function PacketChecklist({ parcelId }: { parcelId: string }) {
  const [items, setItems] = useState<ChecklistItem[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(() => {
    setLoading(true);
    setError(null);
    apiGet<{ items: ChecklistItem[] }>(`/packet/checklist?parcel_id=${encodeURIComponent(parcelId)}`, "land_agent")
      .then((d) => setItems(d.items))
      .catch((e) => {
        setItems(null);
        setError(String(e));
      })
      .finally(() => setLoading(false));
  }, [parcelId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h3 className="text-lg font-semibold">Pre-offer packet</h3>

      {loading && (
        <div className="mt-4">
          <LoadingSpinner text="Loading checklist..." />
        </div>
      )}

      {error && (
        <div className="mt-4">
          <ErrorMessage message="Failed to load checklist" onRetry={fetchData} />
        </div>
      )}

      {!loading && !error && items?.length === 0 && (
        <EmptyState
          icon={ListChecks}
          message="No checklist items"
          className="mt-4"
        />
      )}

      {!loading && !error && items && items.length > 0 && (
        <ul className="mt-4 space-y-2 text-sm">
          {items.map((item) => (
            <li key={item.label} className="flex items-center gap-2">
              <span className={`h-3 w-3 rounded-full ${item.done ? "bg-emerald-500" : "bg-slate-300"}`} />
              <span className={item.done ? "text-slate-700" : "text-slate-500"}>{item.label}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}



