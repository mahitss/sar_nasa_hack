import { ACQUISITIONS, COMPARISON_FIELDS } from "@/lib/case-data";

export default function AcquisitionsPage() {
  return (
    <div className="space-y-6">
      <div>
        <p className="font-mono text-xs tracking-[0.18em] text-[#d7b56d]">ACQUISITION COMPARISON</p>
        <h1 className="mt-2 text-3xl font-semibold">September 2026 NISAR pair</h1>
        <p className="mt-2 max-w-3xl text-sm text-[#c9d5cf]">
          Group D40, provisional CRID P05023. Both records share reported metadata. Orbit and pointing inconsistencies remain
          unresolved.
        </p>
      </div>

      <section className="rounded-2xl border border-white/10">
        <h2 className="px-4 pt-4 text-lg font-medium">Granules</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-white/5 text-xs uppercase tracking-wide text-[#93a39b]">
              <tr>
                <th className="px-4 py-3">Field</th>
                {ACQUISITIONS.map((a) => (
                  <th key={a.iso} className="px-4 py-3">{a.date}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr className="border-t border-white/10">
                <th scope="row" className="px-4 py-3 font-medium">Granule</th>
                {ACQUISITIONS.map((a) => (
                  <td key={a.granule} className="break-all px-4 py-3 font-mono text-xs">{a.granule}</td>
                ))}
              </tr>
              <tr className="border-t border-white/10">
                <th scope="row" className="px-4 py-3 font-medium">Raw sweep-stable pixels</th>
                {ACQUISITIONS.map((a) => (
                  <td key={a.iso} className="px-4 py-3">{a.rawStable}</td>
                ))}
              </tr>
              <tr className="border-t border-white/10">
                <th scope="row" className="px-4 py-3 font-medium">Filtered sweep-stable pixels</th>
                {ACQUISITIONS.map((a) => (
                  <td key={a.iso} className="px-4 py-3">{a.filteredStable}</td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-2xl border border-white/10">
        <h2 className="px-4 pt-4 text-lg font-medium">Shared metadata</h2>
        <div className="overflow-x-auto">
          <table className="w-full table-fixed text-left text-sm">
            <thead className="bg-white/5 text-xs uppercase tracking-wide text-[#93a39b]">
              <tr>
                <th scope="col" className="w-[28%] px-4 py-3">Field</th>
                {ACQUISITIONS.map((a) => (
                  <th scope="col" key={a.iso} className="px-4 py-3">{a.date}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {COMPARISON_FIELDS.map((f) => (
                <tr key={f.label} className="border-t border-white/10">
                  <th scope="row" className="px-4 py-3 align-top font-medium">{f.label}</th>
                  <td className="break-words px-4 py-3 align-top">{f.value}</td>
                  <td className="break-words px-4 py-3 align-top">{f.value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="px-4 pb-4 pt-2 text-sm text-[#93a39b]">
          Coordinate steps are grid spacing. They are not a claim that each step is an independent resolution cell.
        </p>
      </section>

      <section className="rounded-2xl border border-[#d7b56d]/40 bg-[#d7b56d]/10 p-5 text-sm text-[#f3e2b3]">
        <p className="font-medium">Outstanding inconsistencies</p>
        <ul className="mt-2 list-disc space-y-1 pl-5">
          <li>Filename token N expects NOE orbit ephemeris; observed orbitType is MOE.</li>
          <li>Filename token N expects NRP radar pointing; observed attitudeType is Custom.</li>
          <li>No geolocation error was measured. The mismatch is unresolved.</li>
          <li>Geometric accuracy bias and standard deviation are NaN.</li>
        </ul>
      </section>
    </div>
  );
}
