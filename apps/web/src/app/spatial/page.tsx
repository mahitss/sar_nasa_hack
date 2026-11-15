"use client";

import { useState } from "react";
import { InvestigationMap } from "@/components/InvestigationMap";
import { AiAssistant } from "@/components/AiAssistant";
import { DISCOVERY, INVESTIGATION_POINTS, type InvestigationPoint } from "@/lib/case-data";

export default function SpatialPage() {
  const [customPoints, setCustomPoints] = useState<InvestigationPoint[]>([]);
  const [selectedPoint, setSelectedPoint] = useState<InvestigationPoint | null>(null);

  const handleAddPoint = (pt: InvestigationPoint) => {
    setCustomPoints((prev) => {
      if (prev.some((p) => p.id === pt.id)) return prev;
      return [...prev, pt];
    });
    setSelectedPoint(pt);
  };

  const handleAddAllPoints = (points: InvestigationPoint[]) => {
    setCustomPoints((prev) => {
      const existingIds = new Set(prev.map((p) => p.id));
      const newPoints = points.filter((p) => !existingIds.has(p.id));
      return [...prev, ...newPoints];
    });
    if (points.length > 0) {
      setSelectedPoint(points[0]);
    }
  };

  const totalPoints = INVESTIGATION_POINTS.length + customPoints.length;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="font-mono text-xs tracking-[0.18em] text-[#d7b56d]">SPATIAL INVESTIGATION</p>
          <h1 className="mt-2 text-3xl font-semibold">Discovery Zone & Terrain Points</h1>
          <p className="mt-2 max-w-3xl text-sm text-[#c9d5cf]">
            Interactive geospatial map of the Kuwari landslide dam investigation area in Bageshwar district.
            Inspect verified hydrological and radar landmarks, or synthesize new target coordinates using the NASA Earth Science AI Copilot.
          </p>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs text-[#93a39b]">
          <span className="rounded-full border border-white/10 bg-[#121716] px-3 py-1">
            Active POIs: <strong className="text-white">{totalPoints}</strong>
          </span>
          {customPoints.length > 0 ? (
            <span className="rounded-full border border-[#d7b56d]/30 bg-[#d7b56d]/10 px-3 py-1 text-[#d7b56d]">
              NASA AI Generated: {customPoints.length}
            </span>
          ) : null}
        </div>
      </div>

      {/* Main Map Component with Multi-point support */}
      <InvestigationMap
        customPoints={customPoints}
        selectedPointId={selectedPoint?.id}
        onSelectPoint={setSelectedPoint}
      />

      {/* NASA AI Assistant with Multi-point Synthesis */}
      <AiAssistant
        onAddPoint={handleAddPoint}
        onAddAllPoints={handleAddAllPoints}
        onSelectPoint={setSelectedPoint}
        mode="spatial"
      />

      {/* Coordinate Context and Scientific Metadata */}
      <div className="grid gap-4 md:grid-cols-2">
        <section className="rounded-2xl border border-white/10 bg-[#121716] p-5 text-sm">
          <h2 className="font-semibold text-white">Coordinate & Projection Bounds</h2>
          <div className="mt-3 space-y-2 text-xs text-[#c9d5cf]">
            <p>
              <strong className="text-[#93a39b]">Reference CRS:</strong> WGS 84 (EPSG:4326) / UTM Zone 44N (EPSG:32644)
            </p>
            <p>
              <strong className="text-[#93a39b]">Discovery Bounding Box:</strong> W {DISCOVERY.west}°E, S {DISCOVERY.south}°N, E {DISCOVERY.east}°E, N {DISCOVERY.north}°N
            </p>
            <p>
              <strong className="text-[#93a39b]">Spatial Center:</strong> 30.0900°N, 79.8100°E (~2,400 m elevation)
            </p>
            <p className="pt-2 text-[11px] text-[#93a39b]">
              The gold dashed perimeter delineates the satellite radar cropping discovery window. It does not represent a surveyed shoreline or lake perimeter.
            </p>
          </div>
        </section>

        <section className="rounded-2xl border border-white/10 bg-[#121716] p-5 text-sm">
          <h2 className="font-semibold text-white">Investigation Standards</h2>
          <ul className="mt-3 list-disc space-y-1.5 pl-5 text-xs text-[#93a39b]">
            <li>All spatial coordinates are tied to reproducible DEM crops (Copernicus GLO-30 2023_1).</li>
            <li>No artificial water boundary or simulated inundation polygon is promoted without human review.</li>
            <li>NASA AI-synthesized points are recorded with their parameter and prompt provenance.</li>
            <li>Basemap imagery and vector roads © OpenStreetMap contributors.</li>
          </ul>
        </section>
      </div>
    </div>
  );
}
