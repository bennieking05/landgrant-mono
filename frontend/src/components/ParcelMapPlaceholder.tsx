export function ParcelMapPlaceholder() {
  return (
    <div className="rounded-xl border border-dashed border-brand bg-white/60 p-6">
      <p className="text-sm uppercase tracking-wide text-brand">ESRI basemap placeholder</p>
      <div className="mt-4 h-48 w-full rounded-lg bg-[radial-gradient(circle_at_center,_#cee1ff,_#f8fafc)]" />
      <p className="mt-3 text-sm text-slate-600">
        Final implementation renders feature layers via ArcGIS JS API, filtered by risk, deadline, and SLA.
      </p>
    </div>
  );
}



