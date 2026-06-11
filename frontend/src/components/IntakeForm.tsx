import { useState, useEffect, useCallback, useMemo } from "react";
import { createCase, getJurisdictions, type JurisdictionItem } from "@/lib/api";
import { useAppContext } from "@/context";
import { useNavigate } from "react-router-dom";
import { Field, Input, Select, Button, Alert, useToast } from "@/components/ui";

// Common Texas county FIPS codes for smart suggestions
const TEXAS_COUNTIES: Record<string, string> = {
  "48439": "Tarrant County",
  "48113": "Dallas County",
  "48201": "Harris County",
  "48029": "Bexar County",
  "48453": "Travis County",
  "48141": "El Paso County",
  "48085": "Collin County",
  "48121": "Denton County",
  "48215": "Hidalgo County",
  "48157": "Fort Bend County",
};

// State FIPS prefixes allowed for Milestone 1 contract jurisdictions (TX, IN only)
const STATE_PREFIXES: Record<string, string> = {
  "48": "TX",
  "18": "IN",
};

type Props = {
  initialProjectId: string;
  onPartyAdd?: (party: { name: string; role: string; email?: string }) => void;
};

export function IntakeForm({ initialProjectId }: Props) {
  const navigate = useNavigate();
  const toast = useToast();
  const { setProjectId: setSelectedProjectId, setParcelId } = useAppContext();
  const [projectId, setProjectId] = useState(initialProjectId);
  const [countyFips, setCountyFips] = useState("48439");
  const [jurisdiction, setJurisdiction] = useState("TX");
  const [jurisdictionOptions, setJurisdictionOptions] = useState<JurisdictionItem[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<{ projectId?: string; countyFips?: string }>({});
  const [showSuggestions, setShowSuggestions] = useState(false);

  const [ownerName, setOwnerName] = useState("");
  const [ownerEmail, setOwnerEmail] = useState("");
  const [propertyAddress, setPropertyAddress] = useState("");
  const [estimatedValue, setEstimatedValue] = useState<number | "">("");
  const [riskLevel, setRiskLevel] = useState<"low" | "medium" | "high">("medium");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await getJurisdictions();
        if (cancelled) return;
        setJurisdictionOptions(res.items);
        if (res.items.length && !res.items.some((i) => i.code === jurisdiction)) {
          setJurisdiction(res.items[0].code);
        }
      } catch {
        if (!cancelled) setJurisdictionOptions([]);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only load jurisdiction list once on mount
  }, []);

  useEffect(() => {
    if (initialProjectId && !projectId.trim()) {
      setProjectId(initialProjectId);
    }
  }, [initialProjectId, projectId]);

  useEffect(() => {
    const prefix = countyFips.slice(0, 2);
    const detectedJurisdiction = STATE_PREFIXES[prefix];
    const allowedCodes = new Set(jurisdictionOptions.map((j) => j.code));
    if (
      detectedJurisdiction &&
      allowedCodes.has(detectedJurisdiction) &&
      detectedJurisdiction !== jurisdiction
    ) {
      setJurisdiction(detectedJurisdiction);
    }
  }, [countyFips, jurisdiction, jurisdictionOptions]);

  const countyName = useMemo(() => TEXAS_COUNTIES[countyFips] || null, [countyFips]);

  const fipsSuggestions = useMemo(() => {
    if (!countyFips || countyFips.length < 2) return [];
    return Object.entries(TEXAS_COUNTIES)
      .filter(
        ([fips, name]) =>
          fips.startsWith(countyFips) || name.toLowerCase().includes(countyFips.toLowerCase()),
      )
      .slice(0, 5);
  }, [countyFips]);

  const getRiskScore = useCallback((level: "low" | "medium" | "high") => {
    switch (level) {
      case "low":
        return 25;
      case "medium":
        return 50;
      case "high":
        return 75;
    }
  }, []);

  function validate(): boolean {
    const errs: { projectId?: string; countyFips?: string } = {};
    if (!projectId.trim()) errs.projectId = "Select a project before creating a parcel case.";
    if (!/^\d{5}$/.test(countyFips.trim())) errs.countyFips = "Enter a 5-digit county FIPS code.";
    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setFormError(null);
    if (!validate()) return;

    setSubmitting(true);
    const parties = [];
    if (ownerName) {
      parties.push({ name: ownerName, role: "landowner", email: ownerEmail || undefined });
    }

    try {
      const response = await createCase({
        project_id: projectId.trim(),
        jurisdiction_code: jurisdiction,
        parcels: [
          { county_fips: countyFips, stage: "intake", risk_score: getRiskScore(riskLevel), parties },
        ],
      });
      const parcelId = response.parcel_ids?.[0];
      toast.success(
        "Parcel case created",
        parcelId ? `Created parcel ${parcelId}.` : "No parcels were returned.",
      );
      if (parcelId) {
        setSelectedProjectId(projectId.trim());
        setParcelId(parcelId);
        navigate(
          `/workbench?projectId=${encodeURIComponent(projectId.trim())}&parcelId=${encodeURIComponent(parcelId)}`,
        );
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setFormError(message);
      toast.error("Could not create parcel case", message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-card border border-slate-200 bg-white shadow-card">
      <div className="border-b border-slate-200 bg-slate-50 px-6 py-4">
        <h3 className="text-h3 text-slate-900">Intake form</h3>
        <p className="text-small text-slate-600">Create a new parcel case with smart field detection.</p>
      </div>

      <div className="space-y-4 p-6">
        {formError ? <Alert variant="danger" title="Submission failed">{formError}</Alert> : null}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field label="Project ID" required error={fieldErrors.projectId}>
            {(p) => (
              <Input
                {...p}
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
                placeholder="Project identifier"
              />
            )}
          </Field>

          <Field
            label="County FIPS"
            required
            error={fieldErrors.countyFips}
            hint={countyName ?? "5-digit Federal Information Processing Standard county code"}
          >
            {(p) => (
              <div className="relative">
                <Input
                  {...p}
                  value={countyFips}
                  onChange={(e) => {
                    setCountyFips(e.target.value);
                    setShowSuggestions(true);
                  }}
                  onFocus={() => setShowSuggestions(true)}
                  onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                  placeholder="e.g. 48439"
                  inputMode="numeric"
                />
                {showSuggestions && fipsSuggestions.length > 0 && (
                  <div className="absolute z-10 mt-1 w-full overflow-hidden rounded-control border border-slate-200 bg-white shadow-overlay">
                    {fipsSuggestions.map(([fips, name]) => (
                      <button
                        key={fips}
                        type="button"
                        onMouseDown={() => {
                          setCountyFips(fips);
                          setShowSuggestions(false);
                        }}
                        className="flex w-full items-center justify-between px-3 py-2 text-small hover:bg-slate-50"
                      >
                        <span className="font-id font-medium">{fips}</span>
                        <span className="text-slate-500">{name}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </Field>
        </div>

        <Field label="Jurisdiction" hint="Auto-detected from the county FIPS code.">
          {(p) => (
            <Select
              {...p}
              value={jurisdiction}
              onChange={(e) => setJurisdiction(e.target.value)}
            >
              {(jurisdictionOptions.length
                ? jurisdictionOptions
                : [{ code: "TX", label: "Texas", active: true }]
              ).map((j) => (
                <option key={j.code} value={j.code}>
                  {j.label}
                </option>
              ))}
            </Select>
          )}
        </Field>

        <div className="border-t border-slate-200 pt-4">
          <h4 className="mb-3 text-small font-medium text-slate-700">Landowner information (optional)</h4>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Owner name">
              {(p) => (
                <Input {...p} value={ownerName} onChange={(e) => setOwnerName(e.target.value)} placeholder="John Smith" />
              )}
            </Field>
            <Field label="Owner email">
              {(p) => (
                <Input
                  {...p}
                  type="email"
                  value={ownerEmail}
                  onChange={(e) => setOwnerEmail(e.target.value)}
                  placeholder="owner@email.com"
                />
              )}
            </Field>
          </div>
        </div>

        <div className="border-t border-slate-200 pt-4">
          <h4 className="mb-3 text-small font-medium text-slate-700">Property details</h4>
          <div className="space-y-4">
            <Field label="Property address (optional)">
              {(p) => (
                <Input
                  {...p}
                  value={propertyAddress}
                  onChange={(e) => setPropertyAddress(e.target.value)}
                  placeholder="123 Main St, City, State"
                />
              )}
            </Field>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label="Estimated value (USD)">
                {(p) => (
                  <Input
                    {...p}
                    type="number"
                    value={estimatedValue}
                    onChange={(e) => setEstimatedValue(e.target.value ? Number(e.target.value) : "")}
                    placeholder="350000"
                  />
                )}
              </Field>
              <Field label="Initial risk assessment">
                {(p) => (
                  <Select
                    {...p}
                    value={riskLevel}
                    onChange={(e) => setRiskLevel(e.target.value as "low" | "medium" | "high")}
                  >
                    <option value="low">Low risk</option>
                    <option value="medium">Medium risk</option>
                    <option value="high">High risk</option>
                  </Select>
                )}
              </Field>
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-end border-t border-slate-200 bg-slate-50 px-6 py-4">
        <Button type="submit" loading={submitting}>
          Create parcel case
        </Button>
      </div>
    </form>
  );
}
