"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import {
  listEvidence,
  createEvidence,
  listAcquisitions,
  type ApiEvidence,
  type ApiAcquisition,
} from "@/lib/api";
import { EVIDENCE as STATIC_EVIDENCE } from "@/lib/case-data";

const claimLevels = [
  "All",
  "observation",
  "measurement",
  "interpretation",
  "hypothesis",
  "model",
  "gap",
];

const reviewStates = [
  "All",
  "draft",
  "submitted",
  "accepted",
  "rejected",
  "needs_investigation",
];

export default function EvidencePage() {
  const { token, currentIncident, currentRole } = useAuth();
  const [evidenceList, setEvidenceList] = useState<ApiEvidence[]>([]);
  const [acquisitions, setAcquisitions] = useState<ApiAcquisition[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [viewMode, setViewMode] = useState<"ledger" | "lineage">("ledger");

  // Filter states
  const [query, setQuery] = useState("");
  const [claimFilter, setClaimFilter] = useState("All");
  const [reviewFilter, setReviewFilter] = useState("All");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Form states
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [claimLevel, setClaimLevel] = useState("observation");
  const [evidenceKind, setEvidenceKind] = useState("observation");
  const [sourcePath, setSourcePath] = useState("data/manifests/mission006_sweep.json");
  const [acquisitionId, setAcquisitionId] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [formSubmitting, setFormSubmitting] = useState(false);

  const fetchEvidence = useCallback(async () => {
    if (!token || !currentIncident) {
      setEvidenceList([]);
      setAcquisitions([]);
      return;
    }
    setLoading(true);
    try {
      const [evs, acqs] = await Promise.all([
        listEvidence(token, currentIncident.id).catch(() => []),
        listAcquisitions(token, currentIncident.id).catch(() => []),
      ]);
      setEvidenceList(evs || []);
      setAcquisitions(acqs || []);
      if (evs && evs.length > 0 && !selectedId) {
        setSelectedId(evs[0].id);
      }
    } finally {
      setLoading(false);
    }
  }, [token, currentIncident, selectedId]);

  useEffect(() => {
    fetchEvidence();
  }, [fetchEvidence]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !currentIncident) return;
    setFormError(null);
    setFormSubmitting(true);

    try {
      await createEvidence(token, currentIncident.id, {
        title,
        summary,
        claim_level: claimLevel,
        evidence_kind: evidenceKind,
        source_path: sourcePath,
        acquisition_id: acquisitionId || undefined,
      });
      await fetchEvidence();
      setShowAdd(false);
      setTitle("");
      setSummary("");
    } catch (err: unknown) {
      const apiErr = err as { message?: string };
      setFormError(apiErr.message || "Failed to submit evidence");
    } finally {
      setFormSubmitting(false);
    }
  };

  const filteredEvidence = useMemo(() => {
    const q = query.trim().toLowerCase();
    return evidenceList.filter((item) => {
      const haystack = `${item.id} ${item.title} ${item.summary} ${item.source_path} ${item.claim_level} ${item.evidence_kind}`.toLowerCase();
      const matchesQ = q === "" || haystack.includes(q);
      const matchesClaim = claimFilter === "All" || item.claim_level === claimFilter;
      const matchesReview = reviewFilter === "All" || item.review_state === reviewFilter;
      return matchesQ && matchesClaim && matchesReview;
    });
  }, [evidenceList, query, claimFilter, reviewFilter]);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="font-mono text-xs tracking-[0.18em] text-[#d7b56d]">EVIDENCE MANAGEMENT</p>
          <h1 className="mt-2 text-3xl font-semibold">Evidence Ledger & Scientific Lineage</h1>
          <p className="mt-2 max-w-3xl text-sm text-[#c9d5cf]">
            Every scientific record maintains explicit claim level, provenance references, and audit history.
            Human review is strictly enforced; analysts cannot self-approve evidence.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex rounded-xl border border-white/10 p-1 text-xs">
            <button
              type="button"
              onClick={() => setViewMode("ledger")}
              className={`rounded-lg px-3 py-1 font-medium transition ${
                viewMode === "ledger" ? "bg-[#d7b56d] text-[#1a1408]" : "text-[#c9d5cf]"
              }`}
            >
              Ledger View
            </button>
            <button
              type="button"
              onClick={() => setViewMode("lineage")}
              className={`rounded-lg px-3 py-1 font-medium transition ${
                viewMode === "lineage" ? "bg-[#d7b56d] text-[#1a1408]" : "text-[#c9d5cf]"
              }`}
            >
              Lineage Graph
            </button>
          </div>

          {token && currentIncident && (currentRole === "owner" || currentRole === "analyst") ? (
            <button
              type="button"
              onClick={() => setShowAdd(!showAdd)}
              className="rounded-full bg-[#d7b56d] px-4 py-2 text-xs font-semibold text-[#1a1408] transition hover:bg-[#c9a65c]"
            >
              {showAdd ? "✕ Close Form" : "+ Submit Evidence"}
            </button>
          ) : null}
        </div>
      </div>

      {/* Submission Form */}
      {showAdd ? (
        <section className="rounded-3xl border border-[#d7b56d]/40 bg-[#121716] p-6 shadow-xl">
          <h2 className="text-lg font-medium text-white">Register New Evidence Record</h2>
          <p className="mt-1 text-xs text-[#93a39b]">
            Submit a new evidence claim to PostgreSQL for incident: {currentIncident?.title}
          </p>

          {formError ? (
            <div className="mt-3 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-300">
              {formError}
            </div>
          ) : null}

          <form onSubmit={handleCreate} className="mt-4 space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-xs font-medium uppercase tracking-wide text-[#93a39b]">
                  Evidence Title
                </label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="GCOV Backscatter Stability Analysis"
                  className="mt-1 w-full rounded-xl border border-white/15 bg-[#101816] px-3.5 py-2 text-sm text-white focus:border-[#d7b56d] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium uppercase tracking-wide text-[#93a39b]">
                  Claim Level
                </label>
                <select
                  value={claimLevel}
                  onChange={(e) => setClaimLevel(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-white/15 bg-[#101816] px-3.5 py-2 text-sm text-white focus:border-[#d7b56d] focus:outline-none"
                >
                  <option value="observation">Observation (Direct instrument recording)</option>
                  <option value="measurement">Measurement (Derived quantitative metric)</option>
                  <option value="interpretation">Interpretation (Expert hypothesis evaluation)</option>
                  <option value="hypothesis">Hypothesis (Plausible unproven proposal)</option>
                  <option value="model">Model (Simulated or theoretical output)</option>
                  <option value="gap">Knowledge Gap (Missing or unreconciled evidence)</option>
                </select>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-xs font-medium uppercase tracking-wide text-[#93a39b]">
                  Evidence Kind
                </label>
                <select
                  value={evidenceKind}
                  onChange={(e) => setEvidenceKind(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-white/15 bg-[#101816] px-3.5 py-2 text-sm text-white focus:border-[#d7b56d] focus:outline-none"
                >
                  <option value="observation">Observation (Raw satellite / sensor observation)</option>
                  <option value="measurement">Measurement (Derived measurement metric)</option>
                  <option value="interpretation">Interpretation (Expert analysis)</option>
                  <option value="hypothesis">Hypothesis (Plausible proposal)</option>
                  <option value="gap">Gap (Missing or unresolved evidence)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium uppercase tracking-wide text-[#93a39b]">
                  Associated Acquisition (Optional)
                </label>
                <select
                  value={acquisitionId}
                  onChange={(e) => setAcquisitionId(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-white/15 bg-[#101816] px-3.5 py-2 text-sm text-white focus:border-[#d7b56d] focus:outline-none"
                >
                  <option value="">None (Independent record)</option>
                  {acquisitions.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.granule_id.slice(0, 40)}... ({a.crid})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium uppercase tracking-wide text-[#93a39b]">
                Source File / Manifest Path
              </label>
              <input
                type="text"
                required
                value={sourcePath}
                onChange={(e) => setSourcePath(e.target.value)}
                placeholder="data/manifests/mission006_sweep.json"
                className="mt-1 w-full rounded-xl border border-white/15 bg-[#101816] px-3.5 py-2 font-mono text-xs text-white focus:border-[#d7b56d] focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium uppercase tracking-wide text-[#93a39b]">
                Summary & Limitations
              </label>
              <textarea
                rows={3}
                required
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                placeholder="Observed raw backscatter threshold response across 1,092 sweep configurations. 0 pixels remained stable after temporal filtering."
                className="mt-1 w-full rounded-xl border border-white/15 bg-[#101816] px-3.5 py-2 text-sm text-white focus:border-[#d7b56d] focus:outline-none"
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowAdd(false)}
                className="rounded-full border border-white/15 px-4 py-1.5 text-xs text-[#c9d5cf]"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={formSubmitting}
                className="rounded-full bg-[#d7b56d] px-5 py-1.5 text-xs font-semibold text-[#1a1408] transition hover:bg-[#c9a65c] disabled:opacity-50"
              >
                {formSubmitting ? "Submitting..." : "Submit for Institutional Review"}
              </button>
            </div>
          </form>
        </section>
      ) : null}

      {/* Lineage Graph View */}
      {viewMode === "lineage" ? (
        <section className="space-y-4 rounded-3xl border border-white/10 bg-[#121716] p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium text-white">Scientific Lineage & Traceability Graph</h2>
            <span className="text-xs text-[#93a39b]">M023 Provenance Architecture</span>
          </div>

          <div className="overflow-x-auto rounded-2xl border border-white/10 bg-[#0c100f] p-6">
            <div className="min-w-[700px] space-y-6">
              <div className="grid grid-cols-5 gap-3 text-center text-xs font-semibold uppercase tracking-wider text-[#93a39b]">
                <div className="rounded-lg bg-white/5 py-2">1. Source Satellite</div>
                <div className="rounded-lg bg-white/5 py-2">2. Ingest & QA</div>
                <div className="rounded-lg bg-white/5 py-2">3. Processing Run</div>
                <div className="rounded-lg bg-white/5 py-2">4. Derived Evidence</div>
                <div className="rounded-lg bg-white/5 py-2">5. Review Decision</div>
              </div>

              <div className="space-y-4">
                {evidenceList.map((item) => (
                  <div
                    key={item.id}
                    className="grid grid-cols-5 items-center gap-3 rounded-xl border border-white/10 bg-[#141b19] p-3 text-xs"
                  >
                    <div className="space-y-1">
                      <p className="font-semibold text-white">NISAR Group D40</p>
                      <p className="font-mono text-[10px] text-[#d7b56d]">CRID P05023</p>
                    </div>

                    <div className="space-y-1">
                      <p className="text-[#c9d5cf]">Technical QA</p>
                      <p className="font-mono text-[10px] text-emerald-400">PASSED (SHA256)</p>
                    </div>

                    <div className="space-y-1">
                      <p className="text-[#c9d5cf]">Worker Run</p>
                      <p className="font-mono text-[10px] text-[#93a39b]">v1.0 Manifest</p>
                    </div>

                    <div className="space-y-1">
                      <p className="font-medium text-white line-clamp-1">{item.title}</p>
                      <p className="font-mono text-[10px] text-[#d7b56d]">{item.claim_level}</p>
                    </div>

                    <div className="space-y-1 text-center">
                      <span
                        className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${
                          item.review_state === "accepted"
                            ? "bg-emerald-500/20 text-emerald-300"
                            : item.review_state === "rejected"
                            ? "bg-rose-500/20 text-rose-300"
                            : "bg-amber-500/20 text-amber-300"
                        }`}
                      >
                        {item.review_state}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      ) : null}

      {/* Filters */}
      <div className="grid gap-3 sm:grid-cols-3">
        <label className="text-xs text-[#93a39b]">
          Search Records
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search title, summary, source..."
            className="mt-1 w-full rounded-xl border border-white/15 bg-[#101816] px-3 py-2 text-sm text-white placeholder-[#556961] focus:border-[#d7b56d] focus:outline-none"
          />
        </label>

        <label className="text-xs text-[#93a39b]">
          Claim Level
          <select
            value={claimFilter}
            onChange={(e) => setClaimFilter(e.target.value)}
            className="mt-1 w-full rounded-xl border border-white/15 bg-[#101816] px-3 py-2 text-sm text-white focus:border-[#d7b56d] focus:outline-none"
          >
            {claimLevels.map((lvl) => (
              <option key={lvl} value={lvl}>
                {lvl}
              </option>
            ))}
          </select>
        </label>

        <label className="text-xs text-[#93a39b]">
          Review State
          <select
            value={reviewFilter}
            onChange={(e) => setReviewFilter(e.target.value)}
            className="mt-1 w-full rounded-xl border border-white/15 bg-[#101816] px-3 py-2 text-sm text-white focus:border-[#d7b56d] focus:outline-none"
          >
            {reviewStates.map((st) => (
              <option key={st} value={st}>
                {st}
              </option>
            ))}
          </select>
        </label>
      </div>

      {/* Persisted Records List */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-medium">
            Persisted Incident Evidence ({filteredEvidence.length})
          </h2>
          {currentIncident ? (
            <span className="font-mono text-xs text-[#93a39b]">
              Incident: {currentIncident.title}
            </span>
          ) : null}
        </div>

        {loading ? (
          <p className="text-sm text-[#93a39b]">Loading evidence from PostgreSQL...</p>
        ) : filteredEvidence.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-white/15 p-6 text-center text-sm text-[#c9d5cf]">
            No persisted evidence records match the current filters.
          </div>
        ) : (
          <div className="space-y-3">
            {filteredEvidence.map((item) => {
              const isSelected = item.id === selectedId;
              return (
                <article
                  key={item.id}
                  className={`rounded-2xl border transition ${
                    isSelected
                      ? "border-[#d7b56d] bg-[#141d1a]"
                      : "border-white/10 bg-[#121716] hover:border-white/20"
                  }`}
                >
                  <div
                    role="button"
                    tabIndex={0}
                    onClick={() => setSelectedId(isSelected ? null : item.id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        setSelectedId(isSelected ? null : item.id);
                      }
                    }}
                    className="flex w-full cursor-pointer items-start justify-between gap-4 p-5 text-left"
                  >
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold text-white">{item.title}</span>
                        <span className="rounded-full border border-[#d7b56d]/30 bg-[#d7b56d]/10 px-2.5 py-0.5 font-mono text-[11px] text-[#f3e2b3]">
                          {item.claim_level}
                        </span>
                        <span className="rounded-full border border-white/15 px-2 py-0.5 text-[11px] text-[#c9d5cf]">
                          {item.evidence_kind}
                        </span>
                        <span
                          className={`rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase ${
                            item.review_state === "accepted"
                              ? "bg-emerald-500/20 text-emerald-300"
                              : item.review_state === "rejected"
                              ? "bg-rose-500/20 text-rose-300"
                              : "bg-amber-500/20 text-amber-300"
                          }`}
                        >
                          {item.review_state}
                        </span>
                      </div>
                      <p className="mt-2 text-sm text-[#c9d5cf]">{item.summary}</p>
                    </div>

                    <span className="shrink-0 font-mono text-xs text-[#93a39b]">
                      {item.id.slice(0, 8)}
                    </span>
                  </div>

                  {isSelected ? (
                    <div className="border-t border-white/10 bg-[#0e1413] p-5 text-xs">
                      <div className="grid gap-3 sm:grid-cols-2">
                        <div>
                          <p className="text-[#93a39b]">Source Manifest / File</p>
                          <p className="mt-0.5 font-mono text-white">{item.source_path}</p>
                        </div>
                        <div>
                          <p className="text-[#93a39b]">Created By (UUID)</p>
                          <p className="mt-0.5 font-mono text-white">{item.created_by}</p>
                        </div>
                        <div>
                          <p className="text-[#93a39b]">Acquisition ID</p>
                          <p className="mt-0.5 font-mono text-[#d7b56d]">
                            {item.acquisition_id || "None attached"}
                          </p>
                        </div>
                        <div>
                          <p className="text-[#93a39b]">Created At</p>
                          <p className="mt-0.5 text-white">
                            {new Date(item.created_at).toLocaleString()}
                          </p>
                        </div>
                      </div>

                      <div className="mt-4 flex items-center justify-between border-t border-white/10 pt-3">
                        <span className="text-[#93a39b]">
                          Review state transitions require institutional review decision RPC.
                        </span>
                        <Link
                          href="/reviews"
                          className="rounded-full border border-[#d7b56d] px-3.5 py-1 text-xs font-semibold text-[#f3e2b3] hover:bg-[#d7b56d]/10"
                        >
                          Open Review Workspace →
                        </Link>
                      </div>
                    </div>
                  ) : null}
                </article>
              );
            })}
          </div>
        )}
      </section>

      {/* Historical Committed Records Reference */}
      <section className="space-y-4">
        <h2 className="text-xl font-medium">Committed Research Evidence Reference (M003–M012)</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {STATIC_EVIDENCE.slice(0, 6).map((item) => (
            <div key={item.id} className="rounded-2xl border border-white/10 bg-[#121716] p-4 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[#d7b56d]">Mission {item.mission}</span>
                <span className="rounded-full border border-white/15 px-2 py-0.5 text-[10px]">
                  {item.status}
                </span>
              </div>
              <p className="mt-2 font-medium text-white">{item.title}</p>
              <p className="mt-1 text-[#93a39b] line-clamp-2">{item.summary}</p>
              <p className="mt-2 font-mono text-[10px] text-[#556961]">{item.source}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
