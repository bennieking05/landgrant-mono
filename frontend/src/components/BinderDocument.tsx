import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { Printer, X } from "lucide-react";
import { Logo } from "@/components/ui";
import { formatDate } from "@/lib/format";

export type BinderSection = { name: string; status: string; detail?: string };

type Props = {
  projectId: string;
  parcelId?: string | null;
  sections: BinderSection[];
  completenessPct: number | null;
  preparedBy?: string;
  onClose: () => void;
};

/**
 * UX-10: a branded, print-ready Good-Faith Negotiation Binder. Renders into a
 * body-level portal so the app print stylesheet can hide all app chrome and
 * print only this document (cover -> TOC -> exhibits -> integrity hash).
 */
export function BinderDocument({
  projectId,
  parcelId,
  sections,
  completenessPct,
  preparedBy = "LandGrantIQ",
  onClose,
}: Props) {
  const generatedAt = useMemo(() => new Date(), []);
  const [hash, setHash] = useState<string>("computing…");

  // Toggle the body flag that scopes the print stylesheet to this overlay.
  useEffect(() => {
    document.body.classList.add("printing-document");
    return () => document.body.classList.remove("printing-document");
  }, []);

  // Close on Escape for keyboard users.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  // Content integrity hash over a canonical representation of the binder.
  useEffect(() => {
    let cancelled = false;
    const canonical = JSON.stringify({
      doc: "good-faith-binder",
      project_id: projectId,
      parcel_id: parcelId ?? null,
      generated_at: generatedAt.toISOString(),
      completeness_pct: completenessPct,
      sections: sections.map((s) => ({ name: s.name, status: s.status, detail: s.detail ?? "" })),
    });
    (async () => {
      try {
        const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(canonical));
        const hex = [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
        if (!cancelled) setHash(hex);
      } catch {
        if (!cancelled) setHash("unavailable");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [projectId, parcelId, generatedAt, completenessPct, sections]);

  const exhibits = sections.map((s, i) => ({
    label: `Exhibit ${String.fromCharCode(65 + i)}`,
    ...s,
  }));

  const node = (
    <div className="print-portal fixed inset-0 z-[200] overflow-auto bg-slate-200 py-8">
      {/* Screen-only toolbar */}
      <div className="no-print sticky top-0 z-10 mx-auto mb-6 flex max-w-[8.5in] items-center justify-between rounded-card bg-navy-900 px-4 py-3 text-white shadow-card">
        <span className="text-h3">Good-Faith Binder preview</span>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => window.print()}
            className="inline-flex items-center gap-2 rounded-control bg-accent px-3 py-2 text-small font-medium text-white hover:bg-accent-400"
          >
            <Printer className="h-4 w-4" /> Print / Save as PDF
          </button>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex items-center gap-2 rounded-control border border-white/30 px-3 py-2 text-small font-medium hover:bg-white/10"
          >
            <X className="h-4 w-4" /> Close
          </button>
        </div>
      </div>

      {/* The document */}
      <article className="print-document mx-auto max-w-[8.5in] bg-white p-[0.75in] text-slate-900 shadow-card">
        {/* Letterhead */}
        <header className="flex items-center justify-between border-b-2 border-navy-900 pb-4">
          <Logo size={32} />
          <div className="text-right text-caption text-slate-500">
            <p className="font-medium uppercase tracking-wide text-slate-600">Confidential</p>
            <p>Attorney work product</p>
          </div>
        </header>

        {/* Cover */}
        <section className="print-avoid-break py-16 text-center">
          <p className="text-caption font-medium uppercase tracking-widest text-accent">
            Eminent Domain — Good-Faith Negotiation Record
          </p>
          <h1 className="mt-3 text-display text-navy-900">Good-Faith Negotiation Binder</h1>
          <dl className="mx-auto mt-10 max-w-md space-y-2 text-left">
            <CoverRow label="Project" value={projectId} mono />
            {parcelId ? <CoverRow label="Parcel" value={parcelId} mono /> : null}
            <CoverRow label="Prepared by" value={preparedBy} />
            <CoverRow label="Generated" value={formatDate(generatedAt)} />
            {completenessPct !== null ? (
              <CoverRow label="Record completeness" value={`${completenessPct}%`} />
            ) : null}
          </dl>
          <p className="mx-auto mt-10 max-w-lg text-small text-slate-600">
            This binder compiles the documented record of good-faith negotiation efforts. It is
            intended for attorney review and is not legal advice.
          </p>
        </section>

        {/* Table of contents */}
        <section className="print-page-break print-avoid-break">
          <h2 className="border-b border-slate-200 pb-2 text-h1 text-navy-900">Table of Contents</h2>
          <ol className="mt-4 space-y-2">
            {exhibits.map((ex) => (
              <li key={ex.name} className="flex items-baseline justify-between gap-3 text-body">
                <span>
                  <span className="font-medium text-accent">{ex.label}.</span> {ex.name}
                </span>
                <span className="text-caption uppercase text-slate-500">{ex.status}</span>
              </li>
            ))}
          </ol>
        </section>

        {/* Exhibits */}
        {exhibits.map((ex) => (
          <section key={ex.name} className="print-page-break">
            <h2 className="border-b border-slate-200 pb-2 text-h1 text-navy-900">
              <span className="text-accent">{ex.label}.</span> {ex.name}
            </h2>
            <table className="mt-4 w-full text-body">
              <tbody>
                <tr className="border-b border-slate-100">
                  <th className="w-40 py-2 text-left align-top text-small font-medium text-slate-500">
                    Status
                  </th>
                  <td className="py-2">{ex.status}</td>
                </tr>
                <tr>
                  <th className="w-40 py-2 text-left align-top text-small font-medium text-slate-500">
                    Detail
                  </th>
                  <td className="py-2">{ex.detail ?? "—"}</td>
                </tr>
              </tbody>
            </table>
          </section>
        ))}

        {/* Integrity footer */}
        <footer className="print-avoid-break mt-12 border-t-2 border-navy-900 pt-4 text-caption text-slate-500">
          <p>
            <span className="font-medium text-slate-700">Document integrity (SHA-256): </span>
            <span className="font-id break-all">{hash}</span>
          </p>
          <p className="mt-1">
            Generated by LandGrantIQ on {formatDate(generatedAt)}. Page contents are immutable once
            hashed; any change produces a different digest.
          </p>
        </footer>
      </article>
    </div>
  );

  return createPortal(node, document.body);
}

function CoverRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-slate-100 pb-1">
      <dt className="text-small text-slate-500">{label}</dt>
      <dd className={`text-body text-slate-900 ${mono ? "font-id" : ""}`}>{value}</dd>
    </div>
  );
}
