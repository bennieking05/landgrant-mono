import { useState, lazy, Suspense } from "react";
import { useAppContext } from "@/context";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";

const ParcelMap = lazy(() => import("@/components/ParcelMap").then(m => ({ default: m.ParcelMap })));
import { CommsLog } from "@/components/CommsLog";
import { PacketChecklist } from "@/components/PacketChecklist";
import { RuleResults } from "@/components/RuleResults";
import { ParcelList } from "@/components/ParcelList";
import { TitlePanel } from "@/components/TitlePanel";
import { AppraisalPanel } from "@/components/AppraisalPanel";
import { ROEPanel } from "@/components/ROEPanel";
import { NegotiationPanel } from "@/components/NegotiationPanel";
import { TaskManager } from "@/components/TaskManager";
import { CopilotPanel } from "@/components/CopilotPanel";
import { ProjectHierarchyNav } from "@/components/ProjectHierarchyNav";
import { IntakeForm } from "@/components/IntakeForm";

type WorkbenchTab = "parcels" | "pipeline" | "tasks";

export function WorkbenchPage() {
  const { projectId, parcelId, setParcelId, parcels } = useAppContext();
  useDocumentTitle("Workbench", projectId || undefined);
  const [showCopilot, setShowCopilot] = useState(false);
  const [tab, setTab] = useState<WorkbenchTab>("parcels");

  const tabBtn = (id: WorkbenchTab, label: string) => (
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
            <p className="text-sm uppercase tracking-wide text-brand">Agent workbench</p>
            <h1 className="mt-2 text-3xl font-semibold">Parcel list, map filters, packet generation</h1>
            <p className="mt-2 max-w-3xl text-slate-600">
              Pulls backlog stories for map view, routing, comms log, pre-offer packet QA, and portal dispatch.
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

        <div
          className="flex flex-wrap gap-2 rounded-lg border border-slate-200 bg-slate-50 p-1"
          role="tablist"
          aria-label="Workbench sections"
        >
          {tabBtn("parcels", "Parcels & packet")}
          {tabBtn("pipeline", "Title · Appraisal · ROE · Offers")}
          {tabBtn("tasks", "Tasks")}
        </div>

        {projectId ? (
          <ProjectHierarchyNav
            projectId={projectId}
            selectedParcelId={parcelId}
            onSelectParcel={setParcelId}
          />
        ) : null}

        {!parcelId && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
            Select or create a parcel to view parcel-specific workbench tools.
          </div>
        )}

        {tab === "parcels" && (
          <>
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <h3 className="text-lg font-semibold">Staff intake</h3>
              <p className="mt-1 text-sm text-slate-600">
                Create or extend projects and parcels (moved from the landowner portal).
              </p>
              <div className="mt-4">
                <IntakeForm initialProjectId={projectId} />
              </div>
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              <Suspense
                fallback={
                  <div className="flex h-96 items-center justify-center rounded-xl bg-slate-100">
                    <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
                  </div>
                }
              >
                <ParcelMap
                  parcelData={parcels}
                  selectedParcelId={parcelId ?? undefined}
                  onParcelClick={setParcelId}
                  showFilters={true}
                />
              </Suspense>
              <ParcelList projectId={projectId} onSelectParcel={setParcelId} />
            </div>
            {parcelId && projectId && (
              <div className="grid gap-4 md:grid-cols-3">
                <CommsLog projectId={projectId} parcelId={parcelId} />
                <PacketChecklist parcelId={parcelId} />
                <RuleResults parcelId={parcelId} />
              </div>
            )}
          </>
        )}

        {tab === "pipeline" && parcelId && (
          <>
            <div className="grid gap-4 lg:grid-cols-3">
              <TitlePanel parcelId={parcelId} />
              <AppraisalPanel parcelId={parcelId} />
              <ROEPanel parcelId={parcelId} projectId={projectId} />
            </div>
            <NegotiationPanel parcelId={parcelId} projectId={projectId} />
          </>
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
    </div>
  );
}
