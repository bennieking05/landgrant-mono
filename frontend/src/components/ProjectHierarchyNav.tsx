import { useEffect, useState } from "react";
import { getProjectHierarchy, type ProjectHierarchyResponse } from "@/lib/api";

type Props = {
  projectId: string;
  selectedParcelId?: string | null;
  onSelectParcel: (parcelId: string) => void;
};

export function ProjectHierarchyNav({ projectId, selectedParcelId, onSelectParcel }: Props) {
  const [data, setData] = useState<ProjectHierarchyResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setErr(null);
    (async () => {
      try {
        const r = await getProjectHierarchy(projectId);
        if (!cancelled) setData(r);
      } catch (e) {
        if (!cancelled) {
          setData(null);
          setErr(String(e));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  if (!projectId.trim()) return null;
  if (err) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
        Could not load project hierarchy: {err}
      </div>
    );
  }
  if (!data) {
    return (
      <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
        Loading project hierarchy…
      </div>
    );
  }

  const crumbs: string[] = [data.project.name || data.project.id];
  if (selectedParcelId) crumbs.push(`Parcel ${selectedParcelId}`);

  return (
    <nav
      className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700 shadow-sm"
      aria-label="Project hierarchy"
    >
      <div className="flex flex-wrap items-center gap-1">
        <span className="font-semibold text-slate-900">{crumbs.join(" · ")}</span>
        <span className="text-slate-400">|</span>
        <span className="text-slate-500">
          State {data.project.state ?? data.project.jurisdiction_code}
        </span>
      </div>
      <div className="mt-2 max-h-40 overflow-y-auto space-y-2">
        {data.alignments.length === 0 && data.unassigned_parcels.length === 0 && (
          <p className="text-slate-500">No alignments or parcels yet.</p>
        )}
        {data.alignments.map((a) => (
          <div key={a.id}>
            <p className="font-medium text-slate-800">Alignment: {a.name}</p>
            <ul className="ml-2 mt-1 space-y-1">
              {a.segments.map((s) => (
                <li key={s.id}>
                  <span className="text-slate-600">Segment {s.name ?? s.id}</span>
                  <ul className="ml-3 mt-0.5">
                    {s.parcels.map((p) => (
                      <li key={p.id}>
                        <button
                          type="button"
                          className={`text-left underline-offset-2 hover:underline ${
                            selectedParcelId === p.id ? "text-brand font-semibold" : "text-slate-700"
                          }`}
                          onClick={() => onSelectParcel(p.id)}
                        >
                          {p.id} · {p.stage ?? "—"}
                        </button>
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          </div>
        ))}
        {data.unassigned_parcels.length > 0 && (
          <div>
            <p className="font-medium text-slate-800">Unassigned parcels</p>
            <ul className="ml-2 mt-1 space-y-1">
              {data.unassigned_parcels.map((p) => (
                <li key={p.id}>
                  <button
                    type="button"
                    className={`text-left underline-offset-2 hover:underline ${
                      selectedParcelId === p.id ? "text-brand font-semibold" : "text-slate-700"
                    }`}
                    onClick={() => onSelectParcel(p.id)}
                  >
                    {p.id} · {p.stage ?? "—"}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </nav>
  );
}
