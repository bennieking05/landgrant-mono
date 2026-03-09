"use client";

import { useEffect, useState, useCallback } from "react";
import { apiGet } from "@/lib/api";
import { LoadingSpinner, ErrorMessage, EmptyState } from "@/components/ui";
import { Scale } from "lucide-react";

type RuleItem = { id: string; rule_id: string; citation: string; fired: boolean };

export function RuleResults({ parcelId }: { parcelId: string }) {
  const [results, setResults] = useState<RuleItem[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet<{ items: RuleItem[] }>(`/rules/results?parcel_id=${encodeURIComponent(parcelId)}`, "land_agent");
      setResults(data.items);
    } catch (e) {
      setResults(null);
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [parcelId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Rule engine</h3>
        <button
          onClick={refresh}
          disabled={loading}
          className="text-sm text-brand hover:underline disabled:opacity-50"
        >
          Refresh
        </button>
      </div>

      {loading && (
        <div className="mt-4">
          <LoadingSpinner text="Evaluating rules..." />
        </div>
      )}

      {error && (
        <div className="mt-4">
          <ErrorMessage message="Failed to load rules" onRetry={refresh} />
        </div>
      )}

      {!loading && !error && results?.length === 0 && (
        <EmptyState
          icon={Scale}
          message="No rules evaluated yet"
          className="mt-4"
        />
      )}

      {!loading && !error && results && results.length > 0 && (
        <ul className="mt-4 space-y-2 text-sm">
          {results.map((result) => (
            <li key={result.id ?? result.rule_id} className="flex items-center justify-between">
              <div>
                <p className="font-medium text-slate-900">{result.rule_id}</p>
                <p className="text-slate-600">{result.citation}</p>
              </div>
              <span className={`text-xs font-semibold ${result.fired ? "text-emerald-600" : "text-slate-400"}`}>
                {result.fired ? "Fired" : "Not triggered"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}



