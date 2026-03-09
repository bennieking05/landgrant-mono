"use client";

import { useEffect, useRef, useState, useCallback } from "react";

// Mapbox types - imported dynamically
type MapboxGL = typeof import("mapbox-gl");
type MapboxMap = import("mapbox-gl").Map;
type GeoJSONSourceSpecification = import("mapbox-gl").GeoJSONSourceSpecification;

type ParcelFeature = {
  type: "Feature";
  id?: string | number;
  properties: {
    parcel_id: string;
    name?: string;
    status?: string;
    risk_level?: "low" | "medium" | "high" | "critical";
    sla_status?: "on_track" | "at_risk" | "overdue";
    deadline?: string;
    acreage?: number;
    owner_name?: string;
  };
  geometry: {
    type: "Polygon" | "MultiPolygon";
    coordinates: number[][][] | number[][][][];
  };
};

type ParcelGeoJSON = {
  type: "FeatureCollection";
  features: ParcelFeature[];
};

type FilterState = {
  riskLevels: string[];
  slaStatuses: string[];
  showOverdueOnly: boolean;
};

type Props = {
  parcels?: ParcelGeoJSON;
  center?: [number, number]; // [lng, lat]
  zoom?: number;
  onParcelClick?: (parcelId: string) => void;
  selectedParcelId?: string;
  showFilters?: boolean;
  className?: string;
};

const RISK_COLORS = {
  low: "#22c55e",      // green
  medium: "#eab308",   // yellow
  high: "#f97316",     // orange
  critical: "#ef4444", // red
};

const SLA_COLORS = {
  on_track: "#3b82f6",  // blue
  at_risk: "#eab308",   // yellow
  overdue: "#ef4444",   // red
};

// Default center (Texas - common for eminent domain projects)
const DEFAULT_CENTER: [number, number] = [-97.7431, 30.2672]; // Austin, TX
const DEFAULT_ZOOM = 10;

export function ParcelMap({
  parcels,
  center = DEFAULT_CENTER,
  zoom = DEFAULT_ZOOM,
  onParcelClick,
  selectedParcelId,
  showFilters = true,
  className = "",
}: Props) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapboxMap | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [mapboxToken, setMapboxToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterState>({
    riskLevels: [],
    slaStatuses: [],
    showOverdueOnly: false,
  });

  // Check for Mapbox token on mount
  useEffect(() => {
    const token = import.meta.env.VITE_MAPBOX_TOKEN || 
                  (typeof window !== "undefined" && (window as unknown as { MAPBOX_TOKEN?: string }).MAPBOX_TOKEN);
    if (token) {
      setMapboxToken(token);
    }
  }, []);

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current || !mapboxToken) return;

    let map: MapboxMap | null = null;
    let mapboxgl: MapboxGL | null = null;

    async function initMap() {
      try {
        // Dynamic import of mapbox-gl
        mapboxgl = await import("mapbox-gl");
        
        // Import CSS
        await import("mapbox-gl/dist/mapbox-gl.css");

        mapboxgl.accessToken = mapboxToken!;

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

          // Add empty source for parcels
          map!.addSource("parcels", {
            type: "geojson",
            data: { type: "FeatureCollection", features: [] },
          } as GeoJSONSourceSpecification);

          // Fill layer for parcel polygons
          map!.addLayer({
            id: "parcels-fill",
            type: "fill",
            source: "parcels",
            paint: {
              "fill-color": [
                "match",
                ["get", "risk_level"],
                "low", RISK_COLORS.low,
                "medium", RISK_COLORS.medium,
                "high", RISK_COLORS.high,
                "critical", RISK_COLORS.critical,
                "#94a3b8" // default slate
              ],
              "fill-opacity": [
                "case",
                ["boolean", ["feature-state", "selected"], false],
                0.8,
                0.4
              ],
            },
          });

          // Outline layer
          map!.addLayer({
            id: "parcels-outline",
            type: "line",
            source: "parcels",
            paint: {
              "line-color": [
                "case",
                ["boolean", ["feature-state", "selected"], false],
                "#1e3a5f", // dark blue when selected
                "#475569"  // slate
              ],
              "line-width": [
                "case",
                ["boolean", ["feature-state", "selected"], false],
                3,
                1.5
              ],
            },
          });

          // Labels layer
          map!.addLayer({
            id: "parcels-labels",
            type: "symbol",
            source: "parcels",
            layout: {
              "text-field": ["get", "parcel_id"],
              "text-size": 11,
              "text-anchor": "center",
            },
            paint: {
              "text-color": "#1e293b",
              "text-halo-color": "#ffffff",
              "text-halo-width": 1.5,
            },
          });

          // Click handler
          map!.on("click", "parcels-fill", (e) => {
            if (e.features && e.features.length > 0) {
              const parcelId = e.features[0].properties?.parcel_id;
              if (parcelId && onParcelClick) {
                onParcelClick(parcelId);
              }
            }
          });

          // Hover cursor
          map!.on("mouseenter", "parcels-fill", () => {
            if (map) map.getCanvas().style.cursor = "pointer";
          });
          map!.on("mouseleave", "parcels-fill", () => {
            if (map) map.getCanvas().style.cursor = "";
          });
        });

        map.on("error", (e) => {
          console.error("Mapbox error:", e);
          setError("Map failed to load");
        });
      } catch (err) {
        console.error("Failed to initialize map:", err);
        setError("Failed to load map library");
      }
    }

    initMap();

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, [mapboxToken, center, zoom, onParcelClick]);

  // Update parcels data
  useEffect(() => {
    if (!mapLoaded || !mapRef.current || !parcels) return;

    const source = mapRef.current.getSource("parcels") as import("mapbox-gl").GeoJSONSource;
    if (!source) return;

    // Apply filters
    let filteredFeatures = parcels.features;

    if (filters.riskLevels.length > 0) {
      filteredFeatures = filteredFeatures.filter((f) =>
        f.properties.risk_level && filters.riskLevels.includes(f.properties.risk_level)
      );
    }

    if (filters.slaStatuses.length > 0) {
      filteredFeatures = filteredFeatures.filter((f) =>
        f.properties.sla_status && filters.slaStatuses.includes(f.properties.sla_status)
      );
    }

    if (filters.showOverdueOnly) {
      filteredFeatures = filteredFeatures.filter((f) =>
        f.properties.sla_status === "overdue"
      );
    }

    source.setData({
      type: "FeatureCollection",
      features: filteredFeatures,
    });
  }, [mapLoaded, parcels, filters]);

  // Handle selected parcel highlighting
  useEffect(() => {
    if (!mapLoaded || !mapRef.current || !parcels) return;

    // Clear previous selections
    parcels.features.forEach((f) => {
      if (f.id !== undefined) {
        mapRef.current!.setFeatureState(
          { source: "parcels", id: f.id },
          { selected: false }
        );
      }
    });

    // Set new selection
    if (selectedParcelId) {
      const selectedFeature = parcels.features.find(
        (f) => f.properties.parcel_id === selectedParcelId
      );
      if (selectedFeature?.id !== undefined) {
        mapRef.current.setFeatureState(
          { source: "parcels", id: selectedFeature.id },
          { selected: true }
        );
      }
    }
  }, [mapLoaded, selectedParcelId, parcels]);

  // Fit bounds to parcels
  const fitToParcels = useCallback(() => {
    if (!mapRef.current || !parcels || parcels.features.length === 0) return;

    const bounds = new (window as unknown as { mapboxgl: MapboxGL }).mapboxgl.LngLatBounds();

    parcels.features.forEach((feature) => {
      const coords = feature.geometry.coordinates;
      if (feature.geometry.type === "Polygon") {
        (coords as number[][][]).forEach((ring) => {
          ring.forEach(([lng, lat]) => bounds.extend([lng, lat]));
        });
      } else if (feature.geometry.type === "MultiPolygon") {
        (coords as number[][][][]).forEach((polygon) => {
          polygon.forEach((ring) => {
            ring.forEach(([lng, lat]) => bounds.extend([lng, lat]));
          });
        });
      }
    });

    mapRef.current.fitBounds(bounds, { padding: 50 });
  }, [parcels]);

  const toggleRiskFilter = (level: string) => {
    setFilters((prev) => ({
      ...prev,
      riskLevels: prev.riskLevels.includes(level)
        ? prev.riskLevels.filter((l) => l !== level)
        : [...prev.riskLevels, level],
    }));
  };

  const toggleSlaFilter = (status: string) => {
    setFilters((prev) => ({
      ...prev,
      slaStatuses: prev.slaStatuses.includes(status)
        ? prev.slaStatuses.filter((s) => s !== status)
        : [...prev.slaStatuses, status],
    }));
  };

  // Fallback if no token
  if (!mapboxToken) {
    return (
      <div className={`rounded-xl border border-dashed border-brand bg-white/60 p-6 ${className}`}>
        <p className="text-sm uppercase tracking-wide text-brand">Map Integration</p>
        <div className="mt-4 h-48 w-full rounded-lg bg-[radial-gradient(circle_at_center,_#cee1ff,_#f8fafc)] flex items-center justify-center">
          <div className="text-center text-slate-500">
            <p className="font-medium">Mapbox Token Required</p>
            <p className="text-xs mt-1">Set VITE_MAPBOX_TOKEN in your environment</p>
          </div>
        </div>
        <p className="mt-3 text-sm text-slate-600">
          Configure your Mapbox access token to enable interactive parcel mapping with GIS layers.
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`rounded-xl border border-rose-200 bg-rose-50 p-6 ${className}`}>
        <p className="text-sm text-rose-600">{error}</p>
        <p className="text-xs text-rose-500 mt-1">Please check your Mapbox token and network connection.</p>
      </div>
    );
  }

  return (
    <div className={`rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden ${className}`}>
      {/* Filters */}
      {showFilters && (
        <div className="px-4 py-3 border-b border-slate-200 bg-slate-50">
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-slate-500">Risk:</span>
              {Object.entries(RISK_COLORS).map(([level, color]) => (
                <button
                  key={level}
                  onClick={() => toggleRiskFilter(level)}
                  className={`text-xs px-2 py-1 rounded-full border transition-colors ${
                    filters.riskLevels.includes(level)
                      ? "border-transparent text-white"
                      : "border-slate-300 bg-white text-slate-600"
                  }`}
                  style={{
                    backgroundColor: filters.riskLevels.includes(level) ? color : undefined,
                  }}
                >
                  {level}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-slate-500">SLA:</span>
              {Object.entries(SLA_COLORS).map(([status, color]) => (
                <button
                  key={status}
                  onClick={() => toggleSlaFilter(status)}
                  className={`text-xs px-2 py-1 rounded-full border transition-colors ${
                    filters.slaStatuses.includes(status)
                      ? "border-transparent text-white"
                      : "border-slate-300 bg-white text-slate-600"
                  }`}
                  style={{
                    backgroundColor: filters.slaStatuses.includes(status) ? color : undefined,
                  }}
                >
                  {status.replace("_", " ")}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2 ml-auto">
              <button
                onClick={fitToParcels}
                className="text-xs px-2 py-1 rounded border border-slate-300 bg-white text-slate-600 hover:bg-slate-50"
              >
                Fit to Parcels
              </button>
              {(filters.riskLevels.length > 0 || filters.slaStatuses.length > 0) && (
                <button
                  onClick={() => setFilters({ riskLevels: [], slaStatuses: [], showOverdueOnly: false })}
                  className="text-xs px-2 py-1 rounded border border-slate-300 bg-white text-slate-600 hover:bg-slate-50"
                >
                  Clear Filters
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Map Container */}
      <div ref={mapContainer} className="h-96 w-full relative">
        {!mapLoaded && (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-100">
            <div className="text-center">
              <div className="animate-spin h-8 w-8 border-2 border-brand border-t-transparent rounded-full mx-auto" />
              <p className="text-xs text-slate-500 mt-2">Loading map...</p>
            </div>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="px-4 py-3 border-t border-slate-200 bg-slate-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <span className="text-xs font-medium text-slate-500">Legend:</span>
            {Object.entries(RISK_COLORS).map(([level, color]) => (
              <div key={level} className="flex items-center gap-1">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: color }} />
                <span className="text-xs text-slate-600 capitalize">{level}</span>
              </div>
            ))}
          </div>
          {parcels && (
            <span className="text-xs text-slate-500">
              {parcels.features.length} parcel{parcels.features.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// Re-export for backwards compatibility
export { ParcelMap as ParcelMapPlaceholder };
