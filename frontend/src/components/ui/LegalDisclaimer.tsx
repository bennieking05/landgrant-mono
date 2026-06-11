import { Scale } from "lucide-react";
import { cn } from "@/lib/cn";

/**
 * Prominent legal disclaimer (UX-1 / 1.7): the one place where deliberate,
 * legible design is a legal requirement - never 10px grey text.
 */
export function LegalDisclaimer({
  className,
  children = "AI-generated content requires attorney review before use. This is not legal advice.",
}: {
  className?: string;
  children?: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-control border border-warning-border bg-warning-bg px-3 py-2 text-small font-medium text-warning-fg",
        className,
      )}
      role="note"
    >
      <Scale className="h-4 w-4 shrink-0" aria-hidden />
      <span>{children}</span>
    </div>
  );
}
