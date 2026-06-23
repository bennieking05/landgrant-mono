import { useState, lazy, Suspense } from "react";
import { useAppContext } from "@/context";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { InviteCard } from "@/components/InviteCard";
import { UploadPanel } from "@/components/UploadPanel";

const ParcelMap = lazy(() => import("@/components/ParcelMap").then(m => ({ default: m.ParcelMap })));
import { DecisionActions } from "@/components/DecisionActions";

const STEPS = [
  { label: "Verify Identity", number: 1 },
  { label: "Review Documents", number: 2 },
  { label: "Upload Materials", number: 3 },
  { label: "Make Decision", number: 4 },
] as const;

const STEP_HINTS = [
  "Confirm your invite and identity so we can show the right parcel file.",
  "See your parcel on the map and any documents the agency has shared.",
  "Add deeds, photos, or other files that support your position.",
  "Accept, counter, or decline — your attorney still reviews before anything is final.",
] as const;

function StepIndicator({ currentStep, onStepClick }: { currentStep: number; onStepClick: (step: number) => void }) {
  return (
    <nav className="flex min-w-0 items-center justify-between gap-2 overflow-x-auto pb-1 sm:pb-0">
      {STEPS.map((step, idx) => (
        <div key={step.number} className="flex items-center flex-1 last:flex-initial">
          <button
            type="button"
            onClick={() => onStepClick(idx)}
            className="flex flex-col items-center gap-1.5 group"
          >
            <span
              className={`flex h-10 w-10 items-center justify-center rounded-full border-2 text-sm font-semibold transition-colors ${
                idx === currentStep
                  ? "border-brand bg-brand text-white"
                  : idx < currentStep
                    ? "border-brand bg-brand/10 text-brand"
                    : "border-slate-300 bg-white text-slate-400"
              }`}
            >
              {idx < currentStep ? (
                <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
              ) : (
                step.number
              )}
            </span>
            <span
              className={`text-xs font-medium whitespace-nowrap ${
                idx === currentStep ? "text-brand" : idx < currentStep ? "text-slate-700" : "text-slate-500"
              }`}
            >
              {step.label}
            </span>
          </button>

          {idx < STEPS.length - 1 && (
            <div className="flex-1 mx-3 mt-[-1.25rem]">
              <div
                className={`h-0.5 w-full rounded ${idx < currentStep ? "bg-brand" : "bg-slate-200"}`}
              />
            </div>
          )}
        </div>
      ))}
    </nav>
  );
}

export function IntakePage() {
  const { projectId, parcelId, parcels } = useAppContext();
  useDocumentTitle("Landowner portal");
  const [currentStep, setCurrentStep] = useState(0);

  const isFirst = currentStep === 0;
  const isLast = currentStep === STEPS.length - 1;

  return (
    <section className="space-y-6">
      <div>
        <p className="text-sm uppercase tracking-wide text-brand">Landowner portal</p>
        <h1 className="mt-2 text-2xl font-semibold sm:text-3xl">Invite &rarr; review &rarr; e-sign</h1>
        <p className="mt-2 max-w-3xl text-slate-600">
          Complete each step to finalize your property review: verify your identity, review documents,
          upload materials, and make your decision.
        </p>
      </div>

      {/* Step indicator */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
        <StepIndicator currentStep={currentStep} onStepClick={setCurrentStep} />
        <p className="mt-4 rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-700">
          {STEP_HINTS[currentStep]}
        </p>
      </div>

      {/* Step content */}
      <div className="min-h-[280px] sm:min-h-[320px]">
        {currentStep === 0 && (
          parcelId ? (
            <InviteCard projectId={projectId} parcelId={parcelId} />
          ) : (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-800">
              Select or create a parcel before sending a portal invite.
            </div>
          )
        )}
        {currentStep === 1 && (
          <Suspense fallback={<div className="h-96 flex items-center justify-center bg-slate-100 rounded-xl"><div className="animate-spin h-8 w-8 border-2 border-blue-600 border-t-transparent rounded-full" /></div>}>
            <ParcelMap parcelData={parcels} selectedParcelId={parcelId ?? undefined} showFilters={false} />
          </Suspense>
        )}
        {currentStep === 2 && (
          parcelId ? (
            <UploadPanel parcelId={parcelId} />
          ) : (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-800">
              Select a parcel before uploading documents.
            </div>
          )
        )}
        {currentStep === 3 && (
          parcelId ? (
            <DecisionActions parcelId={parcelId} />
          ) : (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-800">
              Select a parcel before submitting a decision.
            </div>
          )
        )}
      </div>

      {/* Navigation buttons */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          disabled={isFirst}
          onClick={() => setCurrentStep((s) => s - 1)}
          className={`inline-flex items-center gap-2 rounded-lg border px-5 py-2.5 text-sm font-medium transition-colors ${
            isFirst
              ? "cursor-not-allowed border-slate-200 text-slate-300"
              : "border-slate-300 text-slate-700 hover:bg-slate-50"
          }`}
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
          </svg>
          Back
        </button>

        <span className="text-sm text-slate-500">
          Step {currentStep + 1} of {STEPS.length}
        </span>

        <button
          type="button"
          disabled={isLast}
          onClick={() => setCurrentStep((s) => s + 1)}
          className={`inline-flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-medium transition-colors ${
            isLast
              ? "cursor-not-allowed bg-slate-100 text-slate-300"
              : "bg-brand text-white hover:bg-brand/90"
          }`}
        >
          Next
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
          </svg>
        </button>
      </div>
    </section>
  );
}
