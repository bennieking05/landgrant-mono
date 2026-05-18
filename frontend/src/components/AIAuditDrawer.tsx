import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import { GroundedBadge } from "./GroundedBadge";

type AIEvent = {
  id: string;
  agent_type?: string;
  task_type?: string;
  model?: string;
  prompt_template_id?: string;
  prompt_version?: string;
  confidence?: number;
  flags?: string[];
  citations?: string[];
  grounded?: boolean;
  escalated?: boolean;
  occurred_at?: string;
  metadata?: Record<string, unknown>;
};

type Props = {
  open: boolean;
  onClose: () => void;
  resourceId?: string;
  title?: string;
};

/**
 * AI Audit drawer surfaces the signed provenance of AI decisions in-place
 * next to the output itself.  Phase 4.2 wires it to
 * ``GET /audit/ai-events?resource=<id>``.  When resourceId is absent we show
 * the last N global events so QA can sanity-check coverage.
 */
export function AIAuditDrawer({ open, onClose, resourceId, title }: Props) {
  const [events, setEvents] = useState<AIEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    setError(null);

    const qs = resourceId
      ? `?resource=${encodeURIComponent(resourceId)}&limit=25`
      : "?limit=25";
    apiGet<{ items?: AIEvent[] } | AIEvent[]>(`/audit/ai-events${qs}`)
      .then((res) => {
        if (cancelled) return;
        const items = Array.isArray(res) ? res : res.items ?? [];
        setEvents(items);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, resourceId]);

  if (!open) return null;

  return (
    <aside
      role="dialog"
      aria-label="AI Audit"
      data-testid="ai-audit-drawer"
      className="fixed right-0 top-0 z-50 flex h-full w-full max-w-md flex-col border-l border-slate-200 bg-white shadow-xl"
    >
      <header className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <div>
          <h2 className="text-base font-semibold text-slate-900">
            {title ?? "AI Audit"}
          </h2>
          {resourceId && (
            <p className="text-xs text-slate-500">{resourceId}</p>
          )}
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-md px-2 py-1 text-sm text-slate-600 hover:bg-slate-100"
        >
          Close
        </button>
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-3">
        {loading && (
          <p className="text-sm text-slate-500">Loading audit events…</p>
        )}
        {error && (
          <p className="text-sm text-red-600" data-testid="ai-audit-error">
            {error}
          </p>
        )}
        {!loading && !error && events.length === 0 && (
          <p className="text-sm text-slate-500">
            No AI events recorded for this resource yet.
          </p>
        )}

        <ul className="space-y-3">
          {events.map((ev) => {
            const status = ev.escalated
              ? "escalated"
              : ev.grounded
                ? "grounded"
                : "unknown";
            return (
              <li
                key={ev.id}
                className="rounded-md border border-slate-200 p-3 text-sm"
                data-testid="ai-audit-item"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium text-slate-900">
                    {ev.agent_type || ev.task_type || "ai_call"}
                  </span>
                  <GroundedBadge
                    status={status}
                    confidence={ev.confidence}
                    citations={ev.citations?.length}
                  />
                </div>
                <dl className="mt-2 grid grid-cols-2 gap-x-2 gap-y-1 text-xs text-slate-600">
                  {ev.model && (
                    <>
                      <dt className="text-slate-500">Model</dt>
                      <dd>{ev.model}</dd>
                    </>
                  )}
                  {ev.prompt_template_id && (
                    <>
                      <dt className="text-slate-500">Prompt</dt>
                      <dd>
                        {ev.prompt_template_id}
                        {ev.prompt_version ? ` · v${ev.prompt_version}` : ""}
                      </dd>
                    </>
                  )}
                  {ev.occurred_at && (
                    <>
                      <dt className="text-slate-500">At</dt>
                      <dd>{ev.occurred_at}</dd>
                    </>
                  )}
                  {ev.flags && ev.flags.length > 0 && (
                    <>
                      <dt className="text-slate-500">Flags</dt>
                      <dd className="font-mono">{ev.flags.join(", ")}</dd>
                    </>
                  )}
                </dl>
              </li>
            );
          })}
        </ul>
      </div>
    </aside>
  );
}

export default AIAuditDrawer;
