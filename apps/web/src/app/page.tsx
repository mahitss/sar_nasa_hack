import Link from "next/link";
import { CASE, DISCOVERY, ACQUISITIONS, EVIDENCE, LIMITATIONS } from "@/lib/case-data";

const links = [
  { href: "/spatial", label: "Open spatial investigation" },
  { href: "/acquisitions", label: "Compare acquisitions" },
  { href: "/evidence", label: "Open evidence ledger" },
  { href: "/report", label: "Read investigation report" },
];

export default function OverviewPage() {
  return (
    <div className="space-y-10">
      <section className="space-y-4">
        <p className="font-mono text-xs tracking-[0.22em] text-[#d7b56d]">RIVET</p>
        <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">{CASE.name}</h1>
        <p className="max-w-3xl text-lg text-[#c9d5cf]">{CASE.place}</p>
        <p className="max-w-3xl text-[#e6ede9]">
          Historical river blockage investigation. {CASE.period}. Status: {CASE.status}
        </p>
        <p className="max-w-3xl rounded-2xl border border-[#d7b56d]/40 bg-[#d7b56d]/10 px-4 py-3 text-sm text-[#f3e2b3]">
          {CASE.warning}
        </p>
        <p className="max-w-3xl text-sm text-[#93a39b]">
          Discovery window W {DISCOVERY.west} / S {DISCOVERY.south} / E {DISCOVERY.east} / N {DISCOVERY.north}. This is a
          discovery area, not a surveyed lake boundary.
        </p>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <article className="rounded-2xl border border-white/10 bg-[#121716] p-5">
          <p className="text-xs uppercase tracking-wide text-[#93a39b]">Research status</p>
          <p className="mt-2">{CASE.status}</p>
        </article>
        <article className="rounded-2xl border border-white/10 bg-[#121716] p-5">
          <p className="text-xs uppercase tracking-wide text-[#93a39b]">Comparability group</p>
          <p className="mt-2">Group D40, provisional CRID P05023</p>
        </article>
        <article className="rounded-2xl border border-white/10 bg-[#121716] p-5">
          <p className="text-xs uppercase tracking-wide text-[#93a39b]">Evidence records</p>
          <p className="mt-2">{EVIDENCE.length} committed records from Missions 003–012</p>
        </article>
      </section>

      <section>
        <h2 className="text-xl font-medium">Investigation activity timeline</h2>
        <ol className="mt-3 space-y-3">
          {ACQUISITIONS.map((a) => (
            <li key={a.iso} className="rounded-2xl border border-white/10 px-4 py-3">
              <p className="font-medium">{a.date}</p>
              <p className="mt-1 font-mono text-xs text-[#c9d5cf] break-all">{a.granule}</p>
              <p className="mt-2 text-sm">
                Raw fully sweep-stable pixels: {a.rawStable}. Filtered fully sweep-stable pixels: {a.filteredStable}.
              </p>
            </li>
          ))}
        </ol>
      </section>

      <section>
        <h2 className="text-xl font-medium">Scientific blockers</h2>
        <ul className="mt-3 space-y-2 text-sm text-[#c9d5cf]">
          {LIMITATIONS.slice(0, 6).map((item) => (
            <li key={item} className="rounded-xl border border-white/10 px-4 py-3">{item}</li>
          ))}
        </ul>
      </section>

      <div className="no-print flex flex-wrap gap-3">
        {links.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className="rounded-full border border-white/15 px-4 py-2 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#d7b56d] first:border-[#d7b56d] first:bg-[#d7b56d] first:text-[#1a1408]"
          >
            {l.label}
          </Link>
        ))}
      </div>
    </div>
  );
}
