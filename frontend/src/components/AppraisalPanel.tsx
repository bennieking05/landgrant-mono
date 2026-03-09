"use client";

import { useEffect, useState } from "react";
import { getAppraisal, upsertAppraisal, type AppraisalData } from "@/lib/api";

type Props = {
  parcelId: string;
};

export function AppraisalPanel({ parcelId }: Props) {
  const [appraisal, setAppraisal] = useState<AppraisalData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Edit mode
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState("");
  const [summary, setSummary] = useState("");
  const [saving, setSaving] = useState(false);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const res = await getAppraisal(parcelId);
      setAppraisal(res.appraisal ?? null);
      if (res.appraisal) {
        setValue(res.appraisal.value?.toString() ?? "");
        setSummary(res.appraisal.summary ?? "");
      }
    } catch (e) {
      setError(String(e));
      setAppraisal(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, [parcelId]);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await upsertAppraisal({
        parcel_id: parcelId,
        value: value ? Number(value) : undefined,
        summary: summary || undefined,
        comps: appraisal?.comps ?? [],
      });
      setEditing(false);
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  }

  function formatCurrency(num?: number): string {
    if (num === undefined || num === null) return "—";
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    }).format(num);
  }

  function formatDate(isoDate?: string): string {
    if (!isoDate) return "—";
    return new Date(isoDate).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold">Appraisal</h3>
          <p className="text-sm text-slate-500">Parcel: {parcelId}</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={refresh}
            disabled={loading}
            className="text-sm text-slate-600 hover:text-brand disabled:opacity-50"
          >
            Refresh
          </button>
          {!editing && (
            <button
              onClick={() => setEditing(true)}
              className="rounded-md bg-brand px-3 py-1.5 text-sm font-medium text-white"
            >
              {appraisal ? "Edit" : "Add"}
            </button>
          )}
        </div>
      </div>

      {error && <p className="text-sm text-rose-600 mb-3">{error}</p>}
      {loading && <p className="text-sm text-slate-500 mb-3">Loading...</p>}

      {editing ? (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Appraised Value</label>
            <div className="relative">
              <span className="absolute left-3 top-2 text-slate-500">$</span>
              <input
                type="number"
                value={value}
                onChange={(e) => setValue(e.target.value)}
                className="w-full rounded-md border border-slate-300 pl-7 pr-3 py-2 text-sm"
                placeholder="350000"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Summary</label>
            <textarea
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              rows={4}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              placeholder="Appraisal methodology and key findings..."
            />
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleSave}
              disabled={saving}
              className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save"}
            </button>
            <button
              onClick={() => {
                setEditing(false);
                setValue(appraisal?.value?.toString() ?? "");
                setSummary(appraisal?.summary ?? "");
              }}
              className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : appraisal ? (
        <div className="space-y-4">
          <div className="flex items-baseline justify-between">
            <span className="text-sm text-slate-600">Appraised Value</span>
            <span className="text-2xl font-semibold text-slate-900">{formatCurrency(appraisal.value)}</span>
          </div>

          {appraisal.summary && (
            <div>
              <span className="text-sm font-medium text-slate-700">Summary</span>
              <p className="mt-1 text-sm text-slate-600">{appraisal.summary}</p>
            </div>
          )}

          {appraisal.completed_at && (
            <p className="text-xs text-slate-500">
              Completed: {formatDate(appraisal.completed_at)}
            </p>
          )}

          {appraisal.comps && appraisal.comps.length > 0 && (
            <div>
              <span className="text-sm font-medium text-slate-700">Comparable Sales</span>
              <ul className="mt-2 space-y-2">
                {appraisal.comps.map((comp, idx) => (
                  <li key={idx} className="flex justify-between text-sm py-2 border-b border-slate-100 last:border-0">
                    <span className="text-slate-700">{String(comp.address ?? `Comp ${idx + 1}`)}</span>
                    <span className="text-slate-900 font-medium">
                      {formatCurrency(comp.sale_price as number | undefined)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : (
        <div className="py-6 text-center text-slate-500">
          No appraisal data available for this parcel
        </div>
      )}
    </div>
  );
}

