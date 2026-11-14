"use client";

import { CASE, DISCOVERY, ACQUISITIONS, EVIDENCE, LIMITATIONS, NEXT_STEPS, MISSION012, COMPARISON_FIELDS } from "@/lib/case-data";

export default function ReportPage() {
  function downloadJson() {
    const payload = {
      product: "RIVET investigation report",
      persistedToBackend: false,
      reviewStorage: "none",
      case: CASE,
      discovery: DISCOVERY,
      acquisitions: ACQUISITIONS,
      comparison: COMPARISON_FIELDS,
      mission012: MISSION012,
      evidence: EVIDENCE,
      limitations: LIMITATIONS,
      nextSteps: NEXT_STEPS,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "rivet-investigation-report.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-6">
      <div className="no-print flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-mono text-xs tracking-[0.18em] text-[#d7b56d]">INVESTIGATION REPORT</p>
          <h1 className="mt-2 text-3xl font-semibold">Reproducible report</h1>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => window.print()}
            className="rounded-full bg-[#d7b56d] px-4 py-2 text-sm font-medium text-[#1a1408] focus-visible:outline focus-visible:outline-2 focus-visible:outline-white"
          >
            Print / Save PDF
          </button>
          <button
            type="button"
            onClick={downloadJson}
            className="rounded-full border border-white/15 px-4 py-2 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#d7b56d]"
          >
            Export JSON
          </button>
        </div>
      </div>

      <article className="space-y-6 rounded-3xl border border-white/10 bg-white p-6 text-black print:border-0">
        <header>
          <h2 className="text-2xl font-semibold">RIVET investigation report</h2>
          <p className="text-sm text-gray-700">{CASE.name} — {CASE.place}</p>
          <p className="text-sm text-gray-700">Period: {CASE.period}</p>
          <p className="text-sm text-gray-700">Status: {CASE.status}</p>
        </header>

        <section>
          <h3 className="font-medium">Discovery region</h3>
          <p className="mt-2 text-sm">
            W {DISCOVERY.west}, S {DISCOVERY.south}, E {DISCOVERY.east}, N {DISCOVERY.north}. This is a discovery window, not a surveyed lake boundary.
          </p>
        </section>

        <section>
          <h3 className="font-medium">Satellite acquisitions</h3>
          <ul className="mt-2 space-y-2 text-sm">
            {ACQUISITIONS.map((a) => (
              <li key={a.granule}>
                {a.date}: <span className="font-mono text-xs">{a.granule}</span>. Raw stable {a.rawStable}. Filtered stable {a.filteredStable}.
              </li>
            ))}
          </ul>
        </section>

        <section>
          <h3 className="font-medium">Comparability group</h3>
          <ul className="mt-2 space-y-1 text-sm">
            {COMPARISON_FIELDS.map((f) => (
              <li key={f.label}><span className="font-medium">{f.label}:</span> {f.value}</li>
            ))}
          </ul>
        </section>

        <section>
          <h3 className="font-medium">Mission 012 NISAR metadata</h3>
          <ul className="mt-2 space-y-1 text-sm">
            <li>Wrapper bytes read per stream: {MISSION012.wrapperBytesRead}.</li>
            <li>orbitType: {MISSION012.orbitType}. attitudeType: {MISSION012.attitudeType}.</li>
            <li>shadowMaskingApplied: {MISSION012.shadowMaskingApplied} (string).</li>
            <li>Radar grid: {MISSION012.grid.x} x {MISSION012.grid.y} x {MISSION012.grid.height}.</li>
            <li>Steps: {MISSION012.steps.x} m, {MISSION012.steps.y} m, {MISSION012.steps.height} m.</li>
            <li>Incidence cube: {MISSION012.incidenceShape}. Values not extracted.</li>
            <li>Processor DEM: {MISSION012.processorDem}.</li>
          </ul>
        </section>

        <section>
          <h3 className="font-medium">Evidence records</h3>
          <ul className="mt-2 space-y-3 text-sm">
            {EVIDENCE.map((e) => (
              <li key={e.id}>
                <span className="font-medium">{e.title} (Mission {e.mission}, {e.status}).</span> {e.summary} Source: {e.source}.
              </li>
            ))}
          </ul>
        </section>

        <section>
          <h3 className="font-medium">Limitations and unresolved questions</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
            {LIMITATIONS.map((l) => <li key={l}>{l}</li>)}
          </ul>
        </section>

        <section>
          <h3 className="font-medium">Recommended next verification steps</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
            {NEXT_STEPS.map((s) => <li key={s}>{s}</li>)}
          </ul>
        </section>

        <p className="text-xs text-gray-600">
          Stored only in this browser. Not an institutional review and not a scientific acceptance. No confirmed water detection.
        </p>
      </article>
    </div>
  );
}
