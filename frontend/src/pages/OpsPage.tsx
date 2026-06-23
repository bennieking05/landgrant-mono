import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useAppContext } from "@/context";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { RoutePlanPanel } from "@/components/RoutePlanPanel";
import { NotificationsPanel } from "@/components/NotificationsPanel";
import { healthEsign, healthInvite, healthLive } from "@/lib/api";

type ProbeState = "loading" | "ok" | "degraded" | "down";

type Probe = {
  id: string;
  label: string;
  description: string;
  run: () => Promise<string>;
};

// Visual mapping from probe state to a dot color and screen-reader label.
// Kept out of the component so tests/snapshots don't rotate on re-render.
const STATE_STYLES: Record<ProbeState, { dot: string; text: string; srLabel: string }> = {
  loading: { dot: "bg-slate-300 animate-pulse", text: "text-slate-500", srLabel: "checking" },
  ok: { dot: "bg-emerald-500", text: "text-emerald-700", srLabel: "healthy" },
  degraded: { dot: "bg-amber-500", text: "text-amber-700", srLabel: "degraded" },
  down: { dot: "bg-rose-500", text: "text-rose-700", srLabel: "offline" },
};

// Module-level probe registry so its identity is stable across renders and
// ``useCallback`` doesn't have to re-bind when the component re-renders.
const PROBES: Probe[] = [
  {
    id: "api",
    label: "API (Cloud Run)",
    description: "GET /health/live",
    run: async () => {
      const res = await healthLive();
      return res.status ?? "ok";
    },
  },
  {
    id: "invite",
    label: "Portal Invites",
    description: "GET /health/invite",
    run: async () => {
      const res = await healthInvite();
      return res.status ?? "ok";
    },
  },
  {
    id: "esign",
    label: "E-sign (Adobe)",
    description: "GET /health/esign",
    run: async () => {
      const res = await healthEsign();
      return `${res.status ?? "ok"} (${res.vendor ?? "unknown"})`;
    },
  },
];

export function OpsPage() {
  const { t } = useTranslation();
  const { projectId, parcelId } = useAppContext();
  useDocumentTitle("Operations");

  const [statuses, setStatuses] = useState<Record<string, { state: ProbeState; detail?: string }>>(
    () => Object.fromEntries(PROBES.map((p) => [p.id, { state: "loading" as const }])),
  );
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const runProbes = useCallback(async () => {
    setRefreshing(true);
    setStatuses((prev) =>
      Object.fromEntries(
        PROBES.map((p) => [p.id, { state: "loading", detail: prev[p.id]?.detail }]),
      ),
    );

    // Probes are independent; fan them out in parallel so one slow endpoint
    // doesn't block the others from displaying their status.
    const results = await Promise.all(
      PROBES.map(async (p) => {
        try {
          const detail = await p.run();
          return [p.id, { state: "ok" as ProbeState, detail }] as const;
        } catch (err) {
          const message = err instanceof Error ? err.message : String(err);
          // A 5xx or network error looks like an outage; 401/403 from a
          // missing persona gets surfaced as ``degraded`` so the operator can
          // see the gate vs. a real outage.
          const state: ProbeState = /401|403/.test(message) ? "degraded" : "down";
          return [p.id, { state, detail: message }] as const;
        }
      }),
    );

    setStatuses(Object.fromEntries(results));
    setLastChecked(new Date());
    setRefreshing(false);
  }, []);

  useEffect(() => {
    runProbes();
    // Auto-refresh every 60s so the panel stays meaningful without blocking
    // a human refresh. The interval is cleared on unmount.
    const interval = window.setInterval(runProbes, 60_000);
    return () => window.clearInterval(interval);
  }, [runProbes]);

  return (
    <section className="space-y-6">
      <div>
        <p className="text-sm uppercase tracking-wide text-brand">{t("pages.ops.eyebrow")}</p>
        <h1 className="mt-2 text-3xl font-semibold">{t("pages.ops.title")}</h1>
        <p className="mt-2 max-w-3xl text-slate-600">{t("pages.ops.subtitle")}</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <RoutePlanPanel projectId={projectId} />
        {parcelId ? (
          <NotificationsPanel projectId={projectId} parcelId={parcelId} />
        ) : (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-800">
            Select a parcel before sending parcel-specific notifications.
          </div>
        )}
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm" data-testid="integration-status">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-lg font-semibold">Integration Status</h3>
            <p className="text-sm text-slate-500">
              {lastChecked
                ? `Last checked ${lastChecked.toLocaleTimeString()}`
                : "Running initial check..."}
            </p>
          </div>
          <button
            type="button"
            onClick={runProbes}
            disabled={refreshing}
            className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 transition-colors hover:border-brand hover:text-brand disabled:cursor-not-allowed disabled:opacity-50"
            data-testid="integration-status-refresh"
          >
            {refreshing ? "Refreshing..." : "Refresh"}
          </button>
        </div>

        <ul className="grid gap-4 md:grid-cols-3">
          {PROBES.map((p) => {
            const s = statuses[p.id] ?? { state: "loading" as ProbeState };
            const styles = STATE_STYLES[s.state];
            return (
              <li
                key={p.id}
                className="rounded-lg bg-slate-50 p-4"
                data-testid={`integration-${p.id}`}
              >
                <div className="mb-2 flex items-center gap-2">
                  <span
                    className={`inline-block h-2 w-2 rounded-full ${styles.dot}`}
                    aria-label={styles.srLabel}
                  />
                  <span className="text-sm font-medium text-slate-900">{p.label}</span>
                  <span className={`ml-auto text-xs font-medium ${styles.text}`}>
                    {s.state === "loading"
                      ? "Checking..."
                      : s.state === "ok"
                        ? "Healthy"
                        : s.state === "degraded"
                          ? "Degraded"
                          : "Offline"}
                  </span>
                </div>
                <p className="text-xs text-slate-500">{p.description}</p>
                {s.detail ? (
                  <p className="mt-1 truncate text-xs text-slate-600" title={s.detail}>
                    {s.detail}
                  </p>
                ) : null}
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}
