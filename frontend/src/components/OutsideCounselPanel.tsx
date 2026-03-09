"use client";

import { useEffect, useState } from "react";
import { getRepositoryCompleteness, initiateCase, type RepositoryCompletenessResponse } from "@/lib/api";

type Props = {
  projectId: string;
  parcelId?: string;
};

export function OutsideCounselPanel({ projectId, parcelId = "PARCEL-001" }: Props) {
  const [completeness, setCompleteness] = useState<RepositoryCompletenessResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Initiate form
  const [showInitiate, setShowInitiate] = useState(false);
  const [templateId, setTemplateId] = useState("fol");
  const [initiating, setInitiating] = useState(false);
  const [initiateResult, setInitiateResult] = useState<{ draft_id: string; docket_number: string } | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const res = await getRepositoryCompleteness(projectId);
      setCompleteness(res);
    } catch (e) {
      setError(String(e));
      setCompleteness(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, [projectId]);

  async function handleInitiate() {
    setInitiating(true);
    setError(null);
    try {
      const res = await initiateCase({
        project_id: projectId,
        parcel_id: parcelId,
        template_id: templateId,
      });
      setInitiateResult(res);
      setShowInitiate(false);
    } catch (e) {
      setError(String(e));
    } finally {
      setInitiating(false);
    }
  }

  function checkIcon(passed: boolean) {
    return passed ? (
      <svg className="w-5 h-5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
    ) : (
      <svg className="w-5 h-5 text-rose-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
      </svg>
    );
  }

  function checkLabel(key: string): string {
    const labels: Record<string, string> = {
      binder_exported: "Binder Exported",
      title_attached: "Title Documents Attached",
      appraisal_attached: "Appraisal Attached",
    };
    return labels[key] ?? key.replace(/_/g, " ");
  }

  const isReady = completeness?.percent === 100;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold">Outside Counsel Handoff</h3>
          <p className="text-sm text-slate-500">Project: {projectId}</p>
        </div>
        <button
          onClick={refresh}
          disabled={loading}
          className="text-sm text-brand hover:underline disabled:opacity-50"
        >
          Refresh
        </button>
      </div>

      {error && <p className="text-sm text-rose-600 mb-3">{error}</p>}
      {loading && <p className="text-sm text-slate-500 mb-3">Checking repository...</p>}

      {completeness && (
        <>
          {/* Progress bar */}
          <div className="mb-4">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium text-slate-700">Repository Completeness</span>
              <span className={`text-sm font-semibold ${completeness.percent === 100 ? "text-emerald-600" : "text-amber-600"}`}>
                {completeness.percent}%
              </span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all ${completeness.percent === 100 ? "bg-emerald-500" : "bg-amber-500"}`}
                style={{ width: `${completeness.percent}%` }}
              />
            </div>
          </div>

          {/* Checklist */}
          <div className="space-y-2 mb-4">
            {Object.entries(completeness.checks).map(([key, passed]) => (
              <div key={key} className="flex items-center gap-3 py-2 px-3 bg-slate-50 rounded">
                {checkIcon(passed)}
                <span className={`text-sm ${passed ? "text-slate-700" : "text-slate-500"}`}>
                  {checkLabel(key)}
                </span>
              </div>
            ))}
          </div>

          {/* Missing items */}
          {completeness.missing.length > 0 && (
            <div className="mb-4 p-3 bg-amber-50 rounded-lg">
              <p className="text-sm font-medium text-amber-800">Missing items:</p>
              <ul className="mt-1 text-sm text-amber-700">
                {completeness.missing.map((item) => (
                  <li key={item}>• {checkLabel(item)}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Initiate button */}
          {!showInitiate && !initiateResult && (
            <button
              onClick={() => setShowInitiate(true)}
              disabled={!isReady}
              className={`w-full rounded-md px-4 py-2 text-sm font-medium ${
                isReady
                  ? "bg-brand text-white hover:bg-brand/90"
                  : "bg-slate-200 text-slate-500 cursor-not-allowed"
              }`}
            >
              {isReady ? "Initiate Outside Counsel Case" : "Complete repository to proceed"}
            </button>
          )}

          {/* Initiate form */}
          {showInitiate && (
            <div className="p-4 bg-slate-50 rounded-lg space-y-3">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Template ID</label>
                <select
                  value={templateId}
                  onChange={(e) => setTemplateId(e.target.value)}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                >
                  <option value="fol">FOL (Final Offer Letter)</option>
                  <option value="petition">Petition</option>
                  <option value="motion">Motion</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Parcel ID</label>
                <input
                  type="text"
                  value={parcelId}
                  disabled
                  className="w-full rounded-md border border-slate-300 bg-slate-100 px-3 py-2 text-sm text-slate-500"
                />
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleInitiate}
                  disabled={initiating}
                  className="flex-1 rounded-md bg-brand px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
                >
                  {initiating ? "Initiating..." : "Confirm Initiation"}
                </button>
                <button
                  onClick={() => setShowInitiate(false)}
                  className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Success result */}
          {initiateResult && (
            <div className="p-4 bg-emerald-50 rounded-lg">
              <p className="text-sm font-medium text-emerald-800">Case Initiated Successfully</p>
              <div className="mt-2 text-sm text-emerald-700">
                <p>Draft ID: <span className="font-mono">{initiateResult.draft_id}</span></p>
                <p>Docket: <span className="font-mono">{initiateResult.docket_number}</span></p>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

