import { useEffect, useMemo, useRef, useState } from "react";
import { Map as MapIcon, Layers } from "lucide-react";
import type { ParcelItem } from "@/lib/api";
import { StageBadge, STAGE_ORDER, STAGE_COLORS, stageLabel } from "@/components/ui";
import { formatDate } from "@/lib/format";
import {
  getMapEngine,
  buildParcelGeo,
  stageColorExpression,
} from "@/components/map/engine";

type MapboxGL = typeof import("mapbox-gl");
type MapboxMap = import("mapbox-gl").Map;
type GeoJSONSourceSpecification = import("mapbox-gl").GeoJSONSourceSpecification;

type Props = {
  /** Parcel rows; those carrying geometry are rendered. */
  parcelData?: ParcelItem[];
  center?: [number, number];
  zoom?: number;
  onParcelClick?: (parcelId: string) => void;
  selectedParcelId?: string;
  showFilters?: boolean;
  className?: string;
};

// Texas is the common jurisdiction for these projects.
const DEFAULT_CENTER: [number, number] = [-97.7431, 30.2672];
const DEFAULT_ZOOM = 9;

export function ParcelMap({
  parcelData,
  center = DEFAULT_CENTER,
  zoom = DEFAULT_ZOOM,
  onParcelClick,
  selectedParcelId,
  showFilters = true,
  className = "",
}: Props) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapboxMap | null>(null);
  const popupRef = useRef<import("mapbox-gl").Popup | null>(null);
  const onClickRef = useRef(onParcelClick);
  onClickRef.current = onParcelClick;

  const engine = useMemo(() => getMapEngine(), []);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stageFilter, setStageFilter] = useState<string[]>([]);

  const geo = useMemo(() => buildParcelGeo(parcelData ?? []), [parcelData]);

  const stagesPresent = useMemo(() => {
    const set = new Set<string>();
    for (const f of geo.points.features) {
      const s = (f.properties as { stage?: string })?.stage;
      if (s) set.add(s);
    }
    return STAGE_ORDER.filter((s) => set.has(s));
  }, [geo]);

  // Initialize the map once (engine available only).
  useEffect(() => {
    if (!mapContainer.current || !engine.available || !engine.token) return;
    let map: MapboxMap | null = null;

    (async () => {
      try {
        const mapboxgl: MapboxGL = await import("mapbox-gl");
        await import("mapbox-gl/dist/mapbox-gl.css");
        // @ts-expect-error mapbox-gl typings
        mapboxgl.accessToken = engine.token;

        map = new mapboxgl.Map({
          container: mapContainer.current!,
          style: "mapbox://styles/mapbox/light-v11",
          center,
          zoom,
          attributionControl: true,
        });
        map.addControl(new mapboxgl.NavigationControl(), "top-right");
        map.addControl(new mapboxgl.ScaleControl(), "bottom-left");

        map.on("load", () => {
          mapRef.current = map;
          setMapLoaded(true);

          map!.addSource("parcels", {
            type: "geojson",
            data: { type: "FeatureCollection", features: [] },
            promoteId: "parcel_id",
          } as GeoJSONSourceSpecification);

          map!.addSource("parcel-points", {
            type: "geojson",
            data: { type: "FeatureCollection", features: [] },
            cluster: true,
            clusterRadius: 50,
            clusterMaxZoom: 12,
          } as GeoJSONSourceSpecification);

          // Polygon fill colored by stage.
          map!.addLayer({
            id: "parcels-fill",
            type: "fill",
            source: "parcels",
            paint: {
              "fill-color": stageColorExpression() as never,
              "fill-opacity": [
                "case",
                ["boolean", ["feature-state", "selected"], false],
                0.75,
                0.4,
              ],
            },
          });
          map!.addLayer({
            id: "parcels-outline",
            type: "line",
            source: "parcels",
            paint: {
              "line-color": [
                "case",
                ["boolean", ["feature-state", "selected"], false],
                "#14294A",
                "#475569",
              ],
              "line-width": [
                "case",
                ["boolean", ["feature-state", "selected"], false],
                3,
                1,
              ],
            },
          });

          // Clustered point overview.
          map!.addLayer({
            id: "clusters",
            type: "circle",
            source: "parcel-points",
            filter: ["has", "point_count"],
            paint: {
              "circle-color": "#1F4B99",
              "circle-opacity": 0.85,
              "circle-radius": ["step", ["get", "point_count"], 16, 25, 22, 100, 30],
            },
          });
          map!.addLayer({
            id: "cluster-count",
            type: "symbol",
            source: "parcel-points",
            filter: ["has", "point_count"],
            layout: {
              "text-field": ["get", "point_count_abbreviated"],
              "text-size": 12,
            },
            paint: { "text-color": "#ffffff" },
          });
          map!.addLayer({
            id: "unclustered-point",
            type: "circle",
            source: "parcel-points",
            filter: ["!", ["has", "point_count"]],
            paint: {
              "circle-color": stageColorExpression() as never,
              "circle-radius": 6,
              "circle-stroke-width": 1.5,
              "circle-stroke-color": "#ffffff",
            },
          });

          const showPopup = (e: import("mapbox-gl").MapLayerMouseEvent) => {
            const f = e.features?.[0];
            if (!f) return;
            const props = f.properties as {
              parcel_id: string;
              stage: string;
              risk_score: number;
              owner?: string;
              county_fips?: string;
              next_deadline_at?: string;
            };
            onClickRef.current?.(props.parcel_id);
            popupRef.current?.remove();
            const stageColor = STAGE_COLORS[props.stage] ?? "#64748b";
            const stagePill =
              `<span style="display:inline-flex;align-items:center;gap:4px;border:1px solid ${stageColor}33;` +
              `background:${stageColor}1a;color:${stageColor};font-size:11px;font-weight:500;padding:1px 8px;border-radius:9999px">` +
              `<span style="width:6px;height:6px;border-radius:9999px;background:${stageColor};opacity:0.7"></span>` +
              `${stageLabel(props.stage)}</span>`;
            const risk =
              props.risk_score >= 70
                ? { label: "High", color: "#B42318" }
                : props.risk_score >= 40
                  ? { label: "Medium", color: "#B45309" }
                  : { label: "Low", color: "#15803D" };
            const riskPill =
              `<span style="display:inline-flex;align-items:center;gap:4px;border:1px solid ${risk.color}33;` +
              `background:${risk.color}1a;color:${risk.color};font-size:11px;font-weight:600;padding:1px 8px;border-radius:9999px">` +
              `${props.risk_score} &middot; ${risk.label}</span>`;
            const nextDeadline = props.next_deadline_at
              ? `<div style="color:#475569;font-size:12px;margin-top:4px">Next deadline: ${formatDate(props.next_deadline_at)}</div>`
              : "";
            popupRef.current = new mapboxgl.Popup({ closeButton: true, offset: 12 })
              .setLngLat(e.lngLat)
              .setHTML(
                `<div style="font-family:Inter,sans-serif;min-width:180px">
                   <div style="font-weight:600;font-family:'IBM Plex Mono',monospace">${props.parcel_id}</div>
                   <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:6px">${stagePill}${riskPill}</div>
                   ${props.owner ? `<div style="color:#475569;font-size:12px;margin-top:4px">${props.owner}</div>` : ""}
                   ${nextDeadline}
                   <a href="/parcels/${encodeURIComponent(props.parcel_id)}" style="display:inline-block;margin-top:8px;color:#1F4B99;font-size:12px;font-weight:600">Open detail</a>
                 </div>`,
              )
              .addTo(map!);
          };

          map!.on("click", "parcels-fill", showPopup);
          map!.on("click", "unclustered-point", showPopup);
          for (const layer of ["parcels-fill", "unclustered-point", "clusters"]) {
            map!.on("mouseenter", layer, () => {
              if (map) map.getCanvas().style.cursor = "pointer";
            });
            map!.on("mouseleave", layer, () => {
              if (map) map.getCanvas().style.cursor = "";
            });
          }
        });

        map.on("error", () => setError("The map failed to load."));
      } catch {
        setError("The map could not be initialized.");
      }
    })();

    return () => {
      popupRef.current?.remove();
      mapRef.current?.remove();
      mapRef.current = null;
      setMapLoaded(false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- init once; data/selection handled in separate effects
  }, [engine.available, engine.token]);

  // Push data (with stage filter) into sources.
  useEffect(() => {
    if (!mapLoaded || !mapRef.current) return;
    const applyFilter = (fc: GeoJSON.FeatureCollection): GeoJSON.FeatureCollection =>
      stageFilter.length === 0
        ? fc
        : {
            type: "FeatureCollection",
            features: fc.features.filter((f) =>
              stageFilter.includes((f.properties as { stage?: string })?.stage ?? ""),
            ),
          };
    (mapRef.current.getSource("parcels") as import("mapbox-gl").GeoJSONSource | undefined)?.setData(
      applyFilter(geo.polygons),
    );
    (mapRef.current.getSource("parcel-points") as import("mapbox-gl").GeoJSONSource | undefined)?.setData(
      applyFilter(geo.points),
    );
  }, [mapLoaded, geo, stageFilter]);

  // Two-way selection highlight.
  useEffect(() => {
    if (!mapLoaded || !mapRef.current) return;
    const map = mapRef.current;
    for (const f of geo.polygons.features) {
      if (f.id !== undefined) map.setFeatureState({ source: "parcels", id: f.id }, { selected: false });
    }
    if (selectedParcelId) {
      map.setFeatureState({ source: "parcels", id: selectedParcelId }, { selected: true });
    }
  }, [mapLoaded, selectedParcelId, geo]);

  function toggleStage(s: string) {
    setStageFilter((prev) => (prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]));
  }

  // Designed fallback (UX-7): never expose an env-var instruction to users.
  if (!engine.available) {
    return (
      <div className={`overflow-hidden rounded-card border border-slate-200 bg-white shadow-card ${className}`}>
        <div className="flex h-96 flex-col items-center justify-center gap-3 bg-slate-50 px-6 text-center">
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-brand/10 text-brand">
            <MapIcon className="h-6 w-6" />
          </span>
          <div>
            <p className="text-h3 text-slate-900">Map view unavailable</p>
            <p className="mt-1 max-w-sm text-small text-slate-500">
              Interactive parcel mapping isn&apos;t enabled for this environment. Parcel data
              remains fully available in the grid and detail views.
            </p>
          </div>
          {import.meta.env.DEV ? (
            <p className="text-caption text-slate-600">
              Dev note: configure the {engine.label} access token to enable the map.
            </p>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <div className={`overflow-hidden rounded-card border border-slate-200 bg-white shadow-card ${className}`}>
      {showFilters && stagesPresent.length > 0 ? (
        <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 bg-slate-50 px-4 py-2">
          <span className="flex items-center gap-1 text-caption font-medium text-slate-500">
            <Layers className="h-3.5 w-3.5" /> Stage
          </span>
          {stagesPresent.map((s) => {
            const active = stageFilter.length === 0 || stageFilter.includes(s);
            return (
              <button
                key={s}
                type="button"
                onClick={() => toggleStage(s)}
                className={active ? "" : "opacity-40"}
                aria-pressed={stageFilter.includes(s)}
                title={`Toggle ${stageLabel(s)}`}
              >
                <StageBadge stage={s} />
              </button>
            );
          })}
          {stageFilter.length > 0 ? (
            <button
              type="button"
              onClick={() => setStageFilter([])}
              className="text-caption text-slate-500 underline hover:text-slate-900"
            >
              Clear
            </button>
          ) : null}
        </div>
      ) : null}

      <div ref={mapContainer} className="relative h-96 w-full">
        {!mapLoaded && !error ? (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-100">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
          </div>
        ) : null}
        {error ? (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-50 px-6 text-center text-small text-slate-500">
            {error}
          </div>
        ) : null}
        {mapLoaded && geo.mappedCount === 0 ? (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-slate-50/80 px-6 text-center">
            <div>
              <p className="text-h3 text-slate-700">No mapped parcels</p>
              <p className="mt-1 text-small text-slate-500">
                Parcels in this project don&apos;t have boundary geometry yet.
              </p>
            </div>
          </div>
        ) : null}
      </div>

      <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50 px-4 py-2">
        <span className="text-caption text-slate-500">{engine.label}</span>
        <span className="text-caption text-slate-500">
          {geo.mappedCount} mapped parcel{geo.mappedCount === 1 ? "" : "s"}
        </span>
      </div>
    </div>
  );
}

export { ParcelMap as ParcelMapPlaceholder };
