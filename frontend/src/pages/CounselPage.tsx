import { useState } from "react";
import { useAppContext } from "@/context";
import { CounselQueue } from "@/components/CounselQueue";
import { BudgetPanel } from "@/components/BudgetPanel";
import { BinderStatus } from "@/components/BinderStatus";
import { DeadlineManager } from "@/components/DeadlineManager";
import { TemplateViewer } from "@/components/TemplateViewer";
import { OutsideCounselPanel } from "@/components/OutsideCounselPanel";
import { AIDecisionReview } from "@/components/AIDecisionReview";
import { CopilotPanel } from "@/components/CopilotPanel";
import { SettlementPredictor } from "@/components/SettlementPredictor";

export function CounselPage() {
  const { projectId, parcelId } = useAppContext();
  const effectiveParcelId = parcelId ?? "PARCEL-001";
  const [showCopilot, setShowCopilot] = useState(false);

  return (
    <div className="flex h-full">
      {/* Main content */}
      <section className={`flex-1 space-y-6 transition-all ${showCopilot ? "mr-96" : ""}`}>
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm uppercase tracking-wide text-brand">Counsel controls</p>
            <h1 className="mt-2 text-3xl font-semibold">Template approvals, binder exports, budgets</h1>
            <p className="mt-2 max-w-3xl text-slate-600">
              Deterministic gate before filings, with audit logging + outside counsel handoffs per scope instructions.
            </p>
          </div>
          <button
            onClick={() => setShowCopilot(!showCopilot)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
              showCopilot
                ? "bg-brand text-white border-brand"
                : "bg-white text-slate-700 border-slate-200 hover:border-brand hover:text-brand"
            }`}
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
            <span className="text-sm font-medium">AI Copilot</span>
          </button>
        </div>

        {/* Original counsel components */}
        <div className="grid gap-4 md:grid-cols-2">
          <CounselQueue />
          <BudgetPanel projectId={projectId} />
        </div>

        {/* Binder and Deadline management */}
        <div className="grid gap-4 lg:grid-cols-2">
          <BinderStatus projectId={projectId} />
          <DeadlineManager projectId={projectId} />
        </div>

        {/* Template library */}
        <TemplateViewer />

        {/* AI Decision Review & Settlement Predictor */}
        <div className="grid gap-4 lg:grid-cols-2">
          <AIDecisionReview />
          <SettlementPredictor
            parcelId={effectiveParcelId}
            jurisdiction="TX"
            assessedValue={350000}
          />
        </div>

        {/* Outside counsel handoff */}
        <OutsideCounselPanel projectId={projectId} parcelId={effectiveParcelId} />
      </section>

      {/* Copilot Panel */}
      {showCopilot && (
        <div className="fixed right-0 top-0 h-screen w-96 shadow-xl z-50">
          <CopilotPanel
            caseId={projectId}
            parcelId={effectiveParcelId}
            jurisdiction="TX"
            isOpen={showCopilot}
            onClose={() => setShowCopilot(false)}
          />
        </div>
      )}
    </div>
  );
}
