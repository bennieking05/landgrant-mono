import { type ReactNode } from "react";

type Status = "grounded" | "escalated" | "unknown";

type Props = {
  status?: Status;
  confidence?: number;
  citations?: number;
  className?: string;
  children?: ReactNode;
};

const CONFIG: Record<Status, { label: string; bg: string; text: string; title: string }> = {
  grounded: {
    label: "Grounded",
    bg: "bg-emerald-100",
    text: "text-emerald-900",
    title: "AI output was accepted by the citation gate.",
  },
  escalated: {
    label: "Escalated",
    bg: "bg-amber-100",
    text: "text-amber-900",
    title: "AI output needs human review before use.",
  },
  unknown: {
    label: "Unverified",
    bg: "bg-slate-100",
    text: "text-slate-700",
    title: "No grounding signal was emitted for this output.",
  },
};

export function GroundedBadge({ status, confidence, citations, className, children }: Props) {
  const resolved: Status = status ?? "unknown";
  const cfg = CONFIG[resolved];

  const suffix: string[] = [];
  if (typeof confidence === "number") {
    suffix.push(`${Math.round(confidence * 100)}%`);
  }
  if (typeof citations === "number") {
    suffix.push(`${citations} cite${citations === 1 ? "" : "s"}`);
  }

  return (
    <span
      data-testid="grounded-badge"
      data-status={resolved}
      title={cfg.title}
      className={[
        "inline-flex items-center gap-2 rounded-full px-2.5 py-0.5 text-xs font-medium",
        cfg.bg,
        cfg.text,
        className ?? "",
      ].join(" ")}
    >
      <span>{children ?? cfg.label}</span>
      {suffix.length > 0 && (
        <span className="opacity-70">· {suffix.join(" · ")}</span>
      )}
    </span>
  );
}

export default GroundedBadge;
