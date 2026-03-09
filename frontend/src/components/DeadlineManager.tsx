"use client";

import { useEffect, useState } from "react";
import {
  listDeadlines,
  createDeadline,
  getDeadlinesIcal,
  deriveDeadlines,
  type DeadlineItem,
  type DerivedDeadlineItem,
} from "@/lib/api";

type Props = {
  projectId: string;
};

// Indiana anchor events for the derive form
const IN_ANCHOR_EVENTS = [
  { key: "offer_served", label: "Offer Served", citation: "IC 32-24-1-5" },
  { key: "complaint_filed", label: "Complaint Filed", citation: "IC 32-24-1-5" },
  { key: "notice_served", label: "Notice Served", citation: "IC 32-24-1-6" },
  { key: "appraisers_report_mailed", label: "Appraisers Report Mailed", citation: "IC 32-24-1-11" },
  { key: "trial_date_set", label: "Trial Date Set", citation: "IC 32-24-1-12" },
];

export function DeadlineManager({ projectId }: Props) {
  const [deadlines, setDeadlines] = useState<DeadlineItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // New deadline form
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [parcelId, setParcelId] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Derive statutory deadlines form
  const [showDeriveForm, setShowDeriveForm] = useState(false);
  const [deriveJurisdiction, setDeriveJurisdiction] = useState("IN");
  const [deriveParcelId, setDeriveParcelId] = useState("");
  const [anchorEvents, setAnchorEvents] = useState<Record<string, string>>({});
  const [deriving, setDeriving] = useState(false);
  const [deriveResult, setDeriveResult] = useState<DerivedDeadlineItem[] | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const res = await listDeadlines(projectId);
      setDeadlines(res.items);
    } catch (e) {
      setError(String(e));
      setDeadlines(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, [projectId]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title || !dueAt) return;

    setSubmitting(true);
    try {
      await createDeadline({
        project_id: projectId,
        title,
        due_at: new Date(dueAt).toISOString(),
        parcel_id: parcelId || undefined,
        timezone: "America/Chicago",
      });
      setTitle("");
      setDueAt("");
      setParcelId("");
      setShowForm(false);
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setSubmitting(false);
    }
  }

  async function downloadIcal() {
    try {
      const res = await getDeadlinesIcal(projectId);
      const blob = new Blob([res.ical], { type: "text/calendar" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${projectId}-deadlines.ics`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(String(e));
    }
  }

  async function handleDerive(e: React.FormEvent) {
    e.preventDefault();
    // Filter out empty anchor events
    const filteredAnchors: Record<string, string> = {};
    for (const [key, value] of Object.entries(anchorEvents)) {
      if (value) {
        filteredAnchors[key] = value;
      }
    }

    if (Object.keys(filteredAnchors).length === 0) {
      setError("Please enter at least one anchor date");
      return;
    }

    setDeriving(true);
    setError(null);
    setDeriveResult(null);

    try {
      const res = await deriveDeadlines({
        project_id: projectId,
        parcel_id: deriveParcelId || undefined,
        jurisdiction: deriveJurisdiction,
        anchor_events: filteredAnchors,
        persist: true,
        timezone: "America/Indiana/Indianapolis",
      });

      setDeriveResult(res.deadlines);

      if (res.errors.length > 0) {
        setError(res.errors.join("; "));
      }

      // Refresh the deadlines list
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setDeriving(false);
    }
  }

  function updateAnchorEvent(key: string, value: string) {
    setAnchorEvents((prev) => ({ ...prev, [key]: value }));
  }

  function resetDeriveForm() {
    setShowDeriveForm(false);
    setAnchorEvents({});
    setDeriveParcelId("");
    setDeriveResult(null);
  }

  function formatDate(isoDate: string): string {
    const d = new Date(isoDate);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  function daysUntil(isoDate: string): number {
    const due = new Date(isoDate);
    const now = new Date();
    return Math.ceil((due.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  }

  function urgencyClass(days: number): string {
    if (days <= 3) return "text-rose-600 bg-rose-50";
    if (days <= 7) return "text-amber-600 bg-amber-50";
    return "text-emerald-600 bg-emerald-50";
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold">Deadlines</h3>
          <p className="text-sm text-slate-500">Project: {projectId}</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={downloadIcal}
            className="text-sm text-slate-600 hover:text-brand"
          >
            Export iCal
          </button>
          <button
            onClick={() => {
              setShowDeriveForm(!showDeriveForm);
              if (showForm) setShowForm(false);
            }}
            className="rounded-md border border-brand px-3 py-1.5 text-sm font-medium text-brand hover:bg-brand/5"
          >
            {showDeriveForm ? "Cancel" : "Generate Statutory"}
          </button>
          <button
            onClick={() => {
              setShowForm(!showForm);
              if (showDeriveForm) setShowDeriveForm(false);
            }}
            className="rounded-md bg-brand px-3 py-1.5 text-sm font-medium text-white"
          >
            {showForm ? "Cancel" : "+ Add"}
          </button>
        </div>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="mb-4 p-4 bg-slate-50 rounded-lg space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <input
              type="text"
              placeholder="Deadline title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
              required
            />
            <input
              type="datetime-local"
              value={dueAt}
              onChange={(e) => setDueAt(e.target.value)}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
              required
            />
          </div>
          <div className="flex gap-3">
            <input
              type="text"
              placeholder="Parcel ID (optional)"
              value={parcelId}
              onChange={(e) => setParcelId(e.target.value)}
              className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
            <button
              type="submit"
              disabled={submitting}
              className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {submitting ? "Saving..." : "Save"}
            </button>
          </div>
        </form>
      )}

      {showDeriveForm && (
        <form onSubmit={handleDerive} className="mb-4 p-4 bg-indigo-50 rounded-lg space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="font-medium text-slate-900">Generate Statutory Deadlines</h4>
            <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-1 rounded">
              {deriveJurisdiction === "IN" ? "Indiana" : deriveJurisdiction}
            </span>
          </div>
          <p className="text-xs text-slate-600">
            Enter key procedural dates to automatically calculate statutory deadlines per Indiana Code Title 32, Article 24.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-600 mb-1">Jurisdiction</label>
              <select
                value={deriveJurisdiction}
                onChange={(e) => setDeriveJurisdiction(e.target.value)}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="IN">Indiana (IN)</option>
                <option value="TX">Texas (TX)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-600 mb-1">Parcel ID (optional)</label>
              <input
                type="text"
                placeholder="e.g., PARCEL-001"
                value={deriveParcelId}
                onChange={(e) => setDeriveParcelId(e.target.value)}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
          </div>

          <div className="border-t border-indigo-200 pt-3">
            <p className="text-xs font-medium text-slate-700 mb-2">Anchor Events (enter dates as they occur)</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {IN_ANCHOR_EVENTS.map((anchor) => (
                <div key={anchor.key}>
                  <label className="block text-xs text-slate-600 mb-1">
                    {anchor.label}
                    <span className="text-slate-400 ml-1">({anchor.citation})</span>
                  </label>
                  <input
                    type="date"
                    value={anchorEvents[anchor.key] || ""}
                    onChange={(e) => updateAnchorEvent(anchor.key, e.target.value)}
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>
              ))}
            </div>
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={resetDeriveForm}
              className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={deriving}
              className="flex-1 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {deriving ? "Generating..." : "Generate & Save Deadlines"}
            </button>
          </div>

          {deriveResult && deriveResult.length > 0 && (
            <div className="mt-4 border-t border-indigo-200 pt-3">
              <p className="text-xs font-medium text-emerald-700 mb-2">
                Generated {deriveResult.length} deadline(s)
              </p>
              <ul className="text-xs space-y-1 max-h-32 overflow-y-auto">
                {deriveResult.map((d) => (
                  <li key={d.id} className="flex justify-between text-slate-600">
                    <span>{d.title}</span>
                    <span className="text-slate-500">{d.due_date} · {d.citation}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </form>
      )}

      {error && <p className="text-sm text-rose-600 mb-3">{error}</p>}
      {loading && <p className="text-sm text-slate-500 mb-3">Loading...</p>}

      <ul className="space-y-3">
        {(deadlines ?? []).map((d) => {
          const days = daysUntil(d.due_at);
          return (
            <li key={d.id} className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
              <div>
                <p className="font-medium text-slate-900">{d.title}</p>
                <p className="text-xs text-slate-500">
                  {d.parcel_id ? `Parcel: ${d.parcel_id}` : "Project-wide"} · {d.timezone}
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm text-slate-700">{formatDate(d.due_at)}</p>
                <span className={`inline-block mt-1 rounded-full px-2 py-0.5 text-xs font-medium ${urgencyClass(days)}`}>
                  {days <= 0 ? "Overdue" : `${days} days`}
                </span>
              </div>
            </li>
          );
        })}
        {deadlines?.length === 0 && (
          <li className="py-6 text-center text-slate-500">No deadlines found</li>
        )}
      </ul>
    </div>
  );
}

