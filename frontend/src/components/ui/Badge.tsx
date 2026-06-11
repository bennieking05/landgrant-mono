import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/cn";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-caption font-medium",
  {
    variants: {
      variant: {
        neutral: "bg-slate-100 text-slate-700 border-slate-200",
        brand: "bg-brand/10 text-brand border-brand/20",
        success: "bg-success-bg text-success-fg border-success-border",
        warning: "bg-warning-bg text-warning-fg border-warning-border",
        danger: "bg-danger-bg text-danger-fg border-danger-border",
        info: "bg-info-bg text-info-fg border-info-border",
        accent: "bg-accent-50 text-accent-700 border-accent-100",
      },
    },
    defaultVariants: { variant: "neutral" },
  },
);

export type BadgeProps = React.HTMLAttributes<HTMLSpanElement> &
  VariantProps<typeof badgeVariants>;

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

/** Small "AI" marker for AI-assisted features (UX-1: no separate color universe). */
export function AIBadge({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full bg-brand/10 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-brand",
        className,
      )}
    >
      AI
    </span>
  );
}
