import Link from "next/link";
import { caseSummary, discovery, evidenceItems, limitations } from "@/lib/evidence";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <section className="rounded-3xl border border-white/10 bg-[#121a17] p-6 md:p-8">
        <p className="font-mono text-xs tracking-[0.2em] text-[#d7b56d]">HISTORICAL CASE</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight md:text-5xl">{caseSummary.title}</h1>
        <p className="mt-2 max-w-2xl text-[#c9d5cf]">{caseSummary.subtitle}</p>
        <p className="mt-6 max-w-3xl text-lg">{caseSummary.caseName}, {discovery.place}. Investigation dates {caseSummary.period}.</p>
        <p className="mt-4 max-w-3xl rounded-2xl border border-[#d7b56d]/40 bg-[#d7b56d]/10 px-4 py-3 text-sm text-[#f3e2b3]">{caseSummary.warning}</p>
      </section>
      <section className="grid gap-4 md:grid-cols-3">
        {[
          ["Research status", caseSummary.status],
          ["Comparability", "Group D40, provisional CRID P05023"],
          ["Evidence quality", "Candidate counts only. No confirmed water."],
        ].map(([label, value]) => (
          <article key={label} className="rounded-2xl border border-white/10 bg-[#101816] p-5">
            <p className="text-xs uppercase tracking-wide text-[#93a39b]">{label}</p>
            <p className="mt-2 text-lg">{value}</p>
          </article>
        ))}
      </section>
      <section className="grid gap-4 md:grid-cols-2">
        {evidenceItems.map((item) => (
          <article key={item.id} className="rounded-2xl border border-white/10 p-5">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-lg font-medium">{item.title}</h2>
              <span className="rounded-full border border-white/15 px-2 py-0.5 font-mono text-xs text-[#d7b56d]">{item.status}</span>
            </div>
            <p className="mt-3 text-sm text-[#d7e2dc]">{item.summary}</p>
          </article>
        ))}
      </section>
      <section>
        <h2 className="text-xl font-medium">Outstanding limitations</h2>
        <ul className="mt-3 space-y-2 text-sm text-[#c9d5cf]">
          {limitations.map((item) => (
            <li key={item} className="rounded-xl border border-white/10 px-4 py-3">{item}</li>
          ))}
        </ul>
        <div className="no-print mt-6 flex flex-wrap gap-3">
          <Link href="/map" className="rounded-full bg-[#d7b56d] px-4 py-2 text-sm font-medium text-[#1a1408]">Open the map</Link>
          <Link href="/evidence" className="rounded-full border border-white/15 px-4 py-2 text-sm">Read the evidence</Link>
        </div>
      </section>
    </div>
  );
}
