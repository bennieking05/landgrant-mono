"use client";

import { useEffect, useState, useCallback } from "react";
import { apiGet } from "@/lib/api";
import { LoadingSpinner, ErrorMessage } from "@/components/ui";

type BudgetSummary = {
  project_id: string;
  cap_amount: number;
  actual_amount: number;
  utilization_pct: number;
  alerts: string[];
};

export function BudgetPanel({ projectId }: { projectId: string }) {
  const [data, setData] = useState<BudgetSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(() => {
    setLoading(true);
    setError(null);
    apiGet<BudgetSummary>(`/budgets/summary?project_id=${encodeURIComponent(projectId)}`, "in_house_counsel")
      .then((d) => setData(d))
      .catch((e) => {
        setData(null);
        setError(String(e));
      })
      .finally(() => setLoading(false));
  }, [projectId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const cap = data ? `$${Math.round(data.cap_amount / 1000)}k` : "—";
  const util = data ? `${data.utilization_pct}%` : "—";
  const alerts = data ? (data.alerts.length ? data.alerts.join(", ") : "None") : "—";

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h3 className="text-lg font-semibold">Budget & utilization</h3>

      {loading && (
        <div className="mt-4">
          <LoadingSpinner text="Loading budget..." />
        </div>
      )}

      {error && (
        <div className="mt-4">
          <ErrorMessage message="Failed to load budget" onRetry={fetchData} />
        </div>
      )}

      {!loading && !error && (
        <dl className="mt-4 space-y-2 text-sm">
          <div className="flex justify-between">
            <dt className="text-slate-600">Matter cap</dt>
            <dd className="font-medium text-slate-900">{cap}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-slate-600">Utilization</dt>
            <dd className="font-medium text-slate-900">{util}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-slate-600">Alerts</dt>
            <dd className="font-medium text-slate-900">{alerts}</dd>
          </div>
        </dl>
      )}
    </div>
  );
}



