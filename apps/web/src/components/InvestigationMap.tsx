"use client";

import { useEffect, useRef, useState, useMemo, useCallback } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { DISCOVERY, INVESTIGATION_POINTS, type InvestigationPoint } from "@/lib/case-data";

// Configure MapLibre to use the standalone web worker served from public/
if (typeof window !== "undefined" && typeof maplibregl.setWorkerUrl === "function") {
  maplibregl.setWorkerUrl("/maplibre-gl-worker.mjs");
}

const polygon: GeoJSON.Feature = {
  type: "Feature",
  properties: {},
  geometry: {
    type: "Polygon",
    coordinates: [[
      [DISCOVERY.west, DISCOVERY.south],
      [DISCOVERY.east, DISCOVERY.south],
      [DISCOVERY.east, DISCOVERY.north],
      [DISCOVERY.west, DISCOVERY.north],
      [DISCOVERY.west, DISCOVERY.south],
    ]],
  },
};

interface InvestigationMapProps {
  customPoints?: InvestigationPoint[];
  selectedPointId?: string | null;
  onSelectPoint?: (point: InvestigationPoint | null) => void;
}

export function InvestigationMap({
  customPoints = [],
  selectedPointId,
  onSelectPoint,
}: InvestigationMapProps) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [activeCategory, setActiveCategory] = useState<string>("All");
  const [activeBasemap, setActiveBasemap] = useState<"topo" | "satellite" | "osm">("topo");

  const allPoints = useMemo(() => {
    return [...INVESTIGATION_POINTS, ...customPoints];
  }, [customPoints]);

  // Keep refs for event callbacks to avoid tearing down map instance on parent re-renders
  const allPointsRef = useRef(allPoints);
  allPointsRef.current = allPoints;

  const onSelectPointRef = useRef(onSelectPoint);
  onSelectPointRef.current = onSelectPoint;

  const filteredPoints = useMemo(() => {
    if (activeCategory === "All") return allPoints;
    return allPoints.filter((p) => p.category === activeCategory);
  }, [allPoints, activeCategory]);

  const categories = useMemo(() => {
    const cats = new Set(allPoints.map((p) => p.category));
    return ["All", ...Array.from(cats)];
  }, [allPoints]);

  const pointsGeoJSON = useMemo<GeoJSON.FeatureCollection>(() => {
    return {
      type: "FeatureCollection",
      features: filteredPoints.map((pt) => ({
        type: "Feature",
        id: pt.id,
        properties: {
          id: pt.id,
          name: pt.name,
          category: pt.category,
          color: pt.color,
          elevation: pt.elevation,
          description: pt.description,
          scientificContext: pt.scientificContext,
        },
        geometry: {
          type: "Point",
          coordinates: pt.coordinates,
        },
      })),
    };
  }, [filteredPoints]);

  const openPopupForPoint = useCallback((pt: InvestigationPoint) => {
    const map = mapRef.current;
    if (!map) return;
    if (popupRef.current) popupRef.current.remove();

    const popup = new maplibregl.Popup({ offset: 14, closeButton: true, className: "rivet-map-popup" })
      .setLngLat(pt.coordinates)
      .setHTML(`
        <div style="font-family: ui-sans-serif, system-ui, sans-serif; font-size: 12px; color: #111; max-width: 260px; line-height: 1.4;">
          <div style="display:flex; align-items:center; gap:6px; margin-bottom: 4px;">
            <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:${pt.color};"></span>
            <span style="font-size: 10px; font-weight: 700; text-transform: uppercase; color: #4b5563;">${pt.category}</span>
          </div>
          <h4 style="margin: 0 0 4px; font-size: 13px; font-weight: 700; color: #111827;">${pt.name}</h4>
          <p style="margin: 0 0 6px; color: #374151; font-size: 11px;">${pt.description}</p>
          <div style="font-size: 10px; color: #4b5563; font-style: italic; margin-bottom: 6px; background: #f3f4f6; padding: 4px 6px; border-radius: 4px;">
            ${pt.scientificContext}
          </div>
          <div style="font-size: 10px; color: #6b7280; font-family: monospace; border-top: 1px solid #e5e7eb; padding-top: 4px; display:flex; justify-content:space-between;">
            <span>${pt.coordinates[1].toFixed(4)}°N, ${pt.coordinates[0].toFixed(4)}°E</span>
            <span>Elev: ${pt.elevation}</span>
          </div>
        </div>
      `)
      .addTo(map);

    popupRef.current = popup;
  }, []);

  // Sync external selection with map
  useEffect(() => {
    if (!selectedPointId || status !== "ready" || !mapRef.current) return;
    const pt = allPoints.find((p) => p.id === selectedPointId);
    if (pt && mapRef.current) {
      mapRef.current.flyTo({ center: pt.coordinates, zoom: 12.5, essential: true });
      openPopupForPoint(pt);
    }
  }, [selectedPointId, allPoints, status, openPopupForPoint]);

  // Update GeoJSON source without recreating the map
  useEffect(() => {
    const map = mapRef.current;
    if (!map || status !== "ready") return;
    const source = map.getSource("investigation-points") as maplibregl.GeoJSONSource | undefined;
    if (source) {
      source.setData(pointsGeoJSON);
    }
  }, [pointsGeoJSON, status]);

  const switchBasemap = (mode: "topo" | "satellite" | "osm") => {
    setActiveBasemap(mode);
    const map = mapRef.current;
    if (!map) return;
    if (map.getLayer("base-topo")) map.setLayoutProperty("base-topo", "visibility", mode === "topo" ? "visible" : "none");
    if (map.getLayer("base-sat")) map.setLayoutProperty("base-sat", "visibility", mode === "satellite" ? "visible" : "none");
    if (map.getLayer("base-osm")) map.setLayoutProperty("base-osm", "visibility", mode === "osm" ? "visible" : "none");
  };

  // Single mount effect: initialize MapLibre once with 100% free, reliable ESRI & OSM tiles
  useEffect(() => {
    if (!container.current) return;
    let map: maplibregl.Map | null = null;
    let isMounted = true;

    try {
      if (typeof maplibregl.setWorkerUrl === "function") {
        maplibregl.setWorkerUrl("/maplibre-gl-worker.mjs");
      }

      map = new maplibregl.Map({
        container: container.current,
        style: {
          version: 8,
          sources: {
            // ESRI World Topo: Clean contour lines, mountain relief, elevations, rivers. No API key needed.
            "esri-topo": {
              type: "raster",
              tiles: [
                "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
              ],
              tileSize: 256,
              attribution: "© Esri, USGS",
            },
            // ESRI World Imagery: High-resolution satellite view of Himalayas & Kuwari Gorge. No API key needed.
            "esri-sat": {
              type: "raster",
              tiles: [
                "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
              ],
              tileSize: 256,
              attribution: "© Esri, DigitalGlobe, Earthstar Geographics",
            },
            // OpenStreetMap: Street & boundary view
            osm: {
              type: "raster",
              tiles: [
                "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
              ],
              tileSize: 256,
              attribution: "© OpenStreetMap contributors",
            },
          },
          layers: [
            { id: "base-topo", type: "raster", source: "esri-topo", layout: { visibility: "visible" } },
            { id: "base-sat", type: "raster", source: "esri-sat", layout: { visibility: "none" } },
            { id: "base-osm", type: "raster", source: "osm", layout: { visibility: "none" } },
          ],
        },
        center: [(DISCOVERY.west + DISCOVERY.east) / 2, (DISCOVERY.south + DISCOVERY.north) / 2],
        zoom: 11,
      });

      mapRef.current = map;
      map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");

      map.on("error", (e) => {
        if (!isMounted) return;
        console.warn("MapLibre non-fatal event:", e);
      });

      map.on("load", () => {
        if (!isMounted || !map) return;
        try {
          // 1. Discovery window polygon layers
          map.addSource("discovery", { type: "geojson", data: polygon });
          map.addLayer({
            id: "discovery-fill",
            type: "fill",
            source: "discovery",
            paint: { "fill-color": "#d7b56d", "fill-opacity": 0.08 },
          });
          map.addLayer({
            id: "discovery-line",
            type: "line",
            source: "discovery",
            paint: { "line-color": "#f3e2b3", "line-width": 2.5, "line-dasharray": [3, 2] },
          });

          // 2. Points of interest source and layers
          map.addSource("investigation-points", { type: "geojson", data: pointsGeoJSON });

          // Halo outer pulse ring
          map.addLayer({
            id: "points-outer",
            type: "circle",
            source: "investigation-points",
            paint: {
              "circle-radius": 12,
              "circle-color": ["get", "color"],
              "circle-opacity": 0.35,
            },
          });

          // Solid inner core circle
          map.addLayer({
            id: "points-inner",
            type: "circle",
            source: "investigation-points",
            paint: {
              "circle-radius": 6.5,
              "circle-color": ["get", "color"],
              "circle-stroke-width": 2,
              "circle-stroke-color": "#ffffff",
            },
          });

          // Text label
          map.addLayer({
            id: "points-label",
            type: "symbol",
            source: "investigation-points",
            layout: {
              "text-field": ["get", "name"],
              "text-size": 11,
              "text-offset": [0, 1.2],
              "text-anchor": "top",
              "text-font": ["Open Sans Regular", "Arial Unicode MS Regular"],
            },
            paint: {
              "text-color": "#ffffff",
              "text-halo-color": "#0b0f0e",
              "text-halo-width": 2,
            },
          });

          // Interactive click on points using stable refs
          map.on("click", "points-inner", (e) => {
            if (!e.features || !e.features[0]) return;
            const f = e.features[0];
            const ptId = f.properties?.id;
            const pt = allPointsRef.current.find((p) => p.id === ptId);
            if (pt) {
              openPopupForPoint(pt);
              onSelectPointRef.current?.(pt);
            }
          });

          map.on("click", "points-outer", (e) => {
            if (!e.features || !e.features[0]) return;
            const f = e.features[0];
            const ptId = f.properties?.id;
            const pt = allPointsRef.current.find((p) => p.id === ptId);
            if (pt) {
              openPopupForPoint(pt);
              onSelectPointRef.current?.(pt);
            }
          });

          map.on("mouseenter", "points-inner", () => {
            if (map) map.getCanvas().style.cursor = "pointer";
          });
          map.on("mouseleave", "points-inner", () => {
            if (map) map.getCanvas().style.cursor = "";
          });

          // Resize and fit bounds
          map.resize();
          map.fitBounds(
            [
              [DISCOVERY.west, DISCOVERY.south],
              [DISCOVERY.east, DISCOVERY.north],
            ],
            { padding: 45 }
          );

          setStatus("ready");

          // Schedule follow-up resizes to guarantee canvas fills 100% when layout settles
          setTimeout(() => {
            if (isMounted && map) map.resize();
          }, 80);
          setTimeout(() => {
            if (isMounted && map) map.resize();
          }, 300);
          setTimeout(() => {
            if (isMounted && map) map.resize();
          }, 800);
        } catch (err) {
          console.error("Error setting up map layers:", err);
          setStatus("ready");
        }
      });

      const resizeObserver = new ResizeObserver(() => {
        if (map) map.resize();
      });
      resizeObserver.observe(container.current);

      const handleWindowResize = () => {
        if (map) map.resize();
      };
      window.addEventListener("resize", handleWindowResize);

      return () => {
        isMounted = false;
        window.removeEventListener("resize", handleWindowResize);
        resizeObserver.disconnect();
        mapRef.current = null;
        map?.remove();
      };
    } catch (err) {
      console.error("Failed to initialize MapLibre map:", err);
      setStatus("error");
    }
  // Intentionally empty array: map instance is initialized once on mount
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handlePointClick = (pt: InvestigationPoint) => {
    if (mapRef.current) {
      mapRef.current.flyTo({ center: pt.coordinates, zoom: 13, essential: true });
      openPopupForPoint(pt);
    }
    onSelectPoint?.(pt);
  };

  const handleResetBounds = () => {
    if (mapRef.current) {
      mapRef.current.resize();
      mapRef.current.fitBounds(
        [
          [DISCOVERY.west, DISCOVERY.south],
          [DISCOVERY.east, DISCOVERY.north],
        ],
        { padding: 45, essential: true }
      );
      if (popupRef.current) popupRef.current.remove();
      onSelectPoint?.(null);
    }
  };

  return (
    <div className="space-y-3">
      {/* Basemap Controls & Category Filter Pills */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Basemap Switcher */}
        <div className="flex items-center gap-1.5 rounded-full border border-white/15 bg-[#121716] p-1">
          <button
            type="button"
            onClick={() => switchBasemap("topo")}
            className={`rounded-full px-3 py-1 text-xs font-medium transition ${
              activeBasemap === "topo"
                ? "bg-[#d7b56d] text-[#1a1408] font-semibold shadow"
                : "text-[#c9d5cf] hover:text-white"
            }`}
          >
            ⛰️ Topo Relief
          </button>
          <button
            type="button"
            onClick={() => switchBasemap("satellite")}
            className={`rounded-full px-3 py-1 text-xs font-medium transition ${
              activeBasemap === "satellite"
                ? "bg-[#d7b56d] text-[#1a1408] font-semibold shadow"
                : "text-[#c9d5cf] hover:text-white"
            }`}
          >
            🛰️ Satellite (Esri)
          </button>
          <button
            type="button"
            onClick={() => switchBasemap("osm")}
            className={`rounded-full px-3 py-1 text-xs font-medium transition ${
              activeBasemap === "osm"
                ? "bg-[#d7b56d] text-[#1a1408] font-semibold shadow"
                : "text-[#c9d5cf] hover:text-white"
            }`}
          >
            🗺️ Street (OSM)
          </button>
        </div>

        {/* Category Pills & Reset */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex flex-wrap items-center gap-1 text-xs">
            {categories.map((cat) => {
              const isSelected = activeCategory === cat;
              const count = cat === "All" ? allPoints.length : allPoints.filter((p) => p.category === cat).length;
              return (
                <button
                  key={cat}
                  type="button"
                  onClick={() => setActiveCategory(cat)}
                  className={`rounded-full border px-2.5 py-1 text-xs transition ${
                    isSelected
                      ? "border-[#d7b56d] bg-[#d7b56d]/15 font-semibold text-white"
                      : "border-white/10 bg-[#121716] text-[#c9d5cf] hover:border-white/20"
                  }`}
                >
                  {cat} ({count})
                </button>
              );
            })}
          </div>

          <button
            type="button"
            onClick={handleResetBounds}
            className="rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs text-[#c9d5cf] transition hover:bg-white/10 hover:text-white"
          >
            ⟲ Reset View
          </button>
        </div>
      </div>

      {/* Map Canvas: explicit height + absolute child fills 100% of container */}
      <div className="relative h-[32rem] w-full overflow-hidden rounded-2xl border border-white/10 bg-[#17211d] shadow-inner">
        <div ref={container} className="absolute inset-0 h-full w-full" />
        {status === "loading" && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-[#17211d] text-sm text-[#93a39b]">
            <div className="flex items-center gap-2">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-[#d7b56d] border-t-transparent" />
              <span>Loading map & terrain points…</span>
            </div>
          </div>
        )}
        {status === "error" && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-[#17211d] text-sm text-[#c9d5cf]">
            Map could not be loaded. Coordinate context is still shown below.
          </div>
        )}
      </div>

      <p className="text-xs text-[#93a39b]" role="status">
        Discovery window (gold dashed outline): W {DISCOVERY.west}°E, S {DISCOVERY.south}°N to E {DISCOVERY.east}°E, N {DISCOVERY.north}°N in Bageshwar district.
        Toggle basemap between <strong>⛰️ Topo Relief</strong> and <strong>🛰️ Satellite (Esri)</strong>, or click any landmark marker to fly and inspect point telemetry.
      </p>

      {/* Interactive Point Navigator Grid */}
      <div className="mt-4 grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
        {filteredPoints.map((pt) => {
          const isSelected = selectedPointId === pt.id;
          return (
            <button
              key={pt.id}
              type="button"
              onClick={() => handlePointClick(pt)}
              className={`flex flex-col justify-between rounded-xl border p-3 text-left transition ${
                isSelected
                  ? "border-[#d7b56d] bg-[#d7b56d]/10 shadow-lg"
                  : "border-white/10 bg-[#121716] hover:border-white/20 hover:bg-[#161d1c]"
              }`}
            >
              <div>
                <div className="flex items-center justify-between gap-2">
                  <span
                    className="inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider"
                    style={{ backgroundColor: `${pt.color}20`, color: pt.color }}
                  >
                    {pt.category}
                  </span>
                  <span className="font-mono text-[11px] text-[#93a39b]">{pt.elevation}</span>
                </div>
                <h4 className="mt-1.5 font-medium text-sm text-white">{pt.name}</h4>
                <p className="mt-1 text-xs text-[#93a39b] line-clamp-2">{pt.description}</p>
              </div>
              <div className="mt-2.5 flex items-center justify-between border-t border-white/5 pt-2 font-mono text-[10px] text-[#c9d5cf]">
                <span>{pt.coordinates[1].toFixed(4)}°N, {pt.coordinates[0].toFixed(4)}°E</span>
                <span className="text-[#d7b56d]">Inspect ➔</span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
