import { useId } from "react";
import { cn } from "@/lib/cn";

type FieldProps = {
  label: string;
  /** Renders the control given the id + aria props it must spread. */
  children: (props: {
    id: string;
    "aria-invalid"?: boolean;
    "aria-describedby"?: string;
    "aria-required"?: boolean;
  }) => React.ReactNode;
  required?: boolean;
  error?: string | null;
  hint?: string;
  className?: string;
};

/**
 * Accessible form field (UX-5 / UX-9): programmatically associated <label for>,
 * required marker, helper text, and inline error wired via aria-describedby.
 */
export function Field({ label, children, required, error, hint, className }: FieldProps) {
  const id = useId();
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const describedBy =
    [error ? errorId : null, hint ? hintId : null].filter(Boolean).join(" ") || undefined;

  return (
    <div className={cn("space-y-1", className)}>
      <label htmlFor={id} className="block text-small font-medium text-slate-700">
        {label}
        {required ? (
          <span className="ml-0.5 text-danger" aria-hidden>
            *
          </span>
        ) : null}
        {required ? <span className="sr-only"> (required)</span> : null}
      </label>
      {children({
        id,
        "aria-invalid": error ? true : undefined,
        "aria-describedby": describedBy,
        "aria-required": required || undefined,
      })}
      {hint && !error ? (
        <p id={hintId} className="text-caption text-slate-500">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} className="text-caption font-medium text-danger" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
