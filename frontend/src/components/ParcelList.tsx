"use client";

import { useEffect, useState } from "react";
import { listParcels, type ParcelItem } from "@/lib/api";

type Props = {
  projectId?: string;
  onSelectParcel?: (parcelId: string) => void;
};

export function ParcelList({ projectId, onSelectParcel }: Props) {
  const [parcels, setParcels] = useState<ParcelItem[] | null>(null);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Filters
  const [stageFilter, setStageFilter] = useState<string>("");
  const [minRisk, setMinRisk] = useState<string>("");

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const params: Parameters<typeof listParcels>[0] = {};
      if (projectId) params.project_id = projectId;
      if (stageFilter) params.stage = stageFilter;
      if (minRisk && !isNaN(Number(minRisk))) params.min_risk = Number(minRisk);

      const res = await listParcels(params);
      setParcels(res.items);
      setTotal(res.total);
    } catch (e) {
      setError(String(e));
      setParcels(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, [projectId, stageFilter, minRisk]);

  function riskColor(score: number): string {
    if (score >= 70) return "text-rose-600 bg-rose-50";
    if (score >= 40) return "text-amber-600 bg-amber-50";
    return "text-emerald-600 bg-emerald-50";
  }

  function stageLabel(stage: string): string {
    const labels: Record<string, string> = {
      intake: "Intake",
      appraisal: "Appraisal",
      offer_pending: "Offer Pending",
      offer_sent: "Offer Sent",
      negotiation: "Negotiation",
      closing: "Closing",
      litigation: "Litigation",
      closed: "Closed",
    };
    return labels[stage] ?? stage;
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold">Parcels</h3>
          <p className="text-sm text-slate-500">{total} total</p>
        </div>
        <button
          onClick={refresh}
          disabled={loading}
          className="text-sm text-brand hover:underline disabled:opacity-50"
        >
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <select
          value={stageFilter}
          onChange={(e) => setStageFilter(e.target.value)}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm"
        >
          <option value="">All stages</option>
          <option value="intake">Intake</option>
          <option value="appraisal">Appraisal</option>
          <option value="offer_pending">Offer Pending</option>
          <option value="offer_sent">Offer Sent</option>
          <option value="negotiation">Negotiation</option>
          <option value="closing">Closing</option>
          <option value="litigation">Litigation</option>
          <option value="closed">Closed</option>
        </select>
        <input
          type="number"
          placeholder="Min risk score"
          value={minRisk}
          onChange={(e) => setMinRisk(e.target.value)}
          className="w-32 rounded-md border border-slate-300 px-3 py-1.5 text-sm"
        />
      </div>

      {error && <p className="text-sm text-rose-600 mb-3">{error}</p>}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-slate-500 border-b">
              <th className="py-2 pr-4">Parcel ID</th>
              <th className="py-2 pr-4">Stage</th>
              <th className="py-2 pr-4">Risk</th>
              <th className="py-2">Deadline</th>
            </tr>
          </thead>
          <tbody>
            {(parcels ?? []).map((parcel) => (
              <tr
                key={parcel.id}
                className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer"
                onClick={() => onSelectParcel?.(parcel.id)}
              >
                <td className="py-2.5 pr-4 font-medium text-slate-900">{parcel.id}</td>
                <td className="py-2.5 pr-4">
                  <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                    {stageLabel(parcel.stage)}
                  </span>
                </td>
                <td className="py-2.5 pr-4">
                  <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${riskColor(parcel.risk_score)}`}>
                    {parcel.risk_score}
                  </span>
                </td>
                <td className="py-2.5 text-slate-600">
                  {parcel.next_deadline_at
                    ? new Date(parcel.next_deadline_at).toLocaleDateString()
                    : "—"}
                </td>
              </tr>
            ))}
            {parcels?.length === 0 && (
              <tr>
                <td colSpan={4} className="py-6 text-center text-slate-500">
                  No parcels found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

