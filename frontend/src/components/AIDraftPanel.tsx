"use client";

import { useState } from "react";
import { generateDraft, type AIDraftResponse } from "@/lib/api";

type Props = {
  jurisdiction?: string;
  parcelId?: string;
};

export function AIDraftPanel({ jurisdiction = "TX", parcelId }: Props) {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AIDraftResponse | null>(null);

  // Payload fields
  const [assessedValue, setAssessedValue] = useState("300000");
  const [disputeLevel, setDisputeLevel] = useState<"LOW" | "MEDIUM" | "HIGH">("LOW");

  async function handleGenerate() {
    setLoading(true);
    setError(null);
    try {
      const res = await generateDraft({
        jurisdiction,
        payload: {
          "parcel.assessed_value": Number(assessedValue) || 0,
          "case.dispute_level": disputeLevel,
          "parcel.id": parcelId ?? "PARCEL-001",
        },
      });
      setResult(res);
    } catch (e) {
      setError(String(e));
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-4">
        <h3 className="text-lg font-semibold">AI Draft Generator</h3>
        <p className="text-sm text-slate-500">
          Generate attorney-reviewed draft documents using rule engine + AI pipeline
        </p>
      </div>

      {/* Input form */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Jurisdiction</label>
          <input
            type="text"
            value={jurisdiction}
            disabled
            className="w-full rounded-md border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Parcel ID</label>
          <input
            type="text"
            value={parcelId ?? "PARCEL-001"}
            disabled
            className="w-full rounded-md border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Assessed Value</label>
          <div className="relative">
            <span className="absolute left-3 top-2 text-slate-500">$</span>
            <input
              type="number"
              value={assessedValue}
              onChange={(e) => setAssessedValue(e.target.value)}
              className="w-full rounded-md border border-slate-300 pl-7 pr-3 py-2 text-sm"
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Dispute Level</label>
          <select
            value={disputeLevel}
            onChange={(e) => setDisputeLevel(e.target.value as "LOW" | "MEDIUM" | "HIGH")}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="LOW">Low</option>
            <option value="MEDIUM">Medium</option>
            <option value="HIGH">High</option>
          </select>
        </div>
      </div>

      <button
        onClick={handleGenerate}
        disabled={loading}
        className="w-full rounded-md bg-brand px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
      >
        {loading ? "Generating..." : "Generate Draft"}
      </button>

      {error && <p className="text-sm text-rose-600 mt-3">{error}</p>}

      {result && (
        <div className="mt-4 space-y-4">
          {/* Summary */}
          <div className="p-4 bg-slate-50 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-slate-700">Template</span>
              <span className="text-sm font-semibold text-slate-900">{result.template_id.toUpperCase()}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-slate-700">Rationale</span>
              <span className={`text-sm font-medium ${result.rationale === "Rules satisfied" ? "text-emerald-600" : "text-amber-600"}`}>
                {result.rationale}
              </span>
            </div>
          </div>

          {/* Rule Results */}
          {result.rule_results.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-slate-700 mb-2">Rule Evaluation</h4>
              <ul className="space-y-2">
                {result.rule_results.map((rule, idx) => (
                  <li key={idx} className="flex items-center justify-between py-2 px-3 bg-slate-50 rounded">
                    <span className="text-sm text-slate-700">{rule.rule_id}</span>
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                      rule.fired ? "bg-emerald-100 text-emerald-700" : "bg-slate-200 text-slate-600"
                    }`}>
                      {rule.fired ? "Fired" : "Not Triggered"}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Suggestions */}
          {result.suggestions.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-slate-700 mb-2">AI Suggestions</h4>
              <ul className="space-y-1">
                {result.suggestions.map((suggestion, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-slate-600">
                    <span className="text-brand mt-0.5">•</span>
                    <span>{suggestion}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Next Actions */}
          {result.next_actions.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-slate-700 mb-2">Recommended Next Actions</h4>
              <div className="flex flex-wrap gap-2">
                {result.next_actions.map((action, idx) => (
                  <span key={idx} className="inline-flex items-center rounded-full bg-brand/10 px-3 py-1 text-xs font-medium text-brand">
                    {action.replace(/_/g, " ")}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

