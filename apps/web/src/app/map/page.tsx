import { InvestigationMap } from "@/components/InvestigationMap";
import { discovery } from "@/lib/evidence";

export default function MapPage() {
  return (
    <div className="space-y-5">
      <div>
        <p className="font-mono text-xs tracking-[0.18em] text-[#d7b56d]">DISCOVERY AREA</p>
        <h1 className="mt-2 text-3xl font-semibold">Investigation map</h1>
        <p className="mt-2 max-w-3xl text-sm text-[#c9d5cf]">{discovery.role} West {discovery.west}, south {discovery.south}, east {discovery.east}, north {discovery.north}.</p>
      </div>
      <InvestigationMap />
      <svg viewBox="0 0 320 180" role="img" aria-label="Discovery window locator" className="h-40 w-full rounded-2xl border border-white/10 bg-[#101816]">
        <rect x="70" y="36" width="180" height="108" fill="none" stroke="#d7b56d" strokeWidth="2" />
        <text x="76" y="28" fill="#f3e2b3" fontSize="12">30.15 N</text>
        <text x="76" y="160" fill="#f3e2b3" fontSize="12">30.03 N</text>
        <text x="12" y="96" fill="#f3e2b3" fontSize="12">79.75 E</text>
        <text x="256" y="96" fill="#f3e2b3" fontSize="12">79.87 E</text>
      </svg>
      <p className="text-xs text-[#93a39b]">Basemap © OpenStreetMap contributors. No lake polygon, shoreline, water extent, satellite raster, or terrain-shadow layer is drawn.</p>
    </div>
  );
}
