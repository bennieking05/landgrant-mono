"use client";

import { useState } from "react";
import { getRoutePlan, type RoutePlanResponse } from "@/lib/api";

type Props = {
  projectId: string;
};

export function RoutePlanPanel({ projectId }: Props) {
  const [plan, setPlan] = useState<RoutePlanResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function generatePlan() {
    setLoading(true);
    setError(null);
    try {
      const res = await getRoutePlan(projectId);
      setPlan(res);
    } catch (e) {
      setError(String(e));
      setPlan(null);
    } finally {
      setLoading(false);
    }
  }

  function downloadCsv() {
    if (!plan?.csv) return;
    const blob = new Blob([plan.csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${projectId}-route-plan.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold">Route Planning</h3>
          <p className="text-sm text-slate-500">
            Optimized parcel visit order based on risk and deadlines
          </p>
        </div>
        <button
          onClick={generatePlan}
          disabled={loading}
          className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {loading ? "Generating..." : "Generate Route"}
        </button>
      </div>

      {error && <p className="text-sm text-rose-600 mb-3">{error}</p>}

      {plan && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-600">
              {plan.parcel_ids.length} parcels in optimized order
            </p>
            <button
              onClick={downloadCsv}
              className="text-sm text-brand hover:underline"
            >
              Download CSV
            </button>
          </div>

          <div className="bg-slate-50 rounded-lg p-4 max-h-64 overflow-y-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-600 border-b border-slate-200">
                  <th className="pb-2 pr-4">Stop #</th>
                  <th className="pb-2">Parcel ID</th>
                </tr>
              </thead>
              <tbody>
                {plan.parcel_ids.map((parcelId, idx) => (
                  <tr
                    key={parcelId}
                    className="border-b border-slate-100 last:border-0"
                  >
                    <td className="py-2 pr-4 font-medium text-slate-900">
                      {idx + 1}
                    </td>
                    <td className="py-2 font-mono text-slate-700">{parcelId}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!plan && !loading && (
        <div className="text-center py-8 text-slate-400 text-sm">
          Click "Generate Route" to create an optimized visit plan
        </div>
      )}
    </div>
  );
}
