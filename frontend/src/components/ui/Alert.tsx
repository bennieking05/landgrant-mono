import { cva, type VariantProps } from "class-variance-authority";
import { AlertTriangle, CheckCircle2, Info, ShieldAlert, XCircle } from "lucide-react";
import { cn } from "@/lib/cn";

/**
 * Standard inline alert (UX-5): title + plain-language message + optional action,
 * replacing raw exception strings. Authorization failures use the "forbidden"
 * variant and read "You don't have access" - distinct from empty.
 */
const alertVariants = cva("flex gap-3 rounded-card border p-4 text-small", {
  variants: {
    variant: {
      info: "border-info-border bg-info-bg text-info-fg",
      success: "border-success-border bg-success-bg text-success-fg",
      warning: "border-warning-border bg-warning-bg text-warning-fg",
      danger: "border-danger-border bg-danger-bg text-danger-fg",
      forbidden: "border-warning-border bg-warning-bg text-warning-fg",
    },
  },
  defaultVariants: { variant: "info" },
});

const ICONS = {
  info: Info,
  success: CheckCircle2,
  warning: AlertTriangle,
  danger: XCircle,
  forbidden: ShieldAlert,
} as const;

export type AlertProps = VariantProps<typeof alertVariants> & {
  title?: string;
  children?: React.ReactNode;
  action?: { label: string; onClick: () => void };
  className?: string;
};

export function Alert({ variant = "info", title, children, action, className }: AlertProps) {
  const Icon = ICONS[variant ?? "info"];
  return (
    <div className={cn(alertVariants({ variant }), className)} role="alert">
      <Icon className="mt-0.5 h-5 w-5 shrink-0" aria-hidden />
      <div className="min-w-0 flex-1">
        {title ? <p className="font-semibold">{title}</p> : null}
        {children ? <div className={cn(title && "mt-0.5")}>{children}</div> : null}
        {action ? (
          <button
            type="button"
            onClick={action.onClick}
            className="mt-2 text-small font-semibold underline underline-offset-2 hover:no-underline"
          >
            {action.label}
          </button>
        ) : null}
      </div>
    </div>
  );
}
