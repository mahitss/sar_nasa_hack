"use client";

import { caseSummary, discovery, evidenceItems, limitations, reportExport } from "@/lib/evidence";
import { useReview } from "@/lib/review";

export default function ReportPage() {
  const { choices } = useReview();
  function downloadJson() {
    const payload = { ...reportExport, prototypeReviewChoices: choices, exportedAt: new Date().toISOString() };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "rivet-kuwari-evidence.json";
    link.click();
    URL.revokeObjectURL(url);
  }
  return (
    <div className="space-y-6">
      <div className="no-print flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-mono text-xs tracking-[0.18em] text-[#d7b56d]">CASE REPORT</p>
          <h1 className="mt-2 text-3xl font-semibold">Investigation report</h1>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={() => window.print()} className="rounded-full bg-[#d7b56d] px-4 py-2 text-sm font-medium text-[#1a1408]">Print</button>
          <button type="button" onClick={downloadJson} className="rounded-full border border-white/15 px-4 py-2 text-sm">Export JSON</button>
        </div>
      </div>
      <article className="space-y-5 rounded-3xl border border-white/10 bg-white p-6 text-black print:border-0">
        <header>
          <p className="font-mono text-xs tracking-[0.18em]">RIVET</p>
          <h2 className="text-2xl font-semibold">{caseSummary.caseName}</h2>
          <p className="mt-1 text-sm">{discovery.place}. {caseSummary.period}. {caseSummary.status}.</p>
          <p className="mt-3 text-sm font-medium">{caseSummary.warning}</p>
        </header>
        <section>
          <h3 className="font-medium">Discovery window</h3>
          <p className="text-sm">West {discovery.west}, south {discovery.south}, east {discovery.east}, north {discovery.north}. {discovery.role}</p>
        </section>
        <section>
          <h3 className="font-medium">Source acquisitions and QC</h3>
          <ul className="mt-2 space-y-3 text-sm">
            {evidenceItems.map((item) => (
              <li key={item.id}>
                <span className="font-medium">{item.title}.</span> {item.summary} Prototype review: {choices[item.id] ?? "not selected"}.
              </li>
            ))}
          </ul>
        </section>
        <section>
          <h3 className="font-medium">Limitations and outstanding questions</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
            {limitations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
        <p className="text-xs">Prototype interaction only — decisions are not persisted to a backend.</p>
      </article>
    </div>
  );
}
