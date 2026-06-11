import { useState } from "react";
import { useAppContext } from "@/context";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { CounselQueue } from "@/components/CounselQueue";
import { BudgetPanel } from "@/components/BudgetPanel";
import { BinderStatus } from "@/components/BinderStatus";
import { DeadlineManager } from "@/components/DeadlineManager";
import { TemplateViewer } from "@/components/TemplateViewer";
import { OutsideCounselPanel } from "@/components/OutsideCounselPanel";
import { LitigationPanel } from "@/components/LitigationPanel";
import { ComplaintParcelsValidatePanel } from "@/components/ComplaintParcelsValidatePanel";
import { TaskManager } from "@/components/TaskManager";
import { AIDecisionReview } from "@/components/AIDecisionReview";
import { CopilotPanel } from "@/components/CopilotPanel";
import { SettlementPredictor } from "@/components/SettlementPredictor";
import { AIAuditDrawer } from "@/components/AIAuditDrawer";

type CounselTab = "approvals" | "binder" | "litigation" | "tasks";

export function CounselPage() {
  const { projectId, parcelId } = useAppContext();
  useDocumentTitle("Counsel");
  const [showCopilot, setShowCopilot] = useState(false);
  const [showAudit, setShowAudit] = useState(false);
  const [tab, setTab] = useState<CounselTab>("approvals");

  const tabBtn = (id: CounselTab, label: string) => (
    <button
      type="button"
      key={id}
      onClick={() => setTab(id)}
      className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
        tab === id ? "bg-brand text-white shadow-sm" : "text-slate-600 hover:bg-slate-100"
      }`}
    >
      {label}
    </button>
  );

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
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowAudit(true)}
              className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:border-brand hover:text-brand"
              data-testid="open-ai-audit"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              AI Audit
            </button>
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
        </div>

        <div
          className="flex flex-wrap gap-2 rounded-lg border border-slate-200 bg-slate-50 p-1"
          role="tablist"
          aria-label="Counsel sections"
        >
          {tabBtn("approvals", "Approvals & templates")}
          {tabBtn("binder", "Binder & deadlines")}
          {tabBtn("litigation", "Litigation")}
          {tabBtn("tasks", "Tasks")}
        </div>

        {tab === "approvals" && (
          <>
            <div className="grid gap-4 md:grid-cols-2">
              <CounselQueue />
              <BudgetPanel projectId={projectId} />
            </div>
            <TemplateViewer />
            <div className="grid gap-4 lg:grid-cols-2">
              <AIDecisionReview />
              <SettlementPredictor
                parcelId={parcelId ?? undefined}
                jurisdiction="TX"
                assessedValue={350000}
              />
            </div>
            <OutsideCounselPanel projectId={projectId} parcelId={parcelId ?? undefined} />
          </>
        )}

        {tab === "binder" && (
          <div className="grid gap-4 lg:grid-cols-2">
            <BinderStatus projectId={projectId} parcelId={parcelId} />
            <DeadlineManager projectId={projectId} />
          </div>
        )}

        {tab === "litigation" && projectId && (
          <div className="space-y-6">
            <ComplaintParcelsValidatePanel projectId={projectId} />
            {parcelId ? <LitigationPanel parcelId={parcelId} projectId={projectId} /> : null}
          </div>
        )}

        {tab === "tasks" && <TaskManager projectId={projectId} parcelId={parcelId ?? undefined} />}
      </section>

      {/* Copilot Panel */}
      {showCopilot && (
        <div className="fixed right-0 top-0 h-screen w-96 shadow-xl z-50">
          <CopilotPanel
            caseId={projectId}
            parcelId={parcelId ?? undefined}
            jurisdiction="TX"
            isOpen={showCopilot}
            onClose={() => setShowCopilot(false)}
          />
        </div>
      )}

      {/* AI Audit drawer - surfaces signed provenance of AI decisions */}
      <AIAuditDrawer
        open={showAudit}
        onClose={() => setShowAudit(false)}
        resourceId={parcelId ?? projectId}
        title="AI decisions for this parcel"
      />
    </div>
  );
}
