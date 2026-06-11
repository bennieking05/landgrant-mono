/**
 * Shared formatters (UX-5): one date format everywhere ("Jun 9, 2026"), with a
 * relative-time helper for hover/secondary display. Keep all date rendering here.
 */

const ABS_DATE = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
});

const ABS_DATETIME = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

function toDate(value: string | number | Date | null | undefined): Date | null {
  if (value == null) return null;
  const d = value instanceof Date ? value : new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** "Jun 9, 2026" - the canonical absolute date. */
export function formatDate(value: string | number | Date | null | undefined): string {
  const d = toDate(value);
  return d ? ABS_DATE.format(d) : "-";
}

/** "Jun 9, 2026, 3:58 PM" - absolute date + time. */
export function formatDateTime(value: string | number | Date | null | undefined): string {
  const d = toDate(value);
  return d ? ABS_DATETIME.format(d) : "-";
}

/** "in 3 days" / "2 hours ago" - relative, for hover or secondary text. */
export function formatRelative(value: string | number | Date | null | undefined): string {
  const d = toDate(value);
  if (!d) return "-";
  const rtf = new Intl.RelativeTimeFormat("en-US", { numeric: "auto" });
  const diffMs = d.getTime() - Date.now();
  const abs = Math.abs(diffMs);
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ["year", 31_536_000_000],
    ["month", 2_592_000_000],
    ["week", 604_800_000],
    ["day", 86_400_000],
    ["hour", 3_600_000],
    ["minute", 60_000],
  ];
  for (const [unit, ms] of units) {
    if (abs >= ms || unit === "minute") {
      return rtf.format(Math.round(diffMs / ms), unit);
    }
  }
  return rtf.format(0, "minute");
}

/** Days from now until the date (negative = overdue). */
export function daysUntil(value: string | number | Date | null | undefined): number | null {
  const d = toDate(value);
  if (!d) return null;
  return Math.ceil((d.getTime() - Date.now()) / 86_400_000);
}

/** Compact USD, e.g. "$350,000". */
export function formatCurrency(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "-";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

/** Thousands-separated integer, e.g. "1,248". */
export function formatNumber(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "-";
  return new Intl.NumberFormat("en-US").format(value);
}
