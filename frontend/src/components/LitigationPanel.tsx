"use client";

import { useEffect, useState } from "react";
import {
  listLitigationCases,
  createLitigationCase,
  getLitigationCase,
  updateLitigationCase,
  getLitigationHistory,
  type LitigationCaseItem,
  type LitigationCaseDetail,
  type LitigationCaseCreatePayload,
  type LitigationCaseUpdatePayload,
} from "@/lib/api";

type Props = {
  parcelId: string;
  projectId: string;
};

type LitigationStatus = 
  | "pending_filing"
  | "filed"
  | "served"
  | "discovery"
  | "trial_scheduled"
  | "trial"
  | "settled"
  | "judgment"
  | "closed";

const STATUS_LABELS: Record<LitigationStatus, string> = {
  pending_filing: "Pending Filing",
  filed: "Filed",
  served: "Served",
  discovery: "Discovery",
  trial_scheduled: "Trial Scheduled",
  trial: "In Trial",
  settled: "Settled",
  judgment: "Judgment",
  closed: "Closed",
};

const STATUS_COLORS: Record<LitigationStatus, string> = {
  pending_filing: "bg-slate-100 text-slate-700",
  filed: "bg-blue-50 text-blue-700",
  served: "bg-indigo-50 text-indigo-700",
  discovery: "bg-purple-50 text-purple-700",
  trial_scheduled: "bg-amber-50 text-amber-700",
  trial: "bg-orange-50 text-orange-700",
  settled: "bg-emerald-50 text-emerald-700",
  judgment: "bg-teal-50 text-teal-700",
  closed: "bg-slate-50 text-slate-500",
};

const STATUS_ORDER: LitigationStatus[] = [
  "pending_filing",
  "filed",
  "served",
  "discovery",
  "trial_scheduled",
  "trial",
  "settled",
  "judgment",
  "closed",
];

type HistoryItem = {
  id: string;
  old_status: string | null;
  new_status: string;
  changed_by: string;
  changed_at: string;
  notes?: string;
};

export function LitigationPanel({ parcelId, projectId }: Props) {
  const [cases, setCases] = useState<LitigationCaseItem[] | null>(null);
  const [selectedCase, setSelectedCase] = useState<LitigationCaseDetail | null>(null);
  const [history, setHistory] = useState<HistoryItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  
  // Create form
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [court, setCourt] = useState("");
  const [courtCounty, setCourtCounty] = useState("");
  const [causeNumber, setCauseNumber] = useState("");
  const [isQuickTake, setIsQuickTake] = useState(false);
  
  // Update form
  const [updating, setUpdating] = useState(false);
  const [newStatus, setNewStatus] = useState<LitigationStatus | "">("");
  const [statusNotes, setStatusNotes] = useState("");
  const [filingDate, setFilingDate] = useState("");
  const [serviceDate, setServiceDate] = useState("");
  const [trialDate, setTrialDate] = useState("");

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const res = await listLitigationCases({ parcel_id: parcelId });
      setCases(res.items);
    } catch (e) {
      setError(String(e));
      setCases(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, [parcelId]);

  async function handleSelectCase(caseId: string) {
    setError(null);
    try {
      const [caseDetail, historyRes] = await Promise.all([
        getLitigationCase(caseId),
        getLitigationHistory(caseId),
      ]);
      setSelectedCase(caseDetail);
      setHistory(historyRes.history);
      // Pre-fill update form
      if (caseDetail.filing_date) {
        setFilingDate(caseDetail.filing_date.split("T")[0]);
      }
      if (caseDetail.service_date) {
        setServiceDate(caseDetail.service_date.split("T")[0]);
      }
      if (caseDetail.trial_date) {
        setTrialDate(caseDetail.trial_date.split("T")[0]);
      }
      setNewStatus("");
      setStatusNotes("");
    } catch (e) {
      setError(String(e));
    }
  }

  async function handleCreateCase() {
    if (!court) {
      setError("Please provide a court name");
      return;
    }

    setCreating(true);
    setError(null);
    try {
      const payload: LitigationCaseCreatePayload = {
        parcel_id: parcelId,
        project_id: projectId,
        court,
        court_county: courtCounty || undefined,
        cause_number: causeNumber || undefined,
        is_quick_take: isQuickTake,
      };
      await createLitigationCase(payload);
      setShowCreate(false);
      setCourt("");
      setCourtCounty("");
      setCauseNumber("");
      setIsQuickTake(false);
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setCreating(false);
    }
  }

  async function handleUpdateCase() {
    if (!selectedCase) return;
    
    setUpdating(true);
    setError(null);
    try {
      const payload: LitigationCaseUpdatePayload = {};
      
      if (newStatus) {
        payload.status = newStatus;
        if (statusNotes) {
          payload.status_notes = statusNotes;
        }
      }
      if (filingDate) {
        payload.filing_date = new Date(filingDate).toISOString();
      }
      if (serviceDate) {
        payload.service_date = new Date(serviceDate).toISOString();
      }
      if (trialDate) {
        payload.trial_date = new Date(trialDate).toISOString();
      }

      await updateLitigationCase(selectedCase.id, payload);
      await handleSelectCase(selectedCase.id);
      await refresh();
      setNewStatus("");
      setStatusNotes("");
    } catch (e) {
      setError(String(e));
    } finally {
      setUpdating(false);
    }
  }

  function formatDate(isoDate?: string | null): string {
    if (!isoDate) return "—";
    return new Date(isoDate).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function formatDateTime(isoDate?: string | null): string {
    if (!isoDate) return "—";
    return new Date(isoDate).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function getNextStatuses(currentStatus: LitigationStatus): LitigationStatus[] {
    const currentIndex = STATUS_ORDER.indexOf(currentStatus);
    if (currentIndex === -1) return STATUS_ORDER;
    // Allow moving forward or to settled/closed from any state
    const forward = STATUS_ORDER.slice(currentIndex + 1);
    return forward;
  }

  const activeCases = cases?.filter((c) => 
    c.status !== "closed" && c.status !== "settled" && c.status !== "judgment"
  );
  const closedCases = cases?.filter((c) => 
    c.status === "closed" || c.status === "settled" || c.status === "judgment"
  );

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold">Litigation Cases</h3>
          <p className="text-sm text-slate-500">Parcel: {parcelId}</p>
        </div>
        <div className="flex items-center gap-3">
          {activeCases && activeCases.length > 0 && (
            <span className="text-xs px-2 py-1 rounded-full bg-amber-50 text-amber-700">
              {activeCases.length} active
            </span>
          )}
          <button
            onClick={() => {
              setShowCreate(!showCreate);
              setSelectedCase(null);
            }}
            className="text-sm px-3 py-1 rounded-md bg-brand text-white hover:bg-brand-dark transition-colors"
          >
            {showCreate ? "Cancel" : "+ New Case"}
          </button>
          <button
            onClick={refresh}
            disabled={loading}
            className="text-sm text-brand hover:underline disabled:opacity-50"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Create Form */}
      {showCreate && (
        <div className="mb-6 p-4 rounded-lg bg-slate-50 border border-slate-200">
          <h4 className="font-medium mb-3">Create New Litigation Case</h4>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="text-xs text-slate-500 block mb-1">Court *</label>
              <input
                type="text"
                value={court}
                onChange={(e) => setCourt(e.target.value)}
                placeholder="e.g., District Court"
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand"
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 block mb-1">County</label>
              <input
                type="text"
                value={courtCounty}
                onChange={(e) => setCourtCounty(e.target.value)}
                placeholder="e.g., Harris County"
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="text-xs text-slate-500 block mb-1">Cause Number</label>
              <input
                type="text"
                value={causeNumber}
                onChange={(e) => setCauseNumber(e.target.value)}
                placeholder="e.g., 2026-CV-12345"
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand"
              />
            </div>
            <div className="flex items-center pt-5">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isQuickTake}
                  onChange={(e) => setIsQuickTake(e.target.checked)}
                  className="w-4 h-4 rounded border-slate-300 text-brand focus:ring-brand"
                />
                <span className="text-sm text-slate-700">Quick-Take Proceeding</span>
              </label>
            </div>
          </div>
          <button
            onClick={handleCreateCase}
            disabled={creating}
            className="px-4 py-2 text-sm rounded-md bg-brand text-white hover:bg-brand-dark disabled:opacity-50 transition-colors"
          >
            {creating ? "Creating..." : "Create Case"}
          </button>
        </div>
      )}

      {error && <p className="text-sm text-rose-600 mb-3">{error}</p>}
      {loading && <p className="text-sm text-slate-500 mb-3">Loading...</p>}

      {/* Cases List */}
      <div className="grid grid-cols-2 gap-6">
        <div>
          <h4 className="text-sm font-medium text-slate-700 mb-3">Cases</h4>
          <ul className="space-y-2">
            {(cases ?? []).map((c) => {
              const status = (c.status as LitigationStatus) || "pending_filing";
              const isSelected = selectedCase?.id === c.id;
              
              return (
                <li key={c.id}>
                  <button
                    onClick={() => handleSelectCase(c.id)}
                    className={`w-full text-left p-3 rounded-lg border transition-colors ${
                      isSelected
                        ? "border-brand bg-brand/5"
                        : "border-slate-200 hover:border-slate-300"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium">{c.court}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_COLORS[status]}`}>
                        {STATUS_LABELS[status]}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      {c.cause_number && (
                        <span className="text-xs text-slate-500">#{c.cause_number}</span>
                      )}
                      {c.is_quick_take && (
                        <span className="text-xs px-1.5 py-0.5 rounded bg-amber-100 text-amber-700">
                          Quick-Take
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-400 mt-1">
                      Filed: {formatDate(c.filing_date)}
                    </p>
                  </button>
                </li>
              );
            })}
            {cases?.length === 0 && (
              <li className="py-8 text-center text-slate-500">
                <p>No litigation cases for this parcel.</p>
                <button
                  onClick={() => setShowCreate(true)}
                  className="mt-2 text-brand hover:underline"
                >
                  Create one now
                </button>
              </li>
            )}
          </ul>
        </div>

        {/* Case Detail */}
        <div>
          {selectedCase ? (
            <div className="p-4 rounded-lg border border-slate-200 bg-slate-50">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h4 className="font-medium">{selectedCase.court}</h4>
                  {selectedCase.court_county && (
                    <p className="text-xs text-slate-500">{selectedCase.court_county}</p>
                  )}
                </div>
                <span className={`text-xs px-2 py-1 rounded-full ${
                  STATUS_COLORS[selectedCase.status as LitigationStatus]
                }`}>
                  {STATUS_LABELS[selectedCase.status as LitigationStatus]}
                </span>
              </div>

              {/* Key Dates */}
              <div className="mb-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Cause #:</span>
                  <span className="font-medium">{selectedCase.cause_number || "—"}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Filing Date:</span>
                  <span>{formatDate(selectedCase.filing_date)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Service Date:</span>
                  <span>{formatDate(selectedCase.service_date)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Trial Date:</span>
                  <span>{formatDate(selectedCase.trial_date)}</span>
                </div>
              </div>

              {/* Update Status */}
              <div className="mb-4 pt-4 border-t border-slate-200">
                <h5 className="text-sm font-medium mb-2">Update Case</h5>
                <div className="space-y-3">
                  <div>
                    <label className="text-xs text-slate-500 block mb-1">Change Status</label>
                    <select
                      value={newStatus}
                      onChange={(e) => setNewStatus(e.target.value as LitigationStatus)}
                      className="w-full px-2 py-1.5 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand"
                    >
                      <option value="">No change</option>
                      {getNextStatuses(selectedCase.status as LitigationStatus).map((s) => (
                        <option key={s} value={s}>{STATUS_LABELS[s]}</option>
                      ))}
                    </select>
                  </div>
                  {newStatus && (
                    <div>
                      <label className="text-xs text-slate-500 block mb-1">Status Notes</label>
                      <input
                        type="text"
                        value={statusNotes}
                        onChange={(e) => setStatusNotes(e.target.value)}
                        placeholder="Optional notes..."
                        className="w-full px-2 py-1.5 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand"
                      />
                    </div>
                  )}
                  <div className="grid grid-cols-3 gap-2">
                    <div>
                      <label className="text-xs text-slate-500 block mb-1">Filing</label>
                      <input
                        type="date"
                        value={filingDate}
                        onChange={(e) => setFilingDate(e.target.value)}
                        className="w-full px-2 py-1 text-xs border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-slate-500 block mb-1">Service</label>
                      <input
                        type="date"
                        value={serviceDate}
                        onChange={(e) => setServiceDate(e.target.value)}
                        className="w-full px-2 py-1 text-xs border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-slate-500 block mb-1">Trial</label>
                      <input
                        type="date"
                        value={trialDate}
                        onChange={(e) => setTrialDate(e.target.value)}
                        className="w-full px-2 py-1 text-xs border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand"
                      />
                    </div>
                  </div>
                  <button
                    onClick={handleUpdateCase}
                    disabled={updating}
                    className="px-3 py-1.5 text-sm rounded-md bg-brand text-white hover:bg-brand-dark disabled:opacity-50 transition-colors"
                  >
                    {updating ? "Updating..." : "Save Changes"}
                  </button>
                </div>
              </div>

              {/* Status History */}
              {history && history.length > 0 && (
                <div className="pt-4 border-t border-slate-200">
                  <h5 className="text-sm font-medium mb-2">Status History</h5>
                  <ul className="space-y-2">
                    {history.map((h) => (
                      <li key={h.id} className="text-xs">
                        <div className="flex items-center gap-1">
                          {h.old_status && (
                            <>
                              <span className={`px-1.5 py-0.5 rounded ${
                                STATUS_COLORS[h.old_status as LitigationStatus]
                              }`}>
                                {STATUS_LABELS[h.old_status as LitigationStatus]}
                              </span>
                              <span className="text-slate-400">→</span>
                            </>
                          )}
                          <span className={`px-1.5 py-0.5 rounded ${
                            STATUS_COLORS[h.new_status as LitigationStatus]
                          }`}>
                            {STATUS_LABELS[h.new_status as LitigationStatus]}
                          </span>
                        </div>
                        <p className="text-slate-400 mt-0.5">
                          {formatDateTime(h.changed_at)} by {h.changed_by}
                        </p>
                        {h.notes && (
                          <p className="text-slate-500 italic mt-0.5">"{h.notes}"</p>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="p-8 rounded-lg border border-dashed border-slate-200 text-center text-slate-400">
              <p>Select a case to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
