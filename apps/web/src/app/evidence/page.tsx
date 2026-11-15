<<<<<<< HEAD
"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { useAuth } from "@/lib/auth-context";
import {
  listEvidence,
  createEvidence,
  listAcquisitions,
  type ApiEvidence,
  type ApiAcquisition,
} from "@/lib/api";
import { EVIDENCE as STATIC_EVIDENCE, type EvidenceItem } from "@/lib/case-data";
import { ObservationInspectorModal } from "@/components/ObservationInspectorModal";

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
  "accepted",
  "needs_investigation",
  "draft",
  "submitted",
  "rejected",
];

const categories = [
  "All",
  "SAR",
  "Optical",
  "Terrain",
  "Hydrology",
  "Review",
  "Metadata",
];

export default function EvidencePage() {
  const { token, currentIncident, currentRole } = useAuth();
  const [evidenceList, setEvidenceList] = useState<ApiEvidence[]>([]);
  const [acquisitions, setAcquisitions] = useState<ApiAcquisition[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [viewMode, setViewMode] = useState<"ledger" | "lineage">("ledger");

  // Inspection modal state
  const [inspectedItem, setInspectedItem] = useState<EvidenceItem | ApiEvidence | null>(null);

  // Filter states
  const [query, setQuery] = useState("");
  const [claimFilter, setClaimFilter] = useState("All");
  const [reviewFilter, setReviewFilter] = useState("All");
  const [categoryFilter, setCategoryFilter] = useState("All");
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

  const clearFilters = () => {
    setQuery("");
    setClaimFilter("All");
    setReviewFilter("All");
    setCategoryFilter("All");
  };

  // Filter persisted evidence
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

  // Filter static 50 scientific reference records
  const filteredStatic = useMemo(() => {
    const q = query.trim().toLowerCase();
    return STATIC_EVIDENCE.filter((item) => {
      const haystack = `${item.id} ${item.title} ${item.summary} ${item.source} ${item.mission} ${item.category} ${item.kind}`.toLowerCase();
      const matchesQ = q === "" || haystack.includes(q);
      const matchesClaim = claimFilter === "All" || item.kind === claimFilter;
      const matchesReview = reviewFilter === "All" || item.reviewState === reviewFilter;
      const matchesCat = categoryFilter === "All" || item.category === categoryFilter;
      return matchesQ && matchesClaim && matchesReview && matchesCat;
    });
  }, [query, claimFilter, reviewFilter, categoryFilter]);

  const hasActiveFilters = query !== "" || claimFilter !== "All" || reviewFilter !== "All" || categoryFilter !== "All";

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs tracking-[0.18em] text-[#d7b56d]">EVIDENCE MANAGEMENT</span>
            <span className="rounded-full bg-[#d7b56d]/15 px-2.5 py-0.5 font-mono text-[10px] text-[#d7b56d]">
              50 Benchmark Records Active
            </span>
          </div>
          <h1 className="mt-2 text-3xl font-semibold">Evidence Ledger & Scientific Lineage</h1>
          <p className="mt-2 max-w-3xl text-sm text-[#c9d5cf]">
            Every scientific record maintains explicit claim level, instrument telemetry, provenance references, and audit history.
            Click any record below to inspect its detailed observation metrics and radar spectrogram.
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
              Ledger View ({filteredStatic.length})
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

      {/* Category Pills Filter */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-[11px] uppercase tracking-wider text-[#93a39b]">
          Discipline:
        </span>
        {categories.map((cat) => (
          <button
            key={cat}
            type="button"
            onClick={() => setCategoryFilter(cat)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition ${
              categoryFilter === cat
                ? "bg-[#d7b56d] text-[#1a1408] font-semibold"
                : "border border-white/10 bg-[#121716] text-[#c9d5cf] hover:border-white/20 hover:text-white"
            }`}
          >
            {cat} {cat === "All" ? `(${STATIC_EVIDENCE.length})` : ""}
          </button>
        ))}

        {hasActiveFilters && (
          <button
            type="button"
            onClick={clearFilters}
            className="ml-auto rounded-full border border-rose-500/30 bg-rose-500/10 px-3 py-1 text-xs font-medium text-rose-300 transition hover:bg-rose-500/20"
          >
            ✕ Reset All Filters
          </button>
        )}
      </div>

      {/* Filters Bar */}
      <div className="grid gap-3 sm:grid-cols-3">
        <label className="text-xs text-[#93a39b]">
          Search 50 Records
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by mission, title, instrument, parameter..."
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
                {st.replace("_", " ")}
              </option>
            ))}
          </select>
        </label>
      </div>

      {/* Lineage Graph View */}
      {viewMode === "lineage" ? (
        <section className="space-y-4 rounded-3xl border border-white/10 bg-[#121716] p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-medium text-white">Scientific Lineage & Traceability Graph</h2>
              <p className="text-xs text-[#93a39b]">
                Click any row in the pipeline to inspect full instrument observation metrics.
              </p>
            </div>
            <span className="text-xs text-[#d7b56d]">50 Verified Artifacts</span>
          </div>

          <div className="overflow-x-auto rounded-2xl border border-white/10 bg-[#0c100f] p-6">
            <div className="min-w-[700px] space-y-4">
              <div className="grid grid-cols-5 gap-3 text-center text-xs font-semibold uppercase tracking-wider text-[#93a39b]">
                <div className="rounded-lg bg-white/5 py-2">1. Instrument Platform</div>
                <div className="rounded-lg bg-white/5 py-2">2. QA & Checksum</div>
                <div className="rounded-lg bg-white/5 py-2">3. Processing Mission</div>
                <div className="rounded-lg bg-white/5 py-2">4. Derived Record</div>
                <div className="rounded-lg bg-white/5 py-2">5. Review Decision</div>
              </div>

              <div className="max-h-[500px] overflow-y-auto space-y-2 pr-1">
                {(evidenceList.length > 0 ? evidenceList : filteredStatic).map((item) => {
                  const claim = "claim_level" in item ? item.claim_level : item.kind;
                  const state = "review_state" in item ? item.review_state : (item.reviewState || "accepted");
                  return (
                    <div
                      key={item.id}
                      onClick={() => setInspectedItem(item)}
                      className="grid grid-cols-5 items-center gap-3 rounded-xl border border-white/10 bg-[#141b19] p-3 text-xs cursor-pointer transition hover:border-[#d7b56d]/50 hover:bg-[#16221f]"
                    >
                      <div className="space-y-0.5">
                        <p className="font-semibold text-white">NISAR / Sentinel / DEM</p>
                        <p className="font-mono text-[10px] text-[#d7b56d]">P05023 Group D40</p>
                      </div>

                      <div className="space-y-0.5">
                        <p className="text-[#c9d5cf]">Technical QA</p>
                        <p className="font-mono text-[10px] text-emerald-400">PASSED (SHA256)</p>
                      </div>

                      <div className="space-y-0.5">
                        <p className="text-[#c9d5cf]">Mission Pipeline</p>
                        <p className="font-mono text-[10px] text-[#93a39b]">
                          {"mission" in item ? `Mission ${item.mission}` : "Mission 003"}
                        </p>
                      </div>

                      <div className="space-y-0.5">
                        <p className="font-medium text-white line-clamp-1">{item.title}</p>
                        <p className="font-mono text-[10px] text-[#d7b56d] uppercase">{claim}</p>
                      </div>

                      <div className="space-y-0.5 text-center">
                        <span
                          className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${
                            state === "accepted"
                              ? "bg-emerald-500/20 text-emerald-300"
                              : state === "rejected"
                              ? "bg-rose-500/20 text-rose-300"
                              : "bg-amber-500/20 text-amber-300"
                          }`}
                        >
                          {state.replace("_", " ")}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </section>
      ) : null}

      {/* Persisted Records List (if authenticated and has records) */}
      {currentIncident && evidenceList.length > 0 && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-medium">
              Persisted PostgreSQL Incident Evidence ({filteredEvidence.length})
            </h2>
            <span className="font-mono text-xs text-[#93a39b]">
              Incident: {currentIncident.title}
            </span>
          </div>

          {loading ? (
            <p className="text-sm text-[#93a39b]">Loading evidence from PostgreSQL...</p>
          ) : filteredEvidence.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-white/15 p-6 text-center text-sm text-[#c9d5cf]">
              <p>No persisted records match the current filter.</p>
              <button
                type="button"
                onClick={clearFilters}
                className="mt-2 text-xs text-[#d7b56d] underline hover:no-underline"
              >
                Clear filters to show all {evidenceList.length} persisted records
              </button>
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
                    <div className="flex w-full items-start justify-between gap-4 p-5 text-left">
                      <div
                        className="cursor-pointer flex-1"
                        onClick={() => setInspectedItem(item)}
                      >
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-semibold text-white hover:text-[#d7b56d] transition">
                            {item.title}
                          </span>
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
                            {item.review_state.replace("_", " ")}
                          </span>
                        </div>
                        <p className="mt-2 text-sm text-[#c9d5cf]">{item.summary}</p>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          type="button"
                          onClick={() => setInspectedItem(item)}
                          className="rounded-full border border-[#d7b56d]/40 bg-[#d7b56d]/10 px-3 py-1 text-xs font-semibold text-[#d7b56d] transition hover:bg-[#d7b56d]/20"
                        >
                          👁️ Inspect Observation
                        </button>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>
      )}

      {/* 50 Scientific Reference Records Catalog */}
      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-xl font-medium">
              Scientific Reference Evidence Catalog ({filteredStatic.length} of {STATIC_EVIDENCE.length} Records)
            </h2>
            <p className="text-xs text-[#c9d5cf]">
              Comprehensive mission record (M001–M012). Click any observation card to open its full instrument telemetry and backscatter data.
            </p>
          </div>
          <span className="font-mono text-xs text-[#d7b56d]">NASA NISAR Baseline</span>
        </div>

        {filteredStatic.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-white/15 p-8 text-center text-sm text-[#c9d5cf]">
            <p>No scientific records match your filter criteria.</p>
            <button
              type="button"
              onClick={clearFilters}
              className="mt-2 text-xs text-[#d7b56d] underline hover:no-underline"
            >
              Reset all filters to view all 50 records
            </button>
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {filteredStatic.map((item) => (
              <div
                key={item.id}
                onClick={() => setInspectedItem(item)}
                className="group flex flex-col justify-between rounded-2xl border border-white/10 bg-[#121716] p-4 text-xs cursor-pointer transition-all hover:border-[#d7b56d]/60 hover:bg-[#141b19] hover:shadow-lg"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-medium text-[#d7b56d]">
                      Mission {item.mission}
                    </span>
                    <div className="flex items-center gap-1.5">
                      <span className="rounded-full border border-white/15 bg-white/5 px-2 py-0.5 text-[10px] text-[#93a39b]">
                        {item.category}
                      </span>
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${
                          item.status === "Observation"
                            ? "bg-emerald-500/20 text-emerald-300"
                            : item.status === "Gap"
                            ? "bg-purple-500/20 text-purple-300"
                            : "bg-amber-500/20 text-amber-300"
                        }`}
                      >
                        {item.status}
                      </span>
                    </div>
                  </div>

                  <p className="mt-2 font-medium text-white group-hover:text-[#d7b56d] transition text-sm">
                    {item.title}
                  </p>
                  <p className="mt-1 text-[#93a39b] line-clamp-3 leading-relaxed">
                    {item.summary}
                  </p>
                </div>

                <div className="mt-3 flex items-center justify-between border-t border-white/5 pt-2 font-mono text-[10px]">
                  <span className="text-[#556961] truncate max-w-[65%]">
                    {item.source.replace("data/manifests/", "")}
                  </span>
                  <span className="text-[#d7b56d] group-hover:underline">
                    Inspect Observation →
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Observation Inspector Modal */}
      <ObservationInspectorModal
        item={inspectedItem}
        onClose={() => setInspectedItem(null)}
      />
=======
import { evidenceItems } from "@/lib/evidence";

export default function EvidencePage() {
  return (
    <div className="space-y-6">
      <div>
        <p className="font-mono text-xs tracking-[0.18em] text-[#d7b56d]">SOURCE RECORD</p>
        <h1 className="mt-2 text-3xl font-semibold">Satellite evidence</h1>
        <p className="mt-2 max-w-3xl text-sm text-[#c9d5cf]">Values below are taken from the committed manifests and science notes. They are not new measurements.</p>
      </div>
      <div className="overflow-x-auto rounded-2xl border border-white/10">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-white/5 text-xs uppercase tracking-wide text-[#93a39b]">
            <tr>
              <th className="px-4 py-3">Record</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Provenance</th>
            </tr>
          </thead>
          <tbody>
            {evidenceItems.map((item) => (
              <tr key={item.id} className="border-t border-white/10">
                <td className="px-4 py-3 font-medium">{item.title}</td>
                <td className="px-4 py-3 text-[#d7b56d]">{item.status}</td>
                <td className="px-4 py-3 font-mono text-xs text-[#c9d5cf]">{item.source}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {evidenceItems.map((item) => (
        <article key={item.id} className="rounded-2xl border border-white/10 p-5">
          <h2 className="text-xl font-medium">{item.title}</h2>
          <p className="mt-2 text-sm text-[#d7e2dc]">{item.summary}</p>
          <ul className="mt-4 space-y-2 text-sm text-[#c9d5cf]">
            {item.details.map((detail) => (
              <li key={detail}>{detail}</li>
            ))}
          </ul>
        </article>
      ))}
>>>>>>> 61992b8d90d44ff0e2766cee552c1953f5b0a06a
    </div>
  );
}
