import { Link } from "react-router-dom";
import { MapPin } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useAppContext } from "@/context";
import { StageBadge, RiskBadge } from "@/components/ui";

/**
 * Staff workbench/counsel pages operate on a single "active" parcel that the
 * app auto-selects (first in the project) or the user picks from the list/map.
 * That selection was previously invisible — panels silently scoped to an
 * unlabeled parcel. This bar makes the active context explicit (id + stage +
 * risk + owner/county) and links to the full parcel record, or guides the user
 * to pick one when none is selected.
 */
export function ActiveParcelBar({ emptyHint }: { emptyHint?: string }) {
  const { t } = useTranslation();
  const { parcelId, parcels } = useAppContext();

  if (!parcelId) {
    return (
      <div className="flex items-start gap-2 rounded-card border border-amber-200 bg-amber-50 p-4 text-small text-amber-800">
        <MapPin className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
        <span>{emptyHint ?? t("common.selectParcelHint")}</span>
      </div>
    );
  }

  const parcel = parcels.find((p) => p.id === parcelId);

  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-card border border-slate-200 bg-white px-4 py-2.5 shadow-card">
      <span className="flex items-center gap-1.5 text-caption font-semibold uppercase tracking-wide text-slate-500">
        <MapPin className="h-4 w-4 text-brand" aria-hidden /> {t("common.activeParcel")}
      </span>
      <span className="font-semibold text-slate-900">{parcelId}</span>
      {parcel?.stage ? <StageBadge stage={parcel.stage} /> : null}
      {typeof parcel?.risk_score === "number" ? <RiskBadge score={parcel.risk_score} /> : null}
      {parcel?.owner ? <span className="text-small text-slate-600">{parcel.owner}</span> : null}
      {parcel?.county || parcel?.county_fips ? (
        <span className="text-small text-slate-500">
          {parcel.county ?? `FIPS ${parcel.county_fips}`}
        </span>
      ) : null}
      <Link
        to={`/parcels/${parcelId}`}
        className="ml-auto text-small font-medium text-brand hover:underline"
      >
        {t("common.viewFullDetail")} &rarr;
      </Link>
    </div>
  );
}
