"use client";

import { evidenceItems } from "@/lib/evidence";
import { useReview, type ReviewChoice } from "@/lib/review";

const choices: { id: ReviewChoice; label: string }[] = [
  { id: "accept", label: "Accept" },
  { id: "reject", label: "Reject" },
  { id: "needs-investigation", label: "Needs further investigation" },
];

export default function ReviewPage() {
  const { choices: selected, setChoice } = useReview();
  return (
    <div className="space-y-6">
      <div>
        <p className="font-mono text-xs tracking-[0.18em] text-[#d7b56d]">REVIEW WORKFLOW</p>
        <h1 className="mt-2 text-3xl font-semibold">Evidence review</h1>
        <p className="mt-3 rounded-2xl border border-[#d7b56d]/40 bg-[#d7b56d]/10 px-4 py-3 text-sm text-[#f3e2b3]">Prototype interaction only — decisions are not persisted to a backend.</p>
      </div>
      {evidenceItems.map((item) => (
        <article key={item.id} className="rounded-2xl border border-white/10 p-5">
          <h2 className="text-lg font-medium">{item.title}</h2>
          <p className="mt-2 text-sm text-[#c9d5cf]">{item.summary}</p>
          <p className="mt-3 text-sm text-[#d7e2dc]">This record stays unconfirmed. Independent same-date evidence, a resolved orbit label, and a tested terrain geometry are still required before any water claim.</p>
          <div className="mt-4 flex flex-wrap gap-2">
            {choices.map((choice) => (
              <button
                key={choice.id}
                type="button"
                onClick={() => setChoice(item.id, choice.id)}
                className={`rounded-full border px-3 py-1.5 text-sm ${selected[item.id] === choice.id ? "border-[#d7b56d] bg-[#d7b56d] text-[#1a1408]" : "border-white/15 text-[#d7e2dc]"}`}
              >
                {choice.label}
              </button>
            ))}
          </div>
        </article>
      ))}
    </div>
  );
}
