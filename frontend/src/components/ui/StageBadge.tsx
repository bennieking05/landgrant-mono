import { cn } from "@/lib/cn";

/**
 * Parcel workflow stages (UX-6). StageBadge is the ONLY way stage is displayed
 * anywhere (grid, dashboards, detail, portal): color from the stage ramp + an
 * always-visible text label. Full class strings so Tailwind JIT keeps them.
 */
export const STAGE_ORDER = [
  "intake",
  "appraisal",
  "offer_pending",
  "offer_sent",
  "negotiation",
  "closing",
  "litigation",
  "closed",
] as const;

export type Stage = (typeof STAGE_ORDER)[number];

export const STAGE_LABELS: Record<string, string> = {
  intake: "Intake",
  appraisal: "Appraisal",
  offer_pending: "Offer pending",
  offer_sent: "Offer sent",
  negotiation: "Negotiation",
  closing: "Closing",
  litigation: "Litigation",
  closed: "Closed",
};

const STAGE_CLASSES: Record<string, string> = {
  intake: "bg-stage-intake-bg text-stage-intake-fg border-stage-intake-border",
  appraisal: "bg-stage-appraisal-bg text-stage-appraisal-fg border-stage-appraisal-border",
  offer_pending:
    "bg-stage-offerPending-bg text-stage-offerPending-fg border-stage-offerPending-border",
  offer_sent: "bg-stage-offerSent-bg text-stage-offerSent-fg border-stage-offerSent-border",
  negotiation:
    "bg-stage-negotiation-bg text-stage-negotiation-fg border-stage-negotiation-border",
  closing: "bg-stage-closing-bg text-stage-closing-fg border-stage-closing-border",
  litigation: "bg-stage-litigation-bg text-stage-litigation-fg border-stage-litigation-border",
  closed: "bg-stage-closed-bg text-stage-closed-fg border-stage-closed-border",
};

/** Stage hex colors for chart fills (Recharts can't consume Tailwind classes). */
export const STAGE_COLORS: Record<string, string> = {
  intake: "#64748b",
  appraisal: "#1570ef",
  offer_pending: "#b54708",
  offer_sent: "#b26a2c",
  negotiation: "#7839ee",
  closing: "#099268",
  litigation: "#d92d20",
  closed: "#98a2b3",
};

export function stageLabel(stage: string): string {
  return STAGE_LABELS[stage] ?? stage.replace(/_/g, " ");
}

export function StageBadge({ stage, className }: { stage: string; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-caption font-medium",
        STAGE_CLASSES[stage] ?? "bg-slate-100 text-slate-700 border-slate-200",
        className,
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70" aria-hidden />
      {stageLabel(stage)}
    </span>
  );
}

/** Legend listing every stage with its color + label (popover content / help). */
export function StageLegend({ className }: { className?: string }) {
  return (
    <ul className={cn("grid grid-cols-2 gap-1.5", className)}>
      {STAGE_ORDER.map((s) => (
        <li key={s}>
          <StageBadge stage={s} />
        </li>
      ))}
    </ul>
  );
}

type RiskBand = "low" | "medium" | "high";

function riskBand(score: number): RiskBand {
  if (score >= 70) return "high";
  if (score >= 40) return "medium";
  return "low";
}

const RISK_CLASSES: Record<RiskBand, string> = {
  low: "bg-risk-low-bg text-risk-low-fg border-risk-low-border",
  medium: "bg-risk-medium-bg text-risk-medium-fg border-risk-medium-border",
  high: "bg-risk-high-bg text-risk-high-fg border-risk-high-border",
};

const RISK_LABELS: Record<RiskBand, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
};

/** Risk shown as "72 - High": numeric score + colored band + label, never color alone. */
export function RiskBadge({ score, className }: { score: number; className?: string }) {
  const band = riskBand(score);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-caption font-semibold tabular-nums",
        RISK_CLASSES[band],
        className,
      )}
    >
      {score} <span className="font-medium opacity-80">- {RISK_LABELS[band]}</span>
    </span>
  );
}
