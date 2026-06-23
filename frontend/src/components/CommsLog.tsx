import { useEffect, useState, useCallback } from "react";
import { getCommunicationsFeed } from "@/lib/api";
import { LoadingSpinner, ErrorMessage, EmptyState } from "@/components/ui";
import { MessageSquare } from "lucide-react";

type CommsItem = {
  kind?: string;
  id: string;
  ts?: string | null;
  channel: string;
  summary?: string | null;
  proof: unknown;
  status?: string | null;
  parcel_id?: string | null;
};

type Props = {
  projectId: string;
  parcelId?: string | null;
};

export function CommsLog({ projectId, parcelId }: Props) {
  const [items, setItems] = useState<CommsItem[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(() => {
    setLoading(true);
    setError(null);
    getCommunicationsFeed(projectId, parcelId ?? undefined)
      .then((d) => setItems(d.items))
      .catch((e) => {
        setItems(null);
        setError(String(e));
      })
      .finally(() => setLoading(false));
  }, [projectId, parcelId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h3 className="text-lg font-semibold">Comms log</h3>
      <p className="mt-2 text-sm text-slate-600">
        Unified feed: outbound comms, notices, and service attempts (time-sorted).
      </p>

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
            <li key={`${event.kind ?? "row"}-${event.id}`} className="flex items-start justify-between gap-3 text-sm">
              <div className="min-w-0">
                <p className="font-medium">
                  {event.kind ? <span className="text-slate-500">{event.kind}</span> : null}{" "}
                  <span>{event.channel}</span>
                </p>
                <p className="text-slate-600 break-words">{event.summary}</p>
                {event.parcel_id ? (
                  <p className="mt-0.5 text-xs text-slate-500">Parcel {event.parcel_id}</p>
                ) : null}
              </div>
              <span className="shrink-0 text-xs text-slate-500">{event.ts ?? event.status ?? ""}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
