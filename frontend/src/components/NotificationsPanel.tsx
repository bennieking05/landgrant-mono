"use client";

import { useState } from "react";
import { previewNotification, type NotificationPreviewResponse } from "@/lib/api";

type Props = {
  projectId: string;
  parcelId: string;
};

const TEMPLATE_OPTIONS = [
  { id: "portal_invite", label: "Portal Invite" },
  { id: "decision_confirmation", label: "Decision Confirmation" },
  { id: "offer_letter", label: "Offer Letter" },
  { id: "deadline_reminder", label: "Deadline Reminder" },
];

const CHANNEL_OPTIONS = [
  { id: "email", label: "Email" },
  { id: "sms", label: "SMS" },
];

export function NotificationsPanel({ projectId, parcelId }: Props) {
  const [templateId, setTemplateId] = useState("portal_invite");
  const [channel, setChannel] = useState("email");
  const [recipient, setRecipient] = useState("");
  const [preview, setPreview] = useState<NotificationPreviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handlePreview() {
    if (!recipient) {
      setError("Please enter a recipient");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await previewNotification({
        template_id: templateId,
        channel,
        to: recipient,
        project_id: projectId,
        parcel_id: parcelId,
        variables: {},
      });
      setPreview(res);
    } catch (e) {
      setError(String(e));
      setPreview(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-4">
        <h3 className="text-lg font-semibold">Notifications</h3>
        <p className="text-sm text-slate-500">
          Preview and send communications to landowners
        </p>
      </div>

      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-slate-600 mb-1">Template</label>
            <select
              value={templateId}
              onChange={(e) => setTemplateId(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              {TEMPLATE_OPTIONS.map((opt) => (
                <option key={opt.id} value={opt.id}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-600 mb-1">Channel</label>
            <select
              value={channel}
              onChange={(e) => setChannel(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              {CHANNEL_OPTIONS.map((opt) => (
                <option key={opt.id} value={opt.id}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="block text-xs text-slate-600 mb-1">
            Recipient {channel === "email" ? "(Email)" : "(Phone)"}
          </label>
          <input
            type={channel === "email" ? "email" : "tel"}
            value={recipient}
            onChange={(e) => setRecipient(e.target.value)}
            placeholder={channel === "email" ? "owner@example.com" : "+1 555-123-4567"}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>

        <div className="flex gap-2 text-xs text-slate-500">
          <span>Project: {projectId}</span>
          <span>·</span>
          <span>Parcel: {parcelId}</span>
        </div>

        <button
          onClick={handlePreview}
          disabled={loading}
          className="w-full rounded-md bg-brand px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {loading ? "Generating Preview..." : "Preview Notification"}
        </button>

        {error && <p className="text-sm text-rose-600">{error}</p>}

        {preview && (
          <div className="border-t border-slate-200 pt-4 space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium text-slate-700">Preview</h4>
              <span
                className={`text-xs px-2 py-0.5 rounded ${
                  preview.mode === "live"
                    ? "bg-emerald-100 text-emerald-700"
                    : "bg-amber-100 text-amber-700"
                }`}
              >
                {preview.mode === "live" ? "Live" : "Preview"}
              </span>
            </div>

            {preview.subject && (
              <div>
                <p className="text-xs text-slate-500">Subject</p>
                <p className="text-sm text-slate-900">{preview.subject}</p>
              </div>
            )}

            <div>
              <p className="text-xs text-slate-500">Body</p>
              <div className="bg-slate-50 rounded-lg p-3 text-sm text-slate-700 whitespace-pre-wrap max-h-48 overflow-y-auto">
                {preview.body}
              </div>
            </div>

            <div className="flex gap-4 text-xs text-slate-500">
              <span>To: {preview.to}</span>
              <span>Channel: {preview.channel}</span>
              {preview.notification_id && (
                <span>ID: {preview.notification_id}</span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
