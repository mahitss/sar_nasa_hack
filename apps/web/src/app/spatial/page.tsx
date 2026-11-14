import { InvestigationMap } from "@/components/InvestigationMap";
import { DISCOVERY } from "@/lib/case-data";

export default function SpatialPage() {
  return (
    <div className="space-y-6">
      <div>
        <p className="font-mono text-xs tracking-[0.18em] text-[#d7b56d]">SPATIAL INVESTIGATION</p>
        <h1 className="mt-2 text-3xl font-semibold">Discovery window</h1>
        <p className="mt-2 max-w-3xl text-sm text-[#c9d5cf]">
          Interactive map of the discovery area. The gold outline is a discovery window, not a surveyed lake boundary.
        </p>
      </div>
      <InvestigationMap />
      <section className="rounded-2xl border border-white/10 p-5 text-sm">
        <h2 className="font-medium">Coordinate context</h2>
        <p className="mt-2 text-[#c9d5cf]">
          CRS: WGS 84 (EPSG:4326). Discovery window W {DISCOVERY.west}, S {DISCOVERY.south}, E {DISCOVERY.east}, N{" "}
          {DISCOVERY.north}.
        </p>
      </section>
    </div>
  );
}
