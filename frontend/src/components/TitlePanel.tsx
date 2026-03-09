"use client";

import { useEffect, useState } from "react";
import {
  listTitleInstruments,
  uploadTitleInstrument,
  listCurativeItems,
  createCurativeItem,
  updateCurativeItem,
  getCurativeAnalytics,
  type TitleInstrumentItem,
  type CurativeItem,
  type CurativeItemCreatePayload,
  type CurativeAnalyticsResponse,
} from "@/lib/api";

type Props = {
  parcelId: string;
};

type CurativeStatus = "identified" | "in_progress" | "resolved" | "waived";
type CurativeSeverity = "low" | "medium" | "high" | "critical";
type CurativeType = "lien" | "encumbrance" | "easement" | "judgment" | "tax_delinquency" | "boundary_dispute" | "other";

const STATUS_COLORS: Record<CurativeStatus, string> = {
  identified: "bg-rose-50 text-rose-700",
  in_progress: "bg-amber-50 text-amber-700",
  resolved: "bg-emerald-50 text-emerald-700",
  waived: "bg-slate-100 text-slate-600",
};

const SEVERITY_COLORS: Record<CurativeSeverity, string> = {
  low: "bg-blue-50 text-blue-700",
  medium: "bg-amber-50 text-amber-700",
  high: "bg-orange-50 text-orange-700",
  critical: "bg-rose-50 text-rose-700",
};

type TabType = "instruments" | "curative";

export function TitlePanel({ parcelId }: Props) {
  const [activeTab, setActiveTab] = useState<TabType>("instruments");
  
  // Instruments state
  const [instruments, setInstruments] = useState<TitleInstrumentItem[] | null>(null);
  const [uploading, setUploading] = useState(false);
  
  // Curative items state
  const [curativeItems, setCurativeItems] = useState<CurativeItem[] | null>(null);
  const [curativeAnalytics, setCurativeAnalytics] = useState<CurativeAnalyticsResponse | null>(null);
  const [showCreateCurative, setShowCreateCurative] = useState(false);
  const [creatingCurative, setCreatingCurative] = useState(false);
  
  // Curative form state
  const [curativeType, setCurativeType] = useState<CurativeType>("lien");
  const [curativeSeverity, setCurativeSeverity] = useState<CurativeSeverity>("medium");
  const [curativeDescription, setCurativeDescription] = useState("");
  const [curativeDueDate, setCurativeDueDate] = useState("");
  
  // Shared state
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function refreshInstruments() {
    setLoading(true);
    setError(null);
    try {
      const res = await listTitleInstruments(parcelId);
      setInstruments(res.items);
    } catch (e) {
      setError(String(e));
      setInstruments(null);
    } finally {
      setLoading(false);
    }
  }

  async function refreshCurative() {
    setLoading(true);
    setError(null);
    try {
      const [itemsRes, analyticsRes] = await Promise.all([
        listCurativeItems(parcelId),
        getCurativeAnalytics({ parcel_id: parcelId }),
      ]);
      setCurativeItems(itemsRes.items);
      setCurativeAnalytics(analyticsRes);
    } catch (e) {
      setError(String(e));
      setCurativeItems(null);
    } finally {
      setLoading(false);
    }
  }

  function refresh() {
    if (activeTab === "instruments") {
      refreshInstruments();
    } else {
      refreshCurative();
    }
  }

  useEffect(() => {
    refresh();
  }, [parcelId, activeTab]);

  async function handleUpload(files: FileList | null) {
    if (!files || files.length === 0) return;

    setUploading(true);
    setError(null);
    try {
      for (const file of Array.from(files)) {
        await uploadTitleInstrument(parcelId, file);
      }
      await refreshInstruments();
    } catch (e) {
      setError(String(e));
    } finally {
      setUploading(false);
    }
  }

  async function handleCreateCurative() {
    if (!curativeDescription) {
      setError("Please provide a description");
      return;
    }

    setCreatingCurative(true);
    setError(null);
    try {
      const payload: CurativeItemCreatePayload = {
        parcel_id: parcelId,
        item_type: curativeType,
        severity: curativeSeverity,
        description: curativeDescription,
        due_date: curativeDueDate ? new Date(curativeDueDate).toISOString() : undefined,
      };
      await createCurativeItem(payload);
      setShowCreateCurative(false);
      setCurativeDescription("");
      setCurativeDueDate("");
      setCurativeType("lien");
      setCurativeSeverity("medium");
      await refreshCurative();
    } catch (e) {
      setError(String(e));
    } finally {
      setCreatingCurative(false);
    }
  }

  async function handleUpdateCurativeStatus(itemId: string, newStatus: CurativeStatus) {
    setError(null);
    try {
      await updateCurativeItem(itemId, { status: newStatus });
      await refreshCurative();
    } catch (e) {
      setError(String(e));
    }
  }

  function formatDate(isoDate?: string): string {
    if (!isoDate) return "—";
    return new Date(isoDate).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function getInstrumentType(metadata?: Record<string, unknown>): string {
    const type = metadata?.instrument_type;
    if (typeof type === "string") {
      return type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    }
    return "Document";
  }

  function getConfidence(ocr?: Record<string, unknown>): number | null {
    const conf = ocr?.confidence;
    if (typeof conf === "number") return Math.round(conf * 100);
    return null;
  }

  function isOverdue(dueDate?: string): boolean {
    if (!dueDate) return false;
    return new Date(dueDate) < new Date();
  }

  const CURATIVE_TYPES: CurativeType[] = ["lien", "encumbrance", "easement", "judgment", "tax_delinquency", "boundary_dispute", "other"];
  const CURATIVE_SEVERITIES: CurativeSeverity[] = ["low", "medium", "high", "critical"];

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      {/* Header with tabs */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold">Title & Curative</h3>
          <p className="text-sm text-slate-500">Parcel: {parcelId}</p>
        </div>
        <div className="flex items-center gap-3">
          {activeTab === "curative" && curativeAnalytics && curativeAnalytics.overdue > 0 && (
            <span className="text-xs px-2 py-1 rounded-full bg-rose-50 text-rose-700">
              {curativeAnalytics.overdue} overdue
            </span>
          )}
          <button
            onClick={refresh}
            disabled={loading}
            className="text-sm text-brand hover:underline disabled:opacity-50"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 border-b border-slate-200">
        <button
          onClick={() => setActiveTab("instruments")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "instruments"
              ? "border-brand text-brand"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          Instruments
        </button>
        <button
          onClick={() => setActiveTab("curative")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "curative"
              ? "border-brand text-brand"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          Curative Items
          {curativeItems && curativeItems.filter((c) => c.status !== "resolved" && c.status !== "waived").length > 0 && (
            <span className="ml-1 text-xs bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full">
              {curativeItems.filter((c) => c.status !== "resolved" && c.status !== "waived").length}
            </span>
          )}
        </button>
      </div>

      {error && <p className="text-sm text-rose-600 mb-3">{error}</p>}
      {loading && <p className="text-sm text-slate-500 mb-3">Loading...</p>}

      {/* Instruments Tab */}
      {activeTab === "instruments" && (
        <>
          {/* Upload area */}
          <label className="mb-4 flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500 hover:border-brand hover:text-brand transition-colors">
            <input
              type="file"
              multiple
              accept=".pdf,.jpg,.jpeg,.png,.tiff"
              className="hidden"
              onChange={(e) => handleUpload(e.target.files)}
              disabled={uploading}
            />
            {uploading ? "Uploading..." : "Drop title documents or click to upload"}
          </label>

          <ul className="space-y-3">
            {(instruments ?? []).map((inst) => {
              const confidence = getConfidence(inst.ocr_payload);
              return (
                <li key={inst.id} className="flex items-start justify-between py-3 border-b border-slate-100 last:border-0">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-slate-900">{getInstrumentType(inst.metadata)}</span>
                      {confidence !== null && (
                        <span className={`text-xs px-2 py-0.5 rounded-full ${confidence >= 90 ? "bg-emerald-50 text-emerald-700" : confidence >= 70 ? "bg-amber-50 text-amber-700" : "bg-rose-50 text-rose-700"}`}>
                          OCR: {confidence}%
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-500 mt-1">
                      Doc ID: {inst.document_id ?? "—"} · Added: {formatDate(inst.created_at)}
                    </p>
                    {inst.ocr_payload?.entities && Array.isArray(inst.ocr_payload.entities) && (
                      <p className="text-xs text-slate-500 mt-1">
                        Entities: {(inst.ocr_payload.entities as string[]).join(", ")}
                      </p>
                    )}
                  </div>
                  <div className="text-right text-xs text-slate-500">
                    {inst.metadata?.recorded_date && (
                      <span>Recorded: {String(inst.metadata.recorded_date)}</span>
                    )}
                    {inst.metadata?.survey_date && (
                      <span>Survey: {String(inst.metadata.survey_date)}</span>
                    )}
                  </div>
                </li>
              );
            })}
            {instruments?.length === 0 && (
              <li className="py-6 text-center text-slate-500">No title instruments found</li>
            )}
          </ul>
        </>
      )}

      {/* Curative Items Tab */}
      {activeTab === "curative" && (
        <>
          {/* Analytics Summary */}
          {curativeAnalytics && (
            <div className="mb-4 p-3 rounded-lg bg-slate-50 border border-slate-200">
              <div className="grid grid-cols-4 gap-3 text-center">
                <div>
                  <p className="text-lg font-semibold text-slate-900">{curativeAnalytics.by_status?.identified ?? 0}</p>
                  <p className="text-xs text-slate-500">Identified</p>
                </div>
                <div>
                  <p className="text-lg font-semibold text-amber-600">{curativeAnalytics.by_status?.in_progress ?? 0}</p>
                  <p className="text-xs text-slate-500">In Progress</p>
                </div>
                <div>
                  <p className="text-lg font-semibold text-emerald-600">{curativeAnalytics.by_status?.resolved ?? 0}</p>
                  <p className="text-xs text-slate-500">Resolved</p>
                </div>
                <div>
                  <p className="text-lg font-semibold text-rose-600">{curativeAnalytics.overdue ?? 0}</p>
                  <p className="text-xs text-slate-500">Overdue</p>
                </div>
              </div>
            </div>
          )}

          {/* Add Curative Button */}
          <button
            onClick={() => setShowCreateCurative(!showCreateCurative)}
            className="mb-4 text-sm px-3 py-1.5 rounded-md bg-brand text-white hover:bg-brand-dark transition-colors"
          >
            {showCreateCurative ? "Cancel" : "+ Add Curative Item"}
          </button>

          {/* Create Form */}
          {showCreateCurative && (
            <div className="mb-4 p-4 rounded-lg bg-slate-50 border border-slate-200">
              <h4 className="font-medium mb-3">Add Curative Item</h4>
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="text-xs text-slate-500 block mb-1">Type</label>
                  <select
                    value={curativeType}
                    onChange={(e) => setCurativeType(e.target.value as CurativeType)}
                    className="w-full px-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand"
                  >
                    {CURATIVE_TYPES.map((t) => (
                      <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-slate-500 block mb-1">Severity</label>
                  <select
                    value={curativeSeverity}
                    onChange={(e) => setCurativeSeverity(e.target.value as CurativeSeverity)}
                    className="w-full px-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand"
                  >
                    {CURATIVE_SEVERITIES.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="mb-4">
                <label className="text-xs text-slate-500 block mb-1">Description *</label>
                <textarea
                  value={curativeDescription}
                  onChange={(e) => setCurativeDescription(e.target.value)}
                  placeholder="Describe the issue..."
                  rows={2}
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand"
                />
              </div>
              <div className="mb-4">
                <label className="text-xs text-slate-500 block mb-1">Due Date</label>
                <input
                  type="date"
                  value={curativeDueDate}
                  onChange={(e) => setCurativeDueDate(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand"
                />
              </div>
              <button
                onClick={handleCreateCurative}
                disabled={creatingCurative}
                className="px-4 py-2 text-sm rounded-md bg-brand text-white hover:bg-brand-dark disabled:opacity-50 transition-colors"
              >
                {creatingCurative ? "Creating..." : "Add Item"}
              </button>
            </div>
          )}

          {/* Curative Items List */}
          <ul className="space-y-3">
            {(curativeItems ?? []).map((item) => {
              const status = (item.status as CurativeStatus) || "identified";
              const severity = (item.severity as CurativeSeverity) || "medium";
              const overdue = isOverdue(item.due_date) && status !== "resolved" && status !== "waived";

              return (
                <li key={item.id} className={`p-3 rounded-lg border ${overdue ? "border-rose-200 bg-rose-50/30" : "border-slate-200"}`}>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-slate-900 capitalize">
                          {item.item_type?.replace(/_/g, " ")}
                        </span>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_COLORS[status]}`}>
                          {status.replace(/_/g, " ")}
                        </span>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${SEVERITY_COLORS[severity]}`}>
                          {severity}
                        </span>
                        {overdue && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-rose-100 text-rose-700">
                            Overdue
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-600">{item.description}</p>
                      <p className="text-xs text-slate-400 mt-1">
                        Due: {formatDate(item.due_date)} · Added: {formatDate(item.created_at)}
                      </p>
                      {item.resolution_notes && (
                        <p className="text-xs text-slate-500 mt-1 italic">
                          Resolution: {item.resolution_notes}
                        </p>
                      )}
                    </div>
                    <div className="flex flex-col gap-1 ml-3">
                      {status === "identified" && (
                        <button
                          onClick={() => handleUpdateCurativeStatus(item.id, "in_progress")}
                          className="text-xs px-2 py-1 rounded bg-amber-100 text-amber-700 hover:bg-amber-200 transition-colors"
                        >
                          Start
                        </button>
                      )}
                      {status === "in_progress" && (
                        <button
                          onClick={() => handleUpdateCurativeStatus(item.id, "resolved")}
                          className="text-xs px-2 py-1 rounded bg-emerald-100 text-emerald-700 hover:bg-emerald-200 transition-colors"
                        >
                          Resolve
                        </button>
                      )}
                      {(status === "identified" || status === "in_progress") && (
                        <button
                          onClick={() => handleUpdateCurativeStatus(item.id, "waived")}
                          className="text-xs px-2 py-1 rounded bg-slate-100 text-slate-600 hover:bg-slate-200 transition-colors"
                        >
                          Waive
                        </button>
                      )}
                    </div>
                  </div>
                </li>
              );
            })}
            {curativeItems?.length === 0 && (
              <li className="py-6 text-center text-slate-500">
                <p>No curative items found</p>
                <button
                  onClick={() => setShowCreateCurative(true)}
                  className="mt-2 text-brand hover:underline"
                >
                  Add the first item
                </button>
              </li>
            )}
          </ul>
        </>
      )}
    </div>
  );
}

