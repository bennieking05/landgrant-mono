"use client";

import { useEffect, useState, useCallback } from "react";
import { apiGet } from "@/lib/api";
import { LoadingSpinner, ErrorMessage, EmptyState } from "@/components/ui";
import { MessageSquare } from "lucide-react";

type CommsItem = {
  id: string;
  ts: string | null;
  channel: string;
  summary: string | null;
  proof: unknown;
  status: string;
};

export function CommsLog({ parcelId }: { parcelId: string }) {
  const [items, setItems] = useState<CommsItem[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(() => {
    setLoading(true);
    setError(null);
    apiGet<{ items: CommsItem[] }>(`/communications?parcel_id=${encodeURIComponent(parcelId)}`, "land_agent")
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
      <h3 className="text-lg font-semibold">Comms log</h3>
      <p className="mt-2 text-sm text-slate-600">Includes email/SMS/certified mail per EminentAI backlog.</p>

      {loading && (
        <div className="mt-4">
          <LoadingSpinner text="Loading communications..." />
        </div>
      )}

      {error && (
        <div className="mt-4">
          <ErrorMessage message="Failed to load communications" onRetry={fetchData} />
        </div>
      )}

      {!loading && !error && items?.length === 0 && (
        <EmptyState
          icon={MessageSquare}
          message="No communications yet"
          className="mt-4"
        />
      )}

      {!loading && !error && items && items.length > 0 && (
        <ul className="mt-4 space-y-3">
          {items.map((event) => (
            <li key={event.id} className="flex items-start justify-between text-sm">
              <div>
                <p className="font-medium">{event.channel}</p>
                <p className="text-slate-600">{event.summary}</p>
              </div>
              <span className="text-xs text-slate-500">{event.ts ?? event.status}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}



