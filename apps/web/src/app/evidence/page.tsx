"use client";

import { useMemo, useState } from "react";
import { EVIDENCE, type EvidenceCategory, type EvidenceItem, type EvidenceStatus } from "@/lib/case-data";

const categories: Array<EvidenceCategory | "All"> = ["All", "SAR", "Optical", "Terrain", "Review", "Metadata"];
const statuses: Array<EvidenceStatus | "All"> = ["All", "Observation", "Provisional", "Gap", "Unresolved"];

export default function EvidencePage() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<EvidenceCategory | "All">("All");
  const [status, setStatus] = useState<EvidenceStatus | "All">("All");
  const [open, setOpen] = useState<string | null>(EVIDENCE[0]?.id ?? null);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return EVIDENCE.filter((item) => {
      const haystack = `${item.id} ${item.title} ${item.mission} ${item.summary} ${item.details.join(" ")} ${item.source}`.toLowerCase();
      const matchesQuery = q === "" || haystack.includes(q);
      const matchesCategory = category === "All" || item.category === category;
      const matchesStatus = status === "All" || item.status === status;
      return matchesQuery && matchesCategory && matchesStatus;
    });
  }, [query, category, status]);

  return (
    <div className="space-y-6">
      <div>
        <p className="font-mono text-xs tracking-[0.18em] text-[#d7b56d]">EVIDENCE LEDGER</p>
        <h1 className="mt-2 text-3xl font-semibold">Evidence records</h1>
        <p className="mt-2 max-w-3xl text-sm text-[#c9d5cf]">
          Central investigation record. Values are copied from committed manifests and reports. Numbers are not new measurements.
        </p>
      </div>

      <form className="grid gap-3 md:grid-cols-3" onSubmit={(e) => e.preventDefault()}>
        <label className="text-sm md:col-span-1">
          Search
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="title, source, detail…"
            className="mt-1 w-full rounded-xl border border-white/15 bg-[#101816] px-3 py-2"
          />
        </label>
        <label className="text-sm">
          Category
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value as EvidenceCategory | "All")}
            className="mt-1 w-full rounded-xl border border-white/15 bg-[#101816] px-3 py-2"
          >
            {categories.map((c) => <option key={c}>{c}</option>)}
          </select>
        </label>
        <label className="text-sm">
          Status
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as EvidenceStatus | "All")}
            className="mt-1 w-full rounded-xl border border-white/15 bg-[#101816] px-3 py-2"
          >
            {statuses.map((s) => <option key={s}>{s}</option>)}
          </select>
        </label>
      </form>

      {visible.length === 0 ? (
        <p className="rounded-2xl border border-white/10 px-4 py-6 text-sm">No records match this search.</p>
      ) : null}

      <div className="space-y-3">
        {visible.map((item) => (
          <EvidenceCard key={item.id} item={item} open={open === item.id} onToggle={() => setOpen(open === item.id ? null : item.id)} />
        ))}
      </div>
    </div>
  );
}

function EvidenceCard({ item, open, onToggle }: { item: EvidenceItem; open: boolean; onToggle: () => void }) {
  return (
    <article className="rounded-2xl border border-white/10">
      <button
        type="button"
        className="flex w-full items-start justify-between gap-4 px-4 py-4 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#d7b56d]"
        aria-expanded={open}
        onClick={onToggle}
      >
        <span>
          <span className="block font-medium">{item.title}</span>
          <span className="mt-1 block text-sm text-[#c9d5cf]">{item.summary}</span>
          <span className="mt-2 inline-flex flex-wrap gap-2 text-xs">
            <span className="rounded-full border border-white/15 px-2 py-0.5 font-mono text-[#d7b56d]">Mission {item.mission}</span>
            <span className="rounded-full border border-white/15 px-2 py-0.5">{item.category}</span>
            <span className="rounded-full border border-white/15 px-2 py-0.5">{item.kind}</span>
            <span className="rounded-full border border-white/15 px-2 py-0.5">{item.status}</span>
          </span>
        </span>
        <span className="shrink-0 font-mono text-xs text-[#93a39b]">{item.id}</span>
      </button>
      {open ? (
        <div className="border-t border-white/10 px-4 py-4 text-sm">
          <p className="font-mono text-xs text-[#93a39b]">Source: {item.source}</p>
          {item.date ? <p className="mt-1 text-[#c9d5cf]">Record date: {item.date}.</p> : null}
          <ul className="mt-3 space-y-2 text-[#d7e2dc]">
            {item.details.map((d) => <li key={d}>{d}</li>)}
          </ul>
          <div className="mt-3">
            <p className="text-xs uppercase tracking-wide text-[#93a39b]">Limitations</p>
            <ul className="mt-1 list-disc space-y-1 pl-5 text-[#c9d5cf]">
              {item.limitations.map((l) => <li key={l}>{l}</li>)}
            </ul>
          </div>
        </div>
      ) : null}
    </article>
  );
}
