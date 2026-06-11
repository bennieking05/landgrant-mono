import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/cn";

export type Crumb = { label: string; to?: string };

/** Breadcrumbs (UX-2): Project / Alignment / Segment / Parcel. */
export function Breadcrumbs({ items, className }: { items: Crumb[]; className?: string }) {
  if (items.length === 0) return null;
  return (
    <nav aria-label="Breadcrumb" className={cn("flex items-center gap-1 text-small", className)}>
      <ol className="flex items-center gap-1">
        {items.map((item, i) => {
          const last = i === items.length - 1;
          return (
            <li key={`${item.label}-${i}`} className="flex items-center gap-1">
              {item.to && !last ? (
                <Link to={item.to} className="text-slate-500 hover:text-slate-900">
                  {item.label}
                </Link>
              ) : (
                <span className={cn(last ? "font-medium text-slate-900" : "text-slate-500")} aria-current={last ? "page" : undefined}>
                  {item.label}
                </span>
              )}
              {!last ? <ChevronRight className="h-3.5 w-3.5 text-slate-300" aria-hidden /> : null}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
