import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Check, FileText, ArrowRight, ArrowLeft, CheckCircle2, ChevronRight } from "lucide-react";
import { useAppContext } from "@/context";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import {
  apiGet,
  apiPostJson,
  listOffers,
  listTitleInstruments,
  type OfferItem,
  type TitleInstrumentItem,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { Button, Card, CardBody, Skeleton } from "@/components/ui";

const STEP_KEYS = ["welcome", "property", "documents", "offer", "decision"] as const;

const DECISION_META: Record<string, { labelKey: string; hintKey: string; tone: string }> = {
  accept: { labelKey: "portal.decision.accept", hintKey: "portal.decision.acceptHint", tone: "border-success-border hover:bg-success-bg" },
  counter: { labelKey: "portal.decision.question", hintKey: "portal.decision.questionHint", tone: "border-info-border hover:bg-info-bg" },
  request_call: { labelKey: "portal.decision.question", hintKey: "portal.decision.questionHint", tone: "border-info-border hover:bg-info-bg" },
  question: { labelKey: "portal.decision.question", hintKey: "portal.decision.questionHint", tone: "border-info-border hover:bg-info-bg" },
  decline: { labelKey: "portal.decision.decline", hintKey: "portal.decision.declineHint", tone: "border-warning-border hover:bg-warning-bg" },
};

function Stepper({ current }: { current: number }) {
  const { t } = useTranslation();
  return (
    <ol className="flex items-center justify-between gap-1" aria-label="Progress">
      {STEP_KEYS.map((key, i) => {
        const done = i < current;
        const active = i === current;
        return (
          <li key={key} className="flex flex-1 flex-col items-center gap-1.5 last:flex-initial">
            <span
              className={`flex h-9 w-9 items-center justify-center rounded-full border-2 text-small font-semibold ${
                active
                  ? "border-brand bg-brand text-white"
                  : done
                    ? "border-brand bg-brand/10 text-brand"
                    : "border-slate-300 bg-white text-slate-400"
              }`}
              aria-current={active ? "step" : undefined}
            >
              {done ? <Check className="h-4 w-4" /> : i + 1}
            </span>
            <span className={`hidden text-caption sm:block ${active ? "font-semibold text-brand" : "text-slate-500"}`}>
              {t(`portal.steps.${key}`)}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

export function PortalPage() {
  const { t } = useTranslation();
  const { parcels, parcelId } = useAppContext();
  useDocumentTitle(t("portal.steps.welcome"));

  const parcel = useMemo(
    () => parcels.find((p) => p.id === parcelId) ?? parcels[0] ?? null,
    [parcels, parcelId],
  );

  const [step, setStep] = useState(0);
  const [offers, setOffers] = useState<OfferItem[]>([]);
  const [docs, setDocs] = useState<TitleInstrumentItem[]>([]);
  const [options, setOptions] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  const [submitting, setSubmitting] = useState<string | null>(null);
  const [confirmation, setConfirmation] = useState<string | null>(null);
  const [decisionError, setDecisionError] = useState<string | null>(null);

  // Load portal data once for the parcel (no polling - portal audience is mobile).
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    (async () => {
      const id = parcel?.id;
      const [optRes, offersRes, docsRes] = await Promise.allSettled([
        apiGet<{ options: string[] }>("/portal/decision/options"),
        id ? listOffers(id) : Promise.resolve({ items: [] as OfferItem[] }),
        id ? listTitleInstruments(id) : Promise.resolve({ items: [] as TitleInstrumentItem[] }),
      ]);
      if (cancelled) return;
      if (optRes.status === "fulfilled") setOptions(optRes.value.options ?? []);
      if (offersRes.status === "fulfilled") setOffers((offersRes.value as { items: OfferItem[] }).items ?? []);
      if (docsRes.status === "fulfilled") setDocs((docsRes.value as { items: TitleInstrumentItem[] }).items ?? []);
      setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [parcel?.id]);

  const latestOffer = offers[0];

  async function submitDecision(selection: string) {
    if (!parcel) return;
    setSubmitting(selection);
    setDecisionError(null);
    try {
      const res = await apiPostJson<{ routed_to: string; decision_id: string }>("/portal/decision", {
        parcel_id: parcel.id,
        selection,
      });
      setConfirmation(res.decision_id);
    } catch {
      setDecisionError(t("portal.decision.error"));
    } finally {
      setSubmitting(null);
    }
  }

  if (loading && !parcel) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Stepper current={step} />

      {step === 0 && (
        <Card>
          <CardBody className="space-y-3">
            <h1 className="text-h1 text-slate-900">{t("portal.welcome.title")}</h1>
            <p className="text-body text-slate-700">{t("portal.welcome.body")}</p>
            <div className="rounded-control border border-info-border bg-info-bg p-3 text-body text-info-fg">
              {t("portal.welcome.reassure")}
            </div>
            <div className="pt-2">
              <Button size="md" onClick={() => setStep(1)}>
                {t("portal.welcome.cta")} <ArrowRight className="h-4 w-4" />
              </Button>
            </div>
          </CardBody>
        </Card>
      )}

      {step === 1 && (
        <Card>
          <CardBody className="space-y-3">
            <h1 className="text-h1 text-slate-900">{t("portal.property.title")}</h1>
            <p className="text-body text-slate-700">{t("portal.property.intro")}</p>
            {parcel ? (
              <dl className="divide-y divide-slate-100 rounded-control border border-slate-200">
                <Row label={t("portal.property.parcel")} value={parcel.id} mono />
                <Row label={t("portal.property.county")} value={parcel.county_fips ?? "-"} mono />
                <Row label={t("portal.property.owner")} value={parcel.owner ?? "-"} />
              </dl>
            ) : (
              <p className="rounded-control border border-warning-border bg-warning-bg p-3 text-body text-warning-fg">
                {t("portal.property.none")}
              </p>
            )}
          </CardBody>
        </Card>
      )}

      {step === 2 && (
        <Card>
          <CardBody className="space-y-3">
            <h1 className="text-h1 text-slate-900">{t("portal.documents.title")}</h1>
            <p className="text-body text-slate-700">{t("portal.documents.intro")}</p>
            {docs.length === 0 ? (
              <p className="rounded-control border border-slate-200 bg-slate-50 p-4 text-body text-slate-600">
                {t("portal.documents.none")}
              </p>
            ) : (
              <ul className="space-y-3">
                {docs.map((d) => {
                  const kind = (d.metadata?.instrument_type as string) || (d.ocr_payload?.type as string) || "Document";
                  return (
                    <li key={d.id} className="rounded-control border border-slate-200 p-4">
                      <p className="flex items-center gap-2 text-h3 text-slate-900">
                        <FileText className="h-5 w-5 text-brand" /> {kind}
                      </p>
                      <p className="mt-1 text-caption font-medium uppercase text-slate-400">
                        {t("portal.documents.summaryLabel")}
                      </p>
                      <p className="text-body text-slate-700">
                        {(d.metadata?.plain_summary as string) ||
                          "This document is part of your property file. Your attorney can explain anything you do not understand."}
                      </p>
                    </li>
                  );
                })}
              </ul>
            )}
          </CardBody>
        </Card>
      )}

      {step === 3 && (
        <Card>
          <CardBody className="space-y-3">
            <h1 className="text-h1 text-slate-900">{t("portal.offer.title")}</h1>
            <p className="text-body text-slate-700">{t("portal.offer.intro")}</p>
            {latestOffer ? (
              <div className="rounded-control border border-slate-200 p-4">
                <p className="text-caption font-medium uppercase text-slate-400">{t("portal.offer.amount")}</p>
                <p className="text-display text-slate-900">
                  {latestOffer.amount != null ? formatCurrency(latestOffer.amount) : "-"}
                </p>
                {latestOffer.terms_summary ? (
                  <>
                    <p className="mt-3 text-caption font-medium uppercase text-slate-400">
                      {t("portal.offer.summaryLabel")}
                    </p>
                    <p className="text-body text-slate-700">{latestOffer.terms_summary}</p>
                  </>
                ) : null}
              </div>
            ) : (
              <p className="rounded-control border border-slate-200 bg-slate-50 p-4 text-body text-slate-600">
                {t("portal.offer.none")}
              </p>
            )}
          </CardBody>
        </Card>
      )}

      {step === 4 && (
        <Card>
          <CardBody className="space-y-4">
            <h1 className="text-h1 text-slate-900">{t("portal.decision.title")}</h1>
            {confirmation ? (
              <div role="status" aria-live="polite" className="rounded-card border border-success-border bg-success-bg p-5 text-success-fg">
                <p className="flex items-center gap-2 text-h2">
                  <CheckCircle2 className="h-6 w-6" /> {t("portal.decision.confirmTitle")}
                </p>
                <p className="mt-2 text-body">{t("portal.decision.confirmBody")}</p>
                <div className="mt-3 rounded-control border border-success-border bg-white px-4 py-3">
                  <p className="text-caption font-medium uppercase text-slate-500">
                    {t("portal.decision.reference")}
                  </p>
                  <p className="font-id text-h3 text-slate-900">{confirmation}</p>
                </div>
                <p className="mt-3 text-body">{t("portal.decision.whatNext")}</p>
              </div>
            ) : (
              <>
                <p className="text-body text-slate-700">{t("portal.decision.intro")}</p>
                {decisionError ? (
                  <p role="alert" className="rounded-control border border-danger-border bg-danger-bg p-3 text-body text-danger-fg">
                    {decisionError}
                  </p>
                ) : null}
                <div className="space-y-3">
                  {(options.length ? options : ["Accept", "Counter", "Decline"]).map((opt) => {
                    const key = opt.toLowerCase().replace(/\s+/g, "_");
                    const meta = DECISION_META[key] ?? {
                      labelKey: "",
                      hintKey: "",
                      tone: "border-slate-200 hover:bg-slate-50",
                    };
                    const label = meta.labelKey ? t(meta.labelKey) : opt;
                    const hint = meta.hintKey ? t(meta.hintKey) : "";
                    return (
                      <button
                        key={opt}
                        type="button"
                        disabled={Boolean(submitting)}
                        onClick={() => submitDecision(opt)}
                        className={`flex w-full items-center justify-between gap-3 rounded-card border-2 bg-white p-4 text-left transition-colors disabled:opacity-60 ${meta.tone}`}
                      >
                        <span>
                          <span className="block text-h3 text-slate-900">{label}</span>
                          {hint ? <span className="block text-small text-slate-600">{hint}</span> : null}
                        </span>
                        <ChevronRight className="h-5 w-5 shrink-0 text-slate-400" />
                      </button>
                    );
                  })}
                </div>
                <p aria-live="polite" className="text-small text-slate-500">
                  {submitting ? t("portal.decision.submitting") : ""}
                </p>
              </>
            )}
          </CardBody>
        </Card>
      )}

      {/* Navigation */}
      {!confirmation && (
        <div className="flex items-center justify-between">
          <Button variant="secondary" onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0}>
            <ArrowLeft className="h-4 w-4" /> {t("portal.back")}
          </Button>
          {step < STEP_KEYS.length - 1 ? (
            <Button onClick={() => setStep((s) => Math.min(STEP_KEYS.length - 1, s + 1))}>
              {t("portal.next")} <ArrowRight className="h-4 w-4" />
            </Button>
          ) : (
            <span />
          )}
        </div>
      )}
    </div>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between px-4 py-3">
      <dt className="text-small text-slate-500">{label}</dt>
      <dd className={`text-body text-slate-900 ${mono ? "font-id" : ""}`}>{value}</dd>
    </div>
  );
}
