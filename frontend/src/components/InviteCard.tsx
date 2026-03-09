"use client";

import { useState } from "react";
import { apiPostJson } from "@/lib/api";

export function InviteCard({ projectId, parcelId }: { projectId: string; parcelId: string }) {
  const [email, setEmail] = useState("owner@example.com");
  const [status, setStatus] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);

  async function send() {
    setIsSending(true);
    setStatus("Sending invite...");
    try {
      const res = await apiPostJson<{
        invite_id: string;
        expires_at: string;
        status: string;
        invite_link?: string;
      }>(
        "/portal/invites",
        { email, project_id: projectId, parcel_id: parcelId },
        "landowner",
      );
      setStatus(`Invite ${res.status} (${res.invite_id}), expires ${res.expires_at}${res.invite_link ? `, link: ${res.invite_link}` : ""}`);
    } catch (e) {
      setStatus(`Invite failed: ${String(e)}`);
    } finally {
      setIsSending(false);
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h3 className="text-lg font-semibold">Secure invite & one-time verify</h3>
      <p className="mt-2 text-sm text-slate-600">Magic-link invite with expiration + throttled retries.</p>
      <div className="mt-4 flex gap-2">
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <button
          onClick={send}
          disabled={isSending}
          className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white"
        >
          {isSending ? "Sending..." : "Send invite"}
        </button>
      </div>
      {status && <p className="mt-2 text-xs text-slate-600 break-words">{status}</p>}
    </div>
  );
}



