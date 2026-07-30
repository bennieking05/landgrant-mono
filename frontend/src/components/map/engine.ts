import type { ParcelItem } from "@/lib/api";
import { STAGE_COLORS } from "@/components/ui";

/**
 * Map render-engine adapter (UX-7).
 *
 * The product currently renders with Mapbox GL, but enterprise GIS teams often
 * standardize on ESRI/ArcGIS. Everything map-related goes through this seam so a
 * second engine can be added later without touching feature code: callers depend
 * on `MapEngineConfig` + the GeoJSON we build here, not on a specific SDK.
 */
export type MapEngineId = "mapbox" | "esri";

export type MapEngineConfig = {
  id: MapEngineId;
  /** Access token / API key for the active engine, if any. */
  token: string | null;
  /** True when the engine has what it needs to render. */
  available: boolean;
  label: string;
};

function resolveToken(): string | null {
  const fromEnv = import.meta.env.VITE_MAPBOX_TOKEN;
  if (fromEnv) return fromEnv;
  if (typeof window !== "undefined") {
    const w = window as unknown as { MAPBOX_TOKEN?: string };
    if (w.MAPBOX_TOKEN) return w.MAPBOX_TOKEN;
  }
  return null;
}

/** Resolve the active map engine config. ESRI is reserved for a future adapter. */
export function getMapEngine(): MapEngineConfig {
  const requested = (import.meta.env.VITE_MAP_ENGINE as MapEngineId) ?? "mapbox";
  if (requested === "esri") {
    // No ESRI adapter yet; report unavailable rather than guessing.
    return { id: "esri", token: null, available: false, label: "ESRI / ArcGIS" };
  }
  const token = resolveToken();
  return { id: "mapbox", token, available: Boolean(token), label: "Mapbox GL" };
}

export type ParcelGeometry = {
  type: "Polygon" | "MultiPolygon" | "Point";
  coordinates: unknown;
};

export type ParcelFeatureProps = {
  parcel_id: string;
  stage: string;
  risk_score: number;
  owner?: string | null;
  county_fips?: string | null;
  next_deadline_at?: string | null;
};

/** Rough centroid of a polygon/multipolygon ring for point/cluster overlays. */
function centroidOf(geom: ParcelGeometry): [number, number] | null {
  try {
    if (geom.type === "Point") {
      const c = geom.coordinates as [number, number];
      return [c[0], c[1]];
    }
    const ring =
      geom.type === "Polygon"
        ? (geom.coordinates as number[][][])[0]
        : (geom.coordinates as number[][][][])[0][0];
    if (!ring || ring.length === 0) return null;
    let x = 0;
    let y = 0;
    for (const [lng, lat] of ring) {
      x += lng;
      y += lat;
    }
    return [x / ring.length, y / ring.length];
  } catch {
    return null;
  }
}

export type BuiltGeo = {
  polygons: GeoJSON.FeatureCollection;
  points: GeoJSON.FeatureCollection;
  mappedCount: number;
};

/** Build polygon + centroid-point FeatureCollections from parcel rows that carry geometry. */
export function buildParcelGeo(parcels: ParcelItem[]): BuiltGeo {
  const polygons: GeoJSON.Feature[] = [];
  const points: GeoJSON.Feature[] = [];
  for (const p of parcels) {
    const geom = p.geom as ParcelGeometry | null | undefined;
    if (!geom || !geom.type || !geom.coordinates) continue;
    const props: ParcelFeatureProps = {
      parcel_id: p.id,
      stage: p.stage,
      risk_score: p.risk_score,
      owner: p.owner ?? null,
      county_fips: p.county_fips ?? null,
      next_deadline_at: p.next_deadline_at ?? null,
    };
    if (geom.type === "Polygon" || geom.type === "MultiPolygon") {
      polygons.push({
        type: "Feature",
        id: p.id,
        properties: props,
        geometry: geom as unknown as GeoJSON.Geometry,
      });
    }
    const c = centroidOf(geom);
    if (c) {
      points.push({
        type: "Feature",
        id: p.id,
        properties: props,
        geometry: { type: "Point", coordinates: c },
      });
    }
  }
  return {
    polygons: { type: "FeatureCollection", features: polygons },
    points: { type: "FeatureCollection", features: points },
    mappedCount: points.length,
  };
}

/** Mapbox "match" expression coloring a layer by parcel stage (UX-7 stage layers). */
export function stageColorExpression(): unknown[] {
  const expr: unknown[] = ["match", ["get", "stage"]];
  for (const [stage, color] of Object.entries(STAGE_COLORS)) {
    expr.push(stage, color);
  }
  expr.push("#94a3b8"); // default slate
  return expr;
}
