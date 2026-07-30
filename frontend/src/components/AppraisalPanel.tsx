import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { getAppraisal, upsertAppraisal, type AppraisalData } from "@/lib/api";
import { Button, Field, Input, Textarea, Alert, EmptyState, Skeleton, useToast } from "@/components/ui";
import { formatCurrency, formatDate } from "@/lib/format";

type Props = {
  parcelId: string;
};

export function AppraisalPanel({ parcelId }: Props) {
  const toast = useToast();
  const [appraisal, setAppraisal] = useState<AppraisalData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Edit mode
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState("");
  const [summary, setSummary] = useState("");
  const [saving, setSaving] = useState(false);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const res = await getAppraisal(parcelId);
      setAppraisal(res.appraisal ?? null);
      if (res.appraisal) {
        setValue(res.appraisal.value?.toString() ?? "");
        setSummary(res.appraisal.summary ?? "");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setAppraisal(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, [parcelId]);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await upsertAppraisal({
        parcel_id: parcelId,
        value: value ? Number(value) : undefined,
        summary: summary || undefined,
        comps: appraisal?.comps ?? [],
      });
      setEditing(false);
      toast.success("Appraisal saved");
      await refresh();
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      setError(message);
      toast.error("Couldn't save appraisal", message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-card border border-slate-200 bg-white p-6 shadow-card">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-h3 font-semibold">Appraisal</h3>
          <p className="text-small text-slate-500">
            Parcel <span className="font-id">{parcelId}</span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={refresh}
            disabled={loading}
            aria-label="Refresh appraisal"
            title="Refresh"
          >
            <RefreshCw className="h-4 w-4" aria-hidden />
          </Button>
          {!editing && (
            <Button size="sm" onClick={() => setEditing(true)}>
              {appraisal ? "Edit" : "Add"}
            </Button>
          )}
        </div>
      </div>

      {error && (
        <Alert variant="danger" title="Couldn't load appraisal" className="mb-3">
          {error}
        </Alert>
      )}
      {loading && !editing ? (
        <Skeleton className="h-24 w-full" />
      ) : editing ? (
        <div className="space-y-4">
          <Field label="Appraised value">
            {(field) => (
              <div className="relative">
                <span className="absolute left-3 top-2 text-slate-500">$</span>
                <Input
                  {...field}
                  type="number"
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
                  className="pl-7"
                  placeholder="350000"
                />
              </div>
            )}
          </Field>
          <Field label="Summary">
            {(field) => (
              <Textarea
                {...field}
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                rows={4}
                placeholder="Appraisal methodology and key findings..."
              />
            )}
          </Field>
          <div className="flex gap-2">
            <Button onClick={handleSave} loading={saving}>
              {saving ? "Saving..." : "Save"}
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                setEditing(false);
                setError(null);
                setValue(appraisal?.value?.toString() ?? "");
                setSummary(appraisal?.summary ?? "");
              }}
            >
              Cancel
            </Button>
          </div>
        </div>
      ) : appraisal ? (
        <div className="space-y-4">
          <div className="flex items-baseline justify-between">
            <span className="text-small text-slate-600">Appraised value</span>
            <span className="text-2xl font-semibold tabular-nums text-slate-900">
              {formatCurrency(appraisal.value)}
            </span>
          </div>

          {appraisal.summary && (
            <div>
              <span className="text-small font-medium text-slate-700">Summary</span>
              <p className="mt-1 text-small text-slate-600">{appraisal.summary}</p>
            </div>
          )}

          {appraisal.completed_at && (
            <p className="text-caption text-slate-500">
              Completed {formatDate(appraisal.completed_at)}
            </p>
          )}

          {appraisal.comps && appraisal.comps.length > 0 && (
            <div>
              <span className="text-small font-medium text-slate-700">Comparable sales</span>
              <ul className="mt-2 space-y-2">
                {appraisal.comps.map((comp, idx) => (
                  <li
                    key={idx}
                    className="flex justify-between text-small py-2 border-b border-slate-100 last:border-0"
                  >
                    <span className="text-slate-700">{String(comp.address ?? `Comp ${idx + 1}`)}</span>
                    <span className="text-slate-900 font-medium tabular-nums">
                      {formatCurrency(comp.sale_price as number | undefined)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : (
        <EmptyState
          title="No appraisal yet"
          message="No appraisal data is available for this parcel. Add one to record value and comps."
        />
      )}
    </div>
  );
}
