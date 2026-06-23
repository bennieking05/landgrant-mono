import { useState } from "react";
import { Sparkles, ScrollText } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useAppContext } from "@/context";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui";
import { ActiveParcelBar } from "@/components/ActiveParcelBar";
import { CopilotDrawer } from "@/components/CopilotDrawer";
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
import { SettlementPredictor } from "@/components/SettlementPredictor";
import { AIAuditDrawer } from "@/components/AIAuditDrawer";

type CounselTab = "approvals" | "binder" | "litigation" | "tasks";

export function CounselPage() {
  const { t } = useTranslation();
  const { projectId, parcelId } = useAppContext();
  useDocumentTitle("Counsel");
  const [showCopilot, setShowCopilot] = useState(false);
  const [showAudit, setShowAudit] = useState(false);
  const [tab, setTab] = useState<CounselTab>("approvals");

  return (
    <div className="flex h-full">
      {/* Main content */}
      <section className={`flex-1 space-y-6 transition-all ${showCopilot ? "md:mr-96" : ""}`}>
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm uppercase tracking-wide text-brand">{t("pages.counsel.eyebrow")}</p>
            <h1 className="mt-2 text-3xl font-semibold">{t("pages.counsel.title")}</h1>
            <p className="mt-2 max-w-3xl text-slate-600">{t("pages.counsel.subtitle")}</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowAudit(true)}
              className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:border-brand hover:text-brand"
              data-testid="open-ai-audit"
            >
              <ScrollText className="h-5 w-5" aria-hidden />
              AI Audit
            </button>
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
        </div>

        <Tabs
          value={tab}
          onValueChange={(v) => setTab(v as CounselTab)}
          className="space-y-6"
        >
          <TabsList aria-label="Counsel sections">
            <TabsTrigger value="approvals">Approvals &amp; templates</TabsTrigger>
            <TabsTrigger value="binder">Binder &amp; deadlines</TabsTrigger>
            <TabsTrigger value="litigation">Litigation</TabsTrigger>
            <TabsTrigger value="tasks">Tasks</TabsTrigger>
          </TabsList>

          <TabsContent value="approvals" className="space-y-6">
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
          </TabsContent>

          <TabsContent value="binder">
            <div className="grid gap-4 lg:grid-cols-2">
              <BinderStatus projectId={projectId} parcelId={parcelId} />
              <DeadlineManager projectId={projectId} />
            </div>
          </TabsContent>

          <TabsContent value="litigation" className="space-y-6">
            <ActiveParcelBar emptyHint={t("common.litigationParcelHint")} />
            {projectId ? (
              <ComplaintParcelsValidatePanel projectId={projectId} />
            ) : null}
            {parcelId && projectId ? (
              <LitigationPanel parcelId={parcelId} projectId={projectId} />
            ) : null}
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
