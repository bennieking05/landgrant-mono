"use client";

import { useState, useEffect, useCallback } from "react";
import {
  listAIDecisions,
  getAIDecision,
  listEscalations,
  getEscalation,
  resolveEscalation,
  type AIDecisionItem,
  type AIDecisionDetail,
  type EscalationItem,
  type EscalationDetail,
} from "@/lib/api";

// ============================================================================
// Types
// ============================================================================

type TabType = "decisions" | "escalations";
type DecisionFilter = "all" | "pending_review" | "reviewed";
type EscalationFilter = "all" | "open" | "resolved";

// ============================================================================
// Constants
// ============================================================================

const AGENT_TYPE_LABELS: Record<string, string> = {
  intake_agent: "Intake Agent",
  docgen_agent: "Document Generator",
  title_agent: "Title Analyst",
  orchestrator: "Orchestrator",
  workflow_engine: "Workflow Engine",
};

const AGENT_TYPE_ICONS: Record<string, string> = {
  intake_agent: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2",
  docgen_agent: "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
  title_agent: "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z",
  orchestrator: "M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z",
  workflow_engine: "M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15",
};

const PRIORITY_STYLES: Record<string, string> = {
  critical: "bg-rose-100 text-rose-800 border-rose-300",
  high: "bg-orange-100 text-orange-800 border-orange-300",
  medium: "bg-amber-100 text-amber-800 border-amber-300",
  low: "bg-slate-100 text-slate-800 border-slate-300",
};

// ============================================================================
// Component
// ============================================================================

export function AIDecisionDashboard() {
  const [activeTab, setActiveTab] = useState<TabType>("decisions");
  
  // Decisions state
  const [decisions, setDecisions] = useState<AIDecisionItem[]>([]);
  const [selectedDecision, setSelectedDecision] = useState<AIDecisionDetail | null>(null);
  const [decisionFilter, setDecisionFilter] = useState<DecisionFilter>("all");
  const [loadingDecisions, setLoadingDecisions] = useState(false);
  
  // Escalations state
  const [escalations, setEscalations] = useState<EscalationItem[]>([]);
  const [selectedEscalation, setSelectedEscalation] = useState<EscalationDetail | null>(null);
  const [escalationFilter, setEscalationFilter] = useState<EscalationFilter>("open");
  const [loadingEscalations, setLoadingEscalations] = useState(false);
  
  // Resolution state
  const [resolution, setResolution] = useState("");
  const [outcome, setOutcome] = useState("approved");
  const [resolving, setResolving] = useState(false);

  // ============================================================================
  // Data Loading
  // ============================================================================

  const loadDecisions = useCallback(async () => {
    setLoadingDecisions(true);
    try {
      const pendingReview = decisionFilter === "pending_review" ? true : 
                           decisionFilter === "reviewed" ? false : undefined;
      const data = await listAIDecisions({ pending_review: pendingReview, limit: 50 });
      setDecisions(data);
    } catch (err) {
      console.error("Failed to load decisions:", err);
    } finally {
      setLoadingDecisions(false);
    }
  }, [decisionFilter]);

  const loadEscalations = useCallback(async () => {
    setLoadingEscalations(true);
    try {
      const status = escalationFilter === "all" ? undefined : escalationFilter;
      const data = await listEscalations({ status });
      setEscalations(data);
    } catch (err) {
      console.error("Failed to load escalations:", err);
    } finally {
      setLoadingEscalations(false);
    }
  }, [escalationFilter]);

  useEffect(() => {
    if (activeTab === "decisions") {
      loadDecisions();
    } else {
      loadEscalations();
    }
  }, [activeTab, loadDecisions, loadEscalations]);

  // ============================================================================
  // Handlers
  // ============================================================================

  const handleSelectDecision = async (id: string) => {
    try {
      const detail = await getAIDecision(id);
      setSelectedDecision(detail);
    } catch (err) {
      console.error("Failed to load decision:", err);
    }
  };

  const handleSelectEscalation = async (id: string) => {
    try {
      const detail = await getEscalation(id);
      setSelectedEscalation(detail);
      setResolution("");
      setOutcome("approved");
    } catch (err) {
      console.error("Failed to load escalation:", err);
    }
  };

  const handleResolve = async () => {
    if (!selectedEscalation || !resolution) return;
    
    setResolving(true);
    try {
      await resolveEscalation(selectedEscalation.id, { resolution, outcome });
      await loadEscalations();
      setSelectedEscalation(null);
    } catch (err) {
      console.error("Failed to resolve:", err);
    } finally {
      setResolving(false);
    }
  };

  // ============================================================================
  // Helpers
  // ============================================================================

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.85) return "text-emerald-600 bg-emerald-50";
    if (confidence >= 0.7) return "text-amber-600 bg-amber-50";
    return "text-rose-600 bg-rose-50";
  };

  const getConfidenceLabel = (confidence: number) => {
    if (confidence >= 0.85) return "High";
    if (confidence >= 0.7) return "Medium";
    return "Low";
  };

  const formatDate = (date: string) => {
    return new Date(date).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  // Stats
  const pendingReviewCount = decisions.filter(d => !d.reviewed).length;
  const openEscalationCount = escalations.filter(e => e.status === "open").length;
  const avgConfidence = decisions.length > 0 
    ? decisions.reduce((acc, d) => acc + d.confidence, 0) / decisions.length 
    : 0;

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-200 bg-gradient-to-r from-purple-50 to-indigo-50">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">AI Decision Dashboard</h2>
            <p className="text-sm text-slate-500">Monitor and review all AI agent decisions</p>
          </div>
          <div className="flex items-center gap-4">
            {/* Stats */}
            <div className="flex items-center gap-6 px-4 py-2 bg-white rounded-lg border border-slate-200">
              <div className="text-center">
                <p className="text-2xl font-bold text-slate-900">{decisions.length}</p>
                <p className="text-xs text-slate-500">Total Decisions</p>
              </div>
              <div className="w-px h-8 bg-slate-200" />
              <div className="text-center">
                <p className={`text-2xl font-bold ${pendingReviewCount > 0 ? "text-amber-600" : "text-emerald-600"}`}>
                  {pendingReviewCount}
                </p>
                <p className="text-xs text-slate-500">Pending Review</p>
              </div>
              <div className="w-px h-8 bg-slate-200" />
              <div className="text-center">
                <p className="text-2xl font-bold text-purple-600">{(avgConfidence * 100).toFixed(0)}%</p>
                <p className="text-xs text-slate-500">Avg Confidence</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="px-6 border-b border-slate-200">
        <div className="flex gap-6">
          <button
            onClick={() => setActiveTab("decisions")}
            className={`py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === "decisions"
                ? "border-brand text-brand"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            AI Decisions
            {pendingReviewCount > 0 && (
              <span className="ml-2 px-2 py-0.5 text-xs bg-amber-100 text-amber-700 rounded-full">
                {pendingReviewCount}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab("escalations")}
            className={`py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === "escalations"
                ? "border-brand text-brand"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            Escalations
            {openEscalationCount > 0 && (
              <span className="ml-2 px-2 py-0.5 text-xs bg-rose-100 text-rose-700 rounded-full">
                {openEscalationCount}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex min-h-[500px]">
        {/* List Panel */}
        <div className="w-1/2 border-r border-slate-200">
          {activeTab === "decisions" ? (
            <>
              {/* Decision Filters */}
              <div className="px-4 py-3 border-b border-slate-100 flex items-center gap-2">
                <span className="text-xs text-slate-500">Filter:</span>
                {(["all", "pending_review", "reviewed"] as DecisionFilter[]).map((f) => (
                  <button
                    key={f}
                    onClick={() => setDecisionFilter(f)}
                    className={`px-3 py-1 text-xs rounded-full transition-colors ${
                      decisionFilter === f
                        ? "bg-brand text-white"
                        : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                    }`}
                  >
                    {f === "all" ? "All" : f === "pending_review" ? "Pending" : "Reviewed"}
                  </button>
                ))}
              </div>

              {/* Decision List */}
              <div className="overflow-y-auto max-h-[450px]">
                {loadingDecisions ? (
                  <div className="p-8 text-center text-slate-500">Loading...</div>
                ) : decisions.length === 0 ? (
                  <div className="p-8 text-center text-slate-500">No decisions found</div>
                ) : (
                  decisions.map((decision) => (
                    <button
                      key={decision.id}
                      onClick={() => handleSelectDecision(decision.id)}
                      className={`w-full text-left p-4 border-b border-slate-100 hover:bg-slate-50 transition-colors ${
                        selectedDecision?.id === decision.id ? "bg-purple-50" : ""
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        {/* Agent Icon */}
                        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center flex-shrink-0">
                          <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={AGENT_TYPE_ICONS[decision.agent_type] || AGENT_TYPE_ICONS.orchestrator} />
                          </svg>
                        </div>
                        
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <span className="font-medium text-slate-900">
                              {AGENT_TYPE_LABELS[decision.agent_type] || decision.agent_type}
                            </span>
                            <span className="text-xs text-slate-400">
                              {formatDate(decision.occurred_at)}
                            </span>
                          </div>
                          
                          <div className="flex items-center gap-2 mt-1">
                            {/* Confidence Badge */}
                            <span className={`px-2 py-0.5 text-xs font-medium rounded ${getConfidenceColor(decision.confidence)}`}>
                              {(decision.confidence * 100).toFixed(0)}% {getConfidenceLabel(decision.confidence)}
                            </span>
                            
                            {/* Review Status */}
                            {!decision.reviewed && (
                              <span className="px-2 py-0.5 text-xs font-medium rounded bg-amber-100 text-amber-700">
                                Needs Review
                              </span>
                            )}
                            {decision.reviewed && (
                              <span className="px-2 py-0.5 text-xs font-medium rounded bg-emerald-100 text-emerald-700">
                                {decision.review_outcome || "Reviewed"}
                              </span>
                            )}
                          </div>
                          
                          {/* Flags */}
                          {decision.flags.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-2">
                              {decision.flags.slice(0, 3).map((flag) => (
                                <span key={flag} className="text-xs px-1.5 py-0.5 bg-slate-100 text-slate-600 rounded">
                                  {flag.replace(/_/g, " ")}
                                </span>
                              ))}
                              {decision.flags.length > 3 && (
                                <span className="text-xs text-slate-400">+{decision.flags.length - 3}</span>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </>
          ) : (
            <>
              {/* Escalation Filters */}
              <div className="px-4 py-3 border-b border-slate-100 flex items-center gap-2">
                <span className="text-xs text-slate-500">Filter:</span>
                {(["open", "resolved", "all"] as EscalationFilter[]).map((f) => (
                  <button
                    key={f}
                    onClick={() => setEscalationFilter(f)}
                    className={`px-3 py-1 text-xs rounded-full transition-colors ${
                      escalationFilter === f
                        ? "bg-brand text-white"
                        : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                    }`}
                  >
                    {f.charAt(0).toUpperCase() + f.slice(1)}
                  </button>
                ))}
              </div>

              {/* Escalation List */}
              <div className="overflow-y-auto max-h-[450px]">
                {loadingEscalations ? (
                  <div className="p-8 text-center text-slate-500">Loading...</div>
                ) : escalations.length === 0 ? (
                  <div className="p-8 text-center text-slate-500">No escalations found</div>
                ) : (
                  escalations.map((esc) => (
                    <button
                      key={esc.id}
                      onClick={() => handleSelectEscalation(esc.id)}
                      className={`w-full text-left p-4 border-b border-slate-100 hover:bg-slate-50 transition-colors ${
                        selectedEscalation?.id === esc.id ? "bg-rose-50" : ""
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className={`px-2 py-0.5 text-xs font-medium rounded border ${PRIORITY_STYLES[esc.priority]}`}>
                              {esc.priority.toUpperCase()}
                            </span>
                            <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                              esc.status === "open" ? "bg-blue-100 text-blue-700" : "bg-emerald-100 text-emerald-700"
                            }`}>
                              {esc.status}
                            </span>
                          </div>
                          <p className="mt-1 text-sm font-medium text-slate-900">
                            {esc.reason.replace(/_/g, " ")}
                          </p>
                          <p className="mt-1 text-xs text-slate-500 line-clamp-1">
                            {esc.context_summary || "No context"}
                          </p>
                        </div>
                        <span className="text-xs text-slate-400">
                          {formatDate(esc.created_at)}
                        </span>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </>
          )}
        </div>

        {/* Detail Panel */}
        <div className="w-1/2 p-6 bg-slate-50">
          {activeTab === "decisions" && selectedDecision ? (
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-slate-900">Decision Details</h3>
                <button
                  onClick={() => setSelectedDecision(null)}
                  className="text-slate-400 hover:text-slate-600"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Confidence Gauge */}
              <div className="mb-6 p-4 bg-white rounded-lg border border-slate-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-slate-700">Confidence Score</span>
                  <span className={`text-2xl font-bold ${getConfidenceColor(selectedDecision.confidence).split(" ")[0]}`}>
                    {(selectedDecision.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="h-3 bg-slate-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      selectedDecision.confidence >= 0.85 ? "bg-emerald-500" :
                      selectedDecision.confidence >= 0.7 ? "bg-amber-500" : "bg-rose-500"
                    }`}
                    style={{ width: `${selectedDecision.confidence * 100}%` }}
                  />
                </div>
                <div className="flex justify-between mt-1 text-xs text-slate-400">
                  <span>0%</span>
                  <span>70% (threshold)</span>
                  <span>100%</span>
                </div>
              </div>

              {/* Details Grid */}
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="p-3 bg-white rounded-lg border border-slate-200">
                  <p className="text-xs text-slate-500 uppercase">Agent Type</p>
                  <p className="text-sm font-medium text-slate-900">
                    {AGENT_TYPE_LABELS[selectedDecision.agent_type] || selectedDecision.agent_type}
                  </p>
                </div>
                <div className="p-3 bg-white rounded-lg border border-slate-200">
                  <p className="text-xs text-slate-500 uppercase">Occurred</p>
                  <p className="text-sm font-medium text-slate-900">
                    {formatDate(selectedDecision.occurred_at)}
                  </p>
                </div>
                {selectedDecision.parcel_id && (
                  <div className="p-3 bg-white rounded-lg border border-slate-200">
                    <p className="text-xs text-slate-500 uppercase">Parcel ID</p>
                    <p className="text-sm font-medium text-slate-900">{selectedDecision.parcel_id}</p>
                  </div>
                )}
                {selectedDecision.project_id && (
                  <div className="p-3 bg-white rounded-lg border border-slate-200">
                    <p className="text-xs text-slate-500 uppercase">Project ID</p>
                    <p className="text-sm font-medium text-slate-900">{selectedDecision.project_id}</p>
                  </div>
                )}
              </div>

              {/* Explanation */}
              {selectedDecision.explanation && (
                <div className="mb-6">
                  <p className="text-xs text-slate-500 uppercase mb-2">AI Explanation</p>
                  <div className="p-4 bg-white rounded-lg border border-slate-200">
                    <p className="text-sm text-slate-700">{selectedDecision.explanation}</p>
                  </div>
                </div>
              )}

              {/* Flags */}
              {selectedDecision.flags.length > 0 && (
                <div className="mb-6">
                  <p className="text-xs text-slate-500 uppercase mb-2">Flags ({selectedDecision.flags.length})</p>
                  <div className="flex flex-wrap gap-2">
                    {selectedDecision.flags.map((flag) => (
                      <span
                        key={flag}
                        className="px-3 py-1 bg-amber-100 text-amber-800 text-sm rounded-full"
                      >
                        {flag.replace(/_/g, " ")}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Review Status */}
              {selectedDecision.reviewed && selectedDecision.reviewed_by && (
                <div className="p-4 bg-emerald-50 rounded-lg border border-emerald-200">
                  <p className="text-xs text-emerald-600 uppercase mb-1">Reviewed</p>
                  <p className="text-sm text-emerald-800">
                    By {selectedDecision.reviewed_by} on {formatDate(selectedDecision.reviewed_at || "")}
                  </p>
                  {selectedDecision.review_outcome && (
                    <p className="mt-1 text-sm font-medium text-emerald-900">
                      Outcome: {selectedDecision.review_outcome}
                    </p>
                  )}
                </div>
              )}
            </div>
          ) : activeTab === "escalations" && selectedEscalation ? (
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-slate-900">Escalation Details</h3>
                <button
                  onClick={() => setSelectedEscalation(null)}
                  className="text-slate-400 hover:text-slate-600"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Priority & Status */}
              <div className="flex items-center gap-3 mb-6">
                <span className={`px-3 py-1 text-sm font-medium rounded border ${PRIORITY_STYLES[selectedEscalation.priority]}`}>
                  {selectedEscalation.priority.toUpperCase()} Priority
                </span>
                <span className={`px-3 py-1 text-sm font-medium rounded ${
                  selectedEscalation.status === "open" ? "bg-blue-100 text-blue-700" : "bg-emerald-100 text-emerald-700"
                }`}>
                  {selectedEscalation.status}
                </span>
              </div>

              {/* AI Decision Info */}
              <div className="mb-6 p-4 bg-white rounded-lg border border-slate-200">
                <p className="text-xs text-slate-500 uppercase mb-2">AI Decision</p>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-900">
                    {AGENT_TYPE_LABELS[selectedEscalation.ai_decision.agent_type] || selectedEscalation.ai_decision.agent_type}
                  </span>
                  <span className={`px-2 py-0.5 text-xs font-medium rounded ${getConfidenceColor(selectedEscalation.ai_decision.confidence)}`}>
                    {(selectedEscalation.ai_decision.confidence * 100).toFixed(0)}% confidence
                  </span>
                </div>
                {selectedEscalation.ai_decision.explanation && (
                  <p className="mt-2 text-sm text-slate-600">{selectedEscalation.ai_decision.explanation}</p>
                )}
              </div>

              {/* Resolve Form */}
              {selectedEscalation.status === "open" && (
                <div className="p-4 bg-white rounded-lg border border-slate-200">
                  <p className="text-sm font-medium text-slate-700 mb-3">Resolve Escalation</p>
                  
                  <div className="mb-4">
                    <p className="text-xs text-slate-500 mb-2">Outcome</p>
                    <div className="flex gap-4">
                      {["approved", "rejected", "modified"].map((opt) => (
                        <label key={opt} className="flex items-center gap-2">
                          <input
                            type="radio"
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

                  <div className="mb-4">
                    <p className="text-xs text-slate-500 mb-2">Resolution Notes</p>
                    <textarea
                      value={resolution}
                      onChange={(e) => setResolution(e.target.value)}
                      placeholder="Enter resolution notes..."
                      rows={3}
                      className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand"
                    />
                  </div>

                  <button
                    onClick={handleResolve}
                    disabled={!resolution || resolving}
                    className="w-full py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-dark disabled:opacity-50 transition-colors"
                  >
                    {resolving ? "Resolving..." : "Resolve Escalation"}
                  </button>
                </div>
              )}

              {/* Resolution Info */}
              {selectedEscalation.status === "resolved" && selectedEscalation.resolution && (
                <div className="p-4 bg-emerald-50 rounded-lg border border-emerald-200">
                  <p className="text-xs text-emerald-600 uppercase mb-1">Resolution</p>
                  <p className="text-sm text-emerald-800">{selectedEscalation.resolution}</p>
                </div>
              )}
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-slate-400">
              <div className="text-center">
                <svg className="w-16 h-16 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                <p className="text-sm">Select an item to view details</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
