import { useAppContext } from "@/context";
import { InviteCard } from "@/components/InviteCard";
import { ParcelMap } from "@/components/ParcelMap";
import { UploadPanel } from "@/components/UploadPanel";
import { DecisionActions } from "@/components/DecisionActions";
import { IntakeForm } from "@/components/IntakeForm";
import { AIDraftPanel } from "@/components/AIDraftPanel";

export function IntakePage() {
  const { projectId, parcelId } = useAppContext();
  const effectiveParcelId = parcelId ?? "PARCEL-001";

  return (
    <section className="space-y-6">
      <div>
        <p className="text-sm uppercase tracking-wide text-brand">Landowner portal</p>
        <h1 className="mt-2 text-3xl font-semibold">Invite → review → e-sign</h1>
        <p className="mt-2 max-w-3xl text-slate-600">
          Mirrors the swimlane: secure invite, parcel overview, doc review, uploads, chat, and Accept / Counter / Request
          Call actions.
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <InviteCard projectId={projectId} parcelId={effectiveParcelId} />
        <ParcelMap 
          selectedParcelId={effectiveParcelId}
          showFilters={false}
        />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <UploadPanel parcelId={effectiveParcelId} />
        <DecisionActions parcelId={effectiveParcelId} />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <IntakeForm initialProjectId={projectId} />
        <AIDraftPanel jurisdiction="TX" parcelId={effectiveParcelId} />
      </div>
    </section>
  );
}
