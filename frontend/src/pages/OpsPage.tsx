import { useAppContext } from "@/context";
import { RoutePlanPanel } from "@/components/RoutePlanPanel";
import { NotificationsPanel } from "@/components/NotificationsPanel";

export function OpsPage() {
  const { projectId, parcelId } = useAppContext();
  const effectiveParcelId = parcelId ?? "PARCEL-001";

  return (
    <section className="space-y-6">
      <div>
        <p className="text-sm uppercase tracking-wide text-brand">Operations</p>
        <h1 className="mt-2 text-3xl font-semibold">Route Planning & Communications</h1>
        <p className="mt-2 max-w-3xl text-slate-600">
          Field operations support: optimized visit routes, batch notifications, and integration diagnostics.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <RoutePlanPanel projectId={projectId} />
        <NotificationsPanel projectId={projectId} parcelId={effectiveParcelId} />
      </div>

      {/* Integration Status */}
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-lg font-semibold mb-4">Integration Status</h3>
        <div className="grid gap-4 md:grid-cols-3">
          <div className="p-4 bg-slate-50 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <span className="w-2 h-2 bg-emerald-500 rounded-full"></span>
              <span className="text-sm font-medium text-slate-900">Email (SendGrid)</span>
            </div>
            <p className="text-xs text-slate-500">Outbound notifications active</p>
          </div>
          <div className="p-4 bg-slate-50 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <span className="w-2 h-2 bg-emerald-500 rounded-full"></span>
              <span className="text-sm font-medium text-slate-900">Docket Webhooks</span>
            </div>
            <p className="text-xs text-slate-500">POST /integrations/dockets</p>
          </div>
          <div className="p-4 bg-slate-50 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <span className="w-2 h-2 bg-amber-500 rounded-full"></span>
              <span className="text-sm font-medium text-slate-900">GIS/PostGIS</span>
            </div>
            <p className="text-xs text-slate-500">Parcel geometry storage ready</p>
          </div>
        </div>
      </div>
    </section>
  );
}
