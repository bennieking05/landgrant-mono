"use client";

import { useEffect, useState } from "react";
import {
  listROEs,
  createROE,
  updateROE,
  createROEFieldEvent,
  listExpiringROEs,
  type ROEItem,
  type ROECreatePayload,
} from "@/lib/api";

type Props = {
  parcelId: string;
  projectId: string;
};

type ROEStatus = "draft" | "sent" | "signed" | "active" | "expired" | "revoked";

const STATUS_COLORS: Record<ROEStatus, string> = {
  draft: "bg-slate-100 text-slate-700",
  sent: "bg-blue-50 text-blue-700",
  signed: "bg-purple-50 text-purple-700",
  active: "bg-emerald-50 text-emerald-700",
  expired: "bg-rose-50 text-rose-700",
  revoked: "bg-amber-50 text-amber-700",
};

export function ROEPanel({ parcelId, projectId }: Props) {
  const [roes, setRoes] = useState<ROEItem[] | null>(null);
  const [expiringRoes, setExpiringRoes] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [selectedRoe, setSelectedRoe] = useState<string | null>(null);
  const [checkingIn, setCheckingIn] = useState<string | null>(null);

  // Form state for create
  const [effectiveDate, setEffectiveDate] = useState("");
  const [expiryDate, setExpiryDate] = useState("");
  const [conditions, setConditions] = useState("");
  const [activities, setActivities] = useState<string[]>(["survey", "environmental"]);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [roesRes, expiringRes] = await Promise.all([
        listROEs(parcelId),
        listExpiringROEs({ project_id: projectId, days_threshold: 30 }),
      ]);
      setRoes(roesRes.items);
      setExpiringRoes(expiringRes.count);
    } catch (e) {
      setError(String(e));
      setRoes(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, [parcelId, projectId]);

  async function handleCreate() {
    if (!effectiveDate || !expiryDate) {
      setError("Please provide effective and expiry dates");
      return;
    }

    setCreating(true);
    setError(null);
    try {
      const payload: ROECreatePayload = {
        parcel_id: parcelId,
        project_id: projectId,
        effective_date: new Date(effectiveDate).toISOString(),
        expiry_date: new Date(expiryDate).toISOString(),
        conditions: conditions || undefined,
        permitted_activities: activities,
      };
      await createROE(payload);
      setShowCreate(false);
      setEffectiveDate("");
      setExpiryDate("");
      setConditions("");
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setCreating(false);
    }
  }

  async function handleStatusChange(roeId: string, newStatus: ROEStatus) {
    setError(null);
    try {
      await updateROE(roeId, { status: newStatus });
      await refresh();
    } catch (e) {
      setError(String(e));
    }
  }

  async function handleCheckIn(roeId: string, eventType: "check_in" | "check_out") {
    setCheckingIn(roeId);
    setError(null);
    try {
      // Get geolocation if available
      let latitude: number | undefined;
      let longitude: number | undefined;
      
      if (navigator.geolocation) {
        try {
          const pos = await new Promise<GeolocationPosition>((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 5000 });
          });
          latitude = pos.coords.latitude;
          longitude = pos.coords.longitude;
        } catch {
          // Geolocation unavailable, continue without it
        }
      }

      await createROEFieldEvent(roeId, {
        event_type: eventType,
        latitude,
        longitude,
        personnel_name: "Field Agent", // In a real app, get from user context
      });
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setCheckingIn(null);
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

  function getDaysUntilExpiry(expiryDate?: string): number | null {
    if (!expiryDate) return null;
    const now = new Date();
    const expiry = new Date(expiryDate);
    const diff = Math.ceil((expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
    return diff;
  }

  function toggleActivity(activity: string) {
    setActivities((prev) =>
      prev.includes(activity) ? prev.filter((a) => a !== activity) : [...prev, activity]
    );
  }

  const availableActivities = ["survey", "environmental", "geotechnical", "appraisal", "utility_locate", "other"];

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold">Right-of-Entry Agreements</h3>
          <p className="text-sm text-slate-500">Parcel: {parcelId}</p>
        </div>
        <div className="flex items-center gap-3">
          {expiringRoes > 0 && (
            <span className="text-xs px-2 py-1 rounded-full bg-amber-50 text-amber-700">
              {expiringRoes} expiring soon
            </span>
          )}
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="text-sm px-3 py-1 rounded-md bg-brand text-white hover:bg-brand-dark transition-colors"
          >
            {showCreate ? "Cancel" : "+ New ROE"}
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
          <h4 className="font-medium mb-3">Create New ROE</h4>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="text-xs text-slate-500 block mb-1">Effective Date</label>
              <input
                type="date"
                value={effectiveDate}
                onChange={(e) => setEffectiveDate(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand"
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 block mb-1">Expiry Date</label>
              <input
                type="date"
                value={expiryDate}
                onChange={(e) => setExpiryDate(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand"
              />
            </div>
          </div>
          <div className="mb-4">
            <label className="text-xs text-slate-500 block mb-1">Conditions</label>
            <textarea
              value={conditions}
              onChange={(e) => setConditions(e.target.value)}
              placeholder="Enter any conditions or restrictions..."
              rows={2}
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand"
            />
          </div>
          <div className="mb-4">
            <label className="text-xs text-slate-500 block mb-2">Permitted Activities</label>
            <div className="flex flex-wrap gap-2">
              {availableActivities.map((activity) => (
                <button
                  key={activity}
                  type="button"
                  onClick={() => toggleActivity(activity)}
                  className={`text-xs px-3 py-1 rounded-full border transition-colors ${
                    activities.includes(activity)
                      ? "bg-brand text-white border-brand"
                      : "bg-white text-slate-600 border-slate-300 hover:border-brand"
                  }`}
                >
                  {activity.replace(/_/g, " ")}
                </button>
              ))}
            </div>
          </div>
          <button
            onClick={handleCreate}
            disabled={creating}
            className="px-4 py-2 text-sm rounded-md bg-brand text-white hover:bg-brand-dark disabled:opacity-50 transition-colors"
          >
            {creating ? "Creating..." : "Create ROE"}
          </button>
        </div>
      )}

      {error && <p className="text-sm text-rose-600 mb-3">{error}</p>}
      {loading && <p className="text-sm text-slate-500 mb-3">Loading...</p>}

      {/* ROE List */}
      <ul className="space-y-4">
        {(roes ?? []).map((roe) => {
          const daysUntilExpiry = getDaysUntilExpiry(roe.expiry_date);
          const isExpiringSoon = daysUntilExpiry !== null && daysUntilExpiry <= 30 && daysUntilExpiry > 0;
          const isExpired = daysUntilExpiry !== null && daysUntilExpiry <= 0;
          const status = (roe.status as ROEStatus) || "draft";

          return (
            <li
              key={roe.id}
              className={`p-4 rounded-lg border ${
                isExpiringSoon
                  ? "border-amber-200 bg-amber-50/30"
                  : isExpired
                  ? "border-rose-200 bg-rose-50/30"
                  : "border-slate-200 bg-white"
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[status]}`}>
                      {status}
                    </span>
                    {isExpiringSoon && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-700">
                        Expires in {daysUntilExpiry} days
                      </span>
                    )}
                    {isExpired && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-rose-100 text-rose-700">
                        Expired
                      </span>
                    )}
                  </div>
                  <div className="text-sm text-slate-700">
                    <span className="font-medium">Effective:</span> {formatDate(roe.effective_date)}
                    <span className="mx-2">→</span>
                    <span className="font-medium">Expires:</span> {formatDate(roe.expiry_date)}
                  </div>
                  {roe.conditions && (
                    <p className="text-xs text-slate-500 mt-1">
                      <span className="font-medium">Conditions:</span> {roe.conditions}
                    </p>
                  )}
                  {roe.permitted_activities && roe.permitted_activities.length > 0 && (
                    <div className="flex gap-1 mt-2">
                      {roe.permitted_activities.map((activity) => (
                        <span key={activity} className="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                          {activity.replace(/_/g, " ")}
                        </span>
                      ))}
                    </div>
                  )}
                  {roe.signed_by && (
                    <p className="text-xs text-slate-500 mt-2">
                      Signed by: {roe.signed_by} on {formatDate(roe.signed_at)}
                    </p>
                  )}
                </div>
                <div className="flex flex-col gap-2 ml-4">
                  {/* Status Actions */}
                  {status === "draft" && (
                    <button
                      onClick={() => handleStatusChange(roe.id, "sent")}
                      className="text-xs px-3 py-1 rounded bg-blue-500 text-white hover:bg-blue-600 transition-colors"
                    >
                      Mark Sent
                    </button>
                  )}
                  {status === "sent" && (
                    <button
                      onClick={() => handleStatusChange(roe.id, "signed")}
                      className="text-xs px-3 py-1 rounded bg-purple-500 text-white hover:bg-purple-600 transition-colors"
                    >
                      Mark Signed
                    </button>
                  )}
                  {status === "signed" && (
                    <button
                      onClick={() => handleStatusChange(roe.id, "active")}
                      className="text-xs px-3 py-1 rounded bg-emerald-500 text-white hover:bg-emerald-600 transition-colors"
                    >
                      Activate
                    </button>
                  )}

                  {/* Field Check-in/out for active ROEs */}
                  {(status === "active" || status === "signed") && (
                    <div className="flex gap-1">
                      <button
                        onClick={() => handleCheckIn(roe.id, "check_in")}
                        disabled={checkingIn === roe.id}
                        className="text-xs px-2 py-1 rounded bg-emerald-100 text-emerald-700 hover:bg-emerald-200 transition-colors disabled:opacity-50"
                      >
                        {checkingIn === roe.id ? "..." : "Check In"}
                      </button>
                      <button
                        onClick={() => handleCheckIn(roe.id, "check_out")}
                        disabled={checkingIn === roe.id}
                        className="text-xs px-2 py-1 rounded bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors disabled:opacity-50"
                      >
                        {checkingIn === roe.id ? "..." : "Check Out"}
                      </button>
                    </div>
                  )}

                  {/* View Details */}
                  <button
                    onClick={() => setSelectedRoe(selectedRoe === roe.id ? null : roe.id)}
                    className="text-xs text-brand hover:underline"
                  >
                    {selectedRoe === roe.id ? "Hide" : "Details"}
                  </button>
                </div>
              </div>

              {/* Expanded Details */}
              {selectedRoe === roe.id && (
                <div className="mt-3 pt-3 border-t border-slate-200 text-xs text-slate-500">
                  <p>ROE ID: {roe.id}</p>
                  <p>Created: {formatDate(roe.created_at)}</p>
                  {roe.template_id && <p>Template: {roe.template_id}</p>}
                  {roe.document_id && <p>Document: {roe.document_id}</p>}
                </div>
              )}
            </li>
          );
        })}
        {roes?.length === 0 && (
          <li className="py-8 text-center text-slate-500">
            <p>No ROE agreements found for this parcel.</p>
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
  );
}
