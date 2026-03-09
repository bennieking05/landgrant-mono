"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPostJson } from "@/lib/api";

export function DecisionActions({ parcelId }: { parcelId: string }) {
  const [actions, setActions] = useState<string[]>([]);
  const [selection, setSelection] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    apiGet<{ options: string[] }>("/portal/decision/options", "landowner")
      .then((d) => setActions(d.options))
      .catch((e) => setStatus(`Failed to load options: ${String(e)}`));
  }, []);

  async function choose(action: string) {
    setSelection(action);
    setStatus("Submitting decision...");
    try {
      const res = await apiPostJson<{ routed_to: string; decision_id: string }>(
        "/portal/decision",
        { parcel_id: parcelId, selection: action },
        "landowner",
      );
      setStatus(`Decision routed to ${res.routed_to} (${res.decision_id})`);
    } catch (e) {
      setStatus(`Decision failed: ${String(e)}`);
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h3 className="text-lg font-semibold">Decision & e-sign</h3>
      <p className="mt-2 text-sm text-slate-600">
        Landowner picks Accept / Counter / Request Call; counters route to agent queue with SLA timers.
      </p>
      <div className="mt-4 flex gap-2">
        {actions.map((action) => (
          <button
            key={action}
            onClick={() => choose(action)}
            className={`flex-1 rounded-md border px-3 py-2 text-sm font-medium ${
              selection === action ? "border-brand bg-brand/10 text-brand" : "border-slate-300 text-slate-700"
            }`}
          >
            {action}
          </button>
        ))}
      </div>
      {status && <p className="mt-3 text-sm text-slate-600">{status}</p>}
    </div>
  );
}



