import { useState, lazy, Suspense } from "react";
import { Sparkles, MapPin } from "lucide-react";
import { useAppContext } from "@/context";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { EmptyState, Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui";
import { ActiveParcelBar } from "@/components/ActiveParcelBar";

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
import { CopilotDrawer } from "@/components/CopilotDrawer";
import { ProjectHierarchyNav } from "@/components/ProjectHierarchyNav";
import { IntakeForm } from "@/components/IntakeForm";

type WorkbenchTab = "parcels" | "pipeline" | "tasks";

export function WorkbenchPage() {
  const { projectId, parcelId, setParcelId, parcels } = useAppContext();
  useDocumentTitle("Workbench", projectId || undefined);
  const [showCopilot, setShowCopilot] = useState(false);
  const [tab, setTab] = useState<WorkbenchTab>("parcels");

  return (
    <div className="flex h-full">
      {/* Main content */}
      <section className={`flex-1 space-y-6 transition-all ${showCopilot ? "md:mr-96" : ""}`}>
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm uppercase tracking-wide text-brand">Agent workbench</p>
            <h1 className="mt-2 text-3xl font-semibold">Workbench</h1>
            <p className="mt-2 max-w-3xl text-slate-600">
              Review parcels on the map, manage the pre-offer packet, run jurisdiction rules, and
              advance each parcel through title, appraisal, ROE, and offers.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setShowCopilot(!showCopilot)}
            aria-pressed={showCopilot}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
              showCopilot
                ? "bg-brand text-white border-brand"
                : "bg-white text-slate-700 border-slate-200 hover:border-brand hover:text-brand"
            }`}
          >
            <Sparkles className="h-5 w-5" aria-hidden />
            <span className="text-sm font-medium">AI Copilot</span>
          </button>
        </div>

        <Tabs
          value={tab}
          onValueChange={(v) => setTab(v as WorkbenchTab)}
          className="space-y-6"
        >
          <TabsList aria-label="Workbench sections">
            <TabsTrigger value="parcels">Parcels &amp; packet</TabsTrigger>
            <TabsTrigger value="pipeline">Title · Appraisal · ROE · Offers</TabsTrigger>
            <TabsTrigger value="tasks">Tasks</TabsTrigger>
          </TabsList>

          {projectId ? (
            <ProjectHierarchyNav
              projectId={projectId}
              selectedParcelId={parcelId}
              onSelectParcel={setParcelId}
            />
          ) : null}

          <ActiveParcelBar
            emptyHint={
              tab === "tasks"
                ? "Showing tasks for the whole project. Select a parcel to focus on its tasks."
                : undefined
            }
          />

          <TabsContent value="parcels" className="space-y-6">
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
          </TabsContent>

          <TabsContent value="pipeline" className="space-y-6">
            {parcelId ? (
              <>
                <div className="grid gap-4 lg:grid-cols-3">
                  <TitlePanel parcelId={parcelId} />
                  <AppraisalPanel parcelId={parcelId} />
                  <ROEPanel parcelId={parcelId} projectId={projectId} />
                </div>
                <NegotiationPanel parcelId={parcelId} projectId={projectId} />
              </>
            ) : (
              <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <EmptyState
                  icon={MapPin}
                  title="No parcel selected"
                  message="Select a parcel from the Parcels &amp; packet tab to view its title, appraisal, ROE, and offers."
                />
              </div>
            )}
          </TabsContent>

          <TabsContent value="tasks">
            <TaskManager projectId={projectId} parcelId={parcelId ?? undefined} />
          </TabsContent>
        </Tabs>
      </section>

      <CopilotDrawer
        open={showCopilot}
        onClose={() => setShowCopilot(false)}
        caseId={projectId}
        parcelId={parcelId ?? undefined}
        jurisdiction="TX"
      />
    </div>
  );
}
