"use client";

import { useEffect, useRef } from "react";
import { Map, NavigationControl } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { discovery } from "@/lib/evidence";

const polygon = {
  type: "Feature" as const,
  properties: { name: discovery.name },
  geometry: {
    type: "Polygon" as const,
    coordinates: [[
      [discovery.west, discovery.south],
      [discovery.east, discovery.south],
      [discovery.east, discovery.north],
      [discovery.west, discovery.north],
      [discovery.west, discovery.south],
    ]],
  },
};

export function InvestigationMap() {
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!container.current) return;
    const map = new Map({
        container: container.current,
        style: {
          version: 8,
          sources: {
            carto: {
              type: "raster",
              tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
              tileSize: 256,
              attribution: "© OpenStreetMap contributors",
            },
          },
          layers: [
            { id: "background", type: "background", paint: { "background-color": "#17211d" } },
            { id: "carto", type: "raster", source: "carto" },
          ],
        },
        center: [(discovery.west + discovery.east) / 2, (discovery.south + discovery.north) / 2],
        zoom: 11,
      });
    map.addControl(new NavigationControl({ showCompass: false }), "top-right");
    map.on("load", () => {
      map.addSource("discovery", { type: "geojson", data: polygon });
      map.addLayer({
        id: "discovery-fill",
        type: "fill",
        source: "discovery",
        paint: { "fill-color": "#d7b56d", "fill-opacity": 0.18 },
      });
      map.addLayer({
        id: "discovery-line",
        type: "line",
        source: "discovery",
        paint: { "line-color": "#f3e2b3", "line-width": 2 },
      });
      map.fitBounds(
        [
          [discovery.west, discovery.south],
          [discovery.east, discovery.north],
        ],
        { padding: 48, duration: 0 },
      );
    });
    return () => map.remove();
  }, []);

  return (
    <div>
      <div ref={container} className="h-[28rem] w-full overflow-hidden rounded-2xl border border-white/10 bg-[#17211d]" />
      <p className="mt-3 text-sm text-[#c9d5cf]">If the basemap tiles do not load, the gold outline remains on the dark canvas. It is the discovery window, not a lake boundary.</p>
    </div>
  );
}
