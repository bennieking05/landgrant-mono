import { useState } from "react";
import { useAppContext } from "@/context";
import { ParcelMap } from "@/components/ParcelMap";
import { CommsLog } from "@/components/CommsLog";
import { PacketChecklist } from "@/components/PacketChecklist";
import { RuleResults } from "@/components/RuleResults";
import { ParcelList } from "@/components/ParcelList";
import { TitlePanel } from "@/components/TitlePanel";
import { AppraisalPanel } from "@/components/AppraisalPanel";
import { CopilotPanel } from "@/components/CopilotPanel";

export function WorkbenchPage() {
  const { projectId, parcelId, setParcelId } = useAppContext();
  const effectiveParcelId = parcelId ?? "PARCEL-001";
  const [showCopilot, setShowCopilot] = useState(false);

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

        {/* Map and Parcel List side by side */}
        <div className="grid gap-4 lg:grid-cols-2">
          <ParcelMap 
            selectedParcelId={effectiveParcelId}
            onParcelClick={setParcelId}
            showFilters={true}
          />
          <ParcelList projectId={projectId} onSelectParcel={setParcelId} />
        </div>

        {/* Original workbench components */}
        <div className="grid gap-4 md:grid-cols-3">
          <CommsLog parcelId={effectiveParcelId} />
          <PacketChecklist parcelId={effectiveParcelId} />
          <RuleResults parcelId={effectiveParcelId} />
        </div>

        {/* Title and Appraisal panels */}
        <div className="grid gap-4 lg:grid-cols-2">
          <TitlePanel parcelId={effectiveParcelId} />
          <AppraisalPanel parcelId={effectiveParcelId} />
        </div>
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
