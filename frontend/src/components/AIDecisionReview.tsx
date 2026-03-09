import { useState, useEffect } from "react";
import {
  listEscalations,
  getEscalation,
  resolveEscalation,
  type EscalationItem,
  type EscalationDetail,
} from "@/lib/api";

const PRIORITY_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-800 border-red-300",
  high: "bg-orange-100 text-orange-800 border-orange-300",
  medium: "bg-yellow-100 text-yellow-800 border-yellow-300",
  low: "bg-gray-100 text-gray-800 border-gray-300",
};

const STATUS_COLORS: Record<string, string> = {
  open: "bg-blue-100 text-blue-800",
  in_review: "bg-purple-100 text-purple-800",
  resolved: "bg-green-100 text-green-800",
};

const REASON_LABELS: Record<string, string> = {
  low_confidence: "Low Confidence",
  high_risk_flag: "High Risk Flag",
  cross_verification_disagreement: "Cross-Verification Disagreement",
  constitutional_issue: "Constitutional Issue",
  litigation_required: "Litigation Required",
  edge_case_detected: "Edge Case Detected",
  compliance_violation: "Compliance Violation",
  system_error: "System Error",
};

export function AIDecisionReview() {
  const [escalations, setEscalations] = useState<EscalationItem[]>([]);
  const [selectedEscalation, setSelectedEscalation] = useState<EscalationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [resolving, setResolving] = useState(false);
  const [resolution, setResolution] = useState("");
  const [outcome, setOutcome] = useState("approved");
  const [filter, setFilter] = useState<"all" | "open" | "resolved">("open");

  useEffect(() => {
    loadEscalations();
  }, [filter]);

  async function loadEscalations() {
    setLoading(true);
    try {
      const status = filter === "all" ? undefined : filter;
      const data = await listEscalations({ status });
      setEscalations(data);
    } catch (err) {
      console.error("Failed to load escalations:", err);
    } finally {
      setLoading(false);
    }
  }

  async function handleSelectEscalation(id: string) {
    try {
      const detail = await getEscalation(id);
      setSelectedEscalation(detail);
      setResolution("");
      setOutcome("approved");
    } catch (err) {
      console.error("Failed to load escalation:", err);
    }
  }

  async function handleResolve() {
    if (!selectedEscalation || !resolution) return;
    
    setResolving(true);
    try {
      await resolveEscalation(selectedEscalation.id, { resolution, outcome });
      await loadEscalations();
      setSelectedEscalation(null);
    } catch (err) {
      console.error("Failed to resolve escalation:", err);
    } finally {
      setResolving(false);
    }
  }

  const openCount = escalations.filter(e => e.status === "open").length;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">AI Decision Review</h2>
          <p className="text-sm text-slate-500">
            Review and approve AI agent decisions requiring human oversight
          </p>
        </div>
        {openCount > 0 && (
          <span className="inline-flex items-center rounded-full bg-red-100 px-3 py-1 text-sm font-medium text-red-800">
            {openCount} pending
          </span>
        )}
      </div>

      {/* Filter tabs */}
      <div className="mt-4 flex space-x-2 border-b border-slate-200">
        <button
          onClick={() => setFilter("open")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            filter === "open"
              ? "border-brand text-brand"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          Open
        </button>
        <button
          onClick={() => setFilter("resolved")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            filter === "resolved"
              ? "border-brand text-brand"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          Resolved
        </button>
        <button
          onClick={() => setFilter("all")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            filter === "all"
              ? "border-brand text-brand"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          All
        </button>
      </div>

      {loading ? (
        <div className="mt-6 text-center text-slate-500">Loading...</div>
      ) : escalations.length === 0 ? (
        <div className="mt-6 text-center text-slate-500">
          No escalations {filter !== "all" ? `with status "${filter}"` : ""}
        </div>
      ) : (
        <div className="mt-4 divide-y divide-slate-100">
          {escalations.map((esc) => (
            <div
              key={esc.id}
              onClick={() => handleSelectEscalation(esc.id)}
              className={`cursor-pointer p-4 transition-colors hover:bg-slate-50 ${
                selectedEscalation?.id === esc.id ? "bg-slate-50" : ""
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <span className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium border ${PRIORITY_COLORS[esc.priority] || PRIORITY_COLORS.medium}`}>
                      {esc.priority.toUpperCase()}
                    </span>
                    <span className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[esc.status] || STATUS_COLORS.open}`}>
                      {esc.status}
                    </span>
                    <span className="text-sm font-medium text-slate-700">
                      {REASON_LABELS[esc.reason] || esc.reason}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-slate-500 line-clamp-1">
                    {esc.context_summary || "No context available"}
                  </p>
                </div>
                <div className="ml-4 text-xs text-slate-400">
                  {new Date(esc.created_at).toLocaleDateString()}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Detail panel */}
      {selectedEscalation && (
        <div className="mt-6 rounded-lg border border-slate-200 bg-slate-50 p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-700">
              Escalation Details
            </h3>
            <button
              onClick={() => setSelectedEscalation(null)}
              className="text-sm text-slate-400 hover:text-slate-600"
            >
              Close
            </button>
          </div>

          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <div>
              <label className="text-xs font-medium uppercase text-slate-500">
                Agent Type
              </label>
              <p className="text-sm text-slate-800">
                {selectedEscalation.ai_decision.agent_type}
              </p>
            </div>
            <div>
              <label className="text-xs font-medium uppercase text-slate-500">
                Confidence
              </label>
              <p className="text-sm text-slate-800">
                {(selectedEscalation.ai_decision.confidence * 100).toFixed(0)}%
              </p>
            </div>
          </div>

          {selectedEscalation.ai_decision.explanation && (
            <div className="mt-4">
              <label className="text-xs font-medium uppercase text-slate-500">
                AI Explanation
              </label>
              <p className="mt-1 text-sm text-slate-700 bg-white rounded p-3 border border-slate-200">
                {selectedEscalation.ai_decision.explanation}
              </p>
            </div>
          )}

          {selectedEscalation.ai_decision.flags.length > 0 && (
            <div className="mt-4">
              <label className="text-xs font-medium uppercase text-slate-500">
                Flags
              </label>
              <div className="mt-1 flex flex-wrap gap-2">
                {selectedEscalation.ai_decision.flags.map((flag) => (
                  <span
                    key={flag}
                    className="inline-flex items-center rounded bg-amber-100 px-2 py-1 text-xs font-medium text-amber-800"
                  >
                    {flag.replace(/_/g, " ")}
                  </span>
                ))}
              </div>
            </div>
          )}

          {selectedEscalation.status === "open" && (
            <div className="mt-6 border-t border-slate-200 pt-4">
              <h4 className="text-sm font-medium text-slate-700">
                Resolve Escalation
              </h4>
              
              <div className="mt-3">
                <label className="text-xs font-medium text-slate-500">
                  Outcome
                </label>
                <div className="mt-1 flex space-x-4">
                  {["approved", "rejected", "modified"].map((opt) => (
                    <label key={opt} className="flex items-center space-x-2">
                      <input
                        type="radio"
                        name="outcome"
                        value={opt}
                        checked={outcome === opt}
                        onChange={(e) => setOutcome(e.target.value)}
                        className="text-brand focus:ring-brand"
                      />
                      <span className="text-sm capitalize">{opt}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="mt-3">
                <label className="text-xs font-medium text-slate-500">
                  Resolution Notes
                </label>
                <textarea
                  value={resolution}
                  onChange={(e) => setResolution(e.target.value)}
                  placeholder="Enter resolution notes..."
                  rows={3}
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-brand focus:ring-1 focus:ring-brand"
                />
              </div>

              <div className="mt-4 flex justify-end space-x-3">
                <button
                  onClick={() => setSelectedEscalation(null)}
                  className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleResolve}
                  disabled={!resolution || resolving}
                  className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand/90 disabled:opacity-50"
                >
                  {resolving ? "Resolving..." : "Resolve"}
                </button>
              </div>
            </div>
          )}

          {selectedEscalation.status === "resolved" && selectedEscalation.resolution && (
            <div className="mt-4 border-t border-slate-200 pt-4">
              <label className="text-xs font-medium uppercase text-slate-500">
                Resolution
              </label>
              <p className="mt-1 text-sm text-slate-700">
                {selectedEscalation.resolution}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
