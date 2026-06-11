import { useCallback, useEffect, useState } from "react";
import {
  listParcels,
  validateComplaintParcels,
  type ParcelItem,
} from "@/lib/api";
import { LoadingSpinner, ErrorMessage } from "@/components/ui";

type Props = {
  projectId: string;
};

export function ComplaintParcelsValidatePanel({ projectId }: Props) {
  const [parcels, setParcels] = useState<ParcelItem[] | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ ok: boolean; errors: string[] } | null>(null);
  const [validating, setValidating] = useState(false);

  const load = useCallback(() => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    listParcels({ project_id: projectId, limit: 200 })
      .then((res) => {
        setParcels(res.items);
        setResult(null);
      })
      .catch((e) => {
        setParcels(null);
        setError(String(e));
      })
      .finally(() => setLoading(false));
  }, [projectId]);

  useEffect(() => {
    load();
  }, [load]);

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
    setResult(null);
  }

  async function runValidate() {
    const ids = [...selected];
    setValidating(true);
    setError(null);
    setResult(null);
    try {
      const res = await validateComplaintParcels({
        project_id: projectId,
        parcel_ids: ids,
      });
      setResult({ ok: res.ok, errors: res.errors ?? [] });
    } catch (e) {
      setError(String(e));
    } finally {
      setValidating(false);
    }
  }

  return (
    <div
      className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
      data-testid="complaint-parcel-validate-panel"
    >
      <h3 className="text-lg font-semibold">Multi-parcel complaint check</h3>
      <p className="mt-1 text-sm text-slate-600">
        Select two or more parcels on this project. The API verifies they belong to the project and share the same
        county (filing alignment guard).
      </p>

      {loading && (
        <div className="mt-4">
          <LoadingSpinner text="Loading parcels…" />
        </div>
      )}

      {error && (
        <div className="mt-4">
          <ErrorMessage message={error} onRetry={load} />
        </div>
      )}

      {!loading && !error && parcels && parcels.length < 2 && (
        <p className="mt-4 text-sm text-amber-800">This project has fewer than two parcels — add another parcel to run validation.</p>
      )}

      {!loading && !error && parcels && parcels.length >= 2 && (
        <>
          <ul className="mt-4 max-h-56 space-y-2 overflow-y-auto text-sm">
            {parcels.map((p) => (
              <li key={p.id} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id={`cpv-${p.id}`}
                  checked={selected.has(p.id)}
                  onChange={() => toggle(p.id)}
                  className="h-4 w-4 rounded border-slate-300"
                />
                <label htmlFor={`cpv-${p.id}`} className="cursor-pointer text-slate-800">
                  {p.id}
                  <span className="ml-2 text-slate-500">({p.stage})</span>
                </label>
              </li>
            ))}
          </ul>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={runValidate}
              disabled={validating || selected.size < 2}
              className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-dark disabled:opacity-50"
              data-testid="complaint-parcel-validate-submit"
            >
              {validating ? "Validating…" : "Run validation"}
            </button>
            <span className="text-xs text-slate-500">{selected.size} parcel(s) selected</span>
          </div>
        </>
      )}

      {result && (
        <div
          className={`mt-4 rounded-md border px-3 py-2 text-sm ${
            result.ok ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-amber-200 bg-amber-50 text-amber-900"
          }`}
          data-testid="complaint-parcel-validate-result"
        >
          <p className="font-medium">{result.ok ? "OK — parcels pass combined complaint checks." : "Validation failed"}</p>
          {result.errors.length > 0 ? (
            <ul className="mt-2 list-disc pl-5">
              {result.errors.map((err) => (
                <li key={err}>{err}</li>
              ))}
            </ul>
          ) : null}
        </div>
      )}
    </div>
  );
}
