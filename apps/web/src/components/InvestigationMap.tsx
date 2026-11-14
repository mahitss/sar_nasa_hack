"use client";

import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { DISCOVERY } from "@/lib/case-data";

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

export function InvestigationMap() {
  const container = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [tilesFailed, setTilesFailed] = useState(false);

  useEffect(() => {
    if (!container.current) return;
    let map: maplibregl.Map | null = null;
    try {
      map = new maplibregl.Map({
        container: container.current,
        style: {
          version: 8,
          sources: {
            osm: {
              type: "raster",
              tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
              tileSize: 256,
              attribution: "© OpenStreetMap contributors",
            },
          },
          layers: [{ id: "osm", type: "raster", source: "osm" }],
        },
        center: [(DISCOVERY.west + DISCOVERY.east) / 2, (DISCOVERY.south + DISCOVERY.north) / 2],
        zoom: 11,
      });
      map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
      map.on("error", (e) => {
        const ev = e as unknown as { tile?: unknown };
        if (ev?.tile) setTilesFailed(true);
        else setStatus("error");
      });
      map.on("load", () => {
        map!.addSource("discovery", { type: "geojson", data: polygon });
        map!.addLayer({
          id: "discovery-fill",
          type: "fill",
          source: "discovery",
          paint: { "fill-color": "#d7b56d", "fill-opacity": 0.08 },
        });
        map!.addLayer({
          id: "discovery-line",
          type: "line",
          source: "discovery",
          paint: { "line-color": "#f3e2b3", "line-width": 3 },
        });
        map!.fitBounds(
          [
            [DISCOVERY.west, DISCOVERY.south],
            [DISCOVERY.east, DISCOVERY.north],
          ],
          { padding: 40 }
        );
        setStatus("ready");
      });
    } catch {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setStatus("error");
    }
    return () => {
      map?.remove();
    };
  }, []);

  return (
    <div>
      {status === "loading" && (
        <div className="flex h-[28rem] items-center justify-center rounded-2xl border border-white/10 bg-[#17211d] text-sm text-[#93a39b]">
          Loading map…
        </div>
      )}
      {status === "error" && (
        <div className="flex h-[28rem] items-center justify-center rounded-2xl border border-white/10 bg-[#17211d] text-sm text-[#c9d5cf]">
          Map could not be loaded. Coordinate context is still shown below.
        </div>
      )}
      <div
        ref={container}
        className={`h-[28rem] w-full overflow-hidden rounded-2xl border border-white/10 bg-[#17211d] ${status !== "ready" ? "hidden" : ""}`}
      />
      <p className="mt-3 text-sm text-[#c9d5cf]" role="status">
        {tilesFailed
          ? "Basemap tiles did not load. The gold outline on the dark canvas is still the discovery window, not a lake boundary."
          : "The gold outline is the discovery window, not a lake boundary."}
      </p>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div className="rounded-2xl border border-white/10 p-4 text-sm">
          <p className="font-medium">Discovery window</p>
          <p className="mt-1 font-mono text-xs text-[#c9d5cf]">
            W {DISCOVERY.west}, S {DISCOVERY.south}, E {DISCOVERY.east}, N {DISCOVERY.north}
          </p>
          <p className="mt-2 text-[#93a39b]">Place: Kuwari, Bageshwar district, Uttarakhand, India.</p>
        </div>
        <div className="rounded-2xl border border-white/10 p-4 text-sm">
          <p className="font-medium">Map notes</p>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-[#93a39b]">
            <li>No lake polygon, shoreline, raster, footprint, shadow, or layover mask is fabricated.</li>
            <li>Basemap © OpenStreetMap contributors.</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
