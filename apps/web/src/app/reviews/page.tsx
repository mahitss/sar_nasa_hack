"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth-context";
import {
  listEvidence,
  createDecision,
  type ApiEvidence,
} from "@/lib/api";

export default function ReviewsPage() {
  const { token, currentIncident, user, currentRole } = useAuth();
  const [evidenceList, setEvidenceList] = useState<ApiEvidence[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null);

  // Decision form states
  const [decision, setDecision] = useState<"accept" | "reject" | "needs_investigation">("accept");
  const [rationale, setRationale] = useState("");
  const [decisionError, setDecisionError] = useState<string | null>(null);
  const [decisionSuccess, setDecisionSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const fetchEvidence = useCallback(async () => {
    if (!token || !currentIncident) {
      setEvidenceList([]);
      return;
    }
    setLoading(true);
    try {
      const data = await listEvidence(token, currentIncident.id);
      setEvidenceList(data || []);
      if (data && data.length > 0 && !selectedEvidenceId) {
        setSelectedEvidenceId(data[0].id);
      }
    } finally {
      setLoading(false);
    }
  }, [token, currentIncident, selectedEvidenceId]);

  useEffect(() => {
    fetchEvidence();
  }, [fetchEvidence]);

  const handleSubmitDecision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !currentIncident || !selectedEvidenceId) return;
    setDecisionError(null);
    setDecisionSuccess(null);
    setSubmitting(true);

    try {
      await createDecision(token, currentIncident.id, selectedEvidenceId, {
        decision,
        rationale: rationale.trim() || undefined,
      });
      setDecisionSuccess(`Decision '${decision}' successfully recorded in PostgreSQL audit history.`);
      setRationale("");
      await fetchEvidence();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : (err as { message?: string }).message;
      setDecisionError(msg || "Failed to submit review decision");
    } finally {
      setSubmitting(false);
    }
  };

  const selectedEvidence = evidenceList.find((e) => e.id === selectedEvidenceId);
  const isCreator = selectedEvidence && user ? selectedEvidence.created_by === user.id : false;
  const isEligibleReviewer = currentRole === "owner" || currentRole === "reviewer";

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="font-mono text-xs tracking-[0.18em] text-[#d7b56d]">INSTITUTIONAL REVIEW</p>
          <h1 className="mt-2 text-3xl font-semibold">Evidence Decisions & Review Workspace</h1>
          <p className="mt-2 max-w-3xl text-sm text-[#c9d5cf]">
            Every scientific claim requires independent review. Analysts cannot self-review their own submissions,
            and decisions are audited immutably via PostgreSQL database functions.
          </p>
        </div>

        <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-[#121716] px-3.5 py-1.5 text-xs">
          <span className="text-[#93a39b]">Your Role:</span>
          <span className="font-semibold text-white uppercase">{currentRole || "Viewer"}</span>
        </div>
      </div>

      {/* Security Notice */}
      <section className="rounded-2xl border border-[#d7b56d]/30 bg-[#d7b56d]/5 p-4 text-xs text-[#f3e2b3]">
        <p className="font-semibold">Review Authorization Rules (PostgreSQL RLS & RPC Enforced):</p>
        <ul className="mt-1 list-disc space-y-1 pl-5 text-[#c9d5cf]">
          <li>Only users with <strong>owner</strong> or <strong>reviewer</strong> roles can submit review decisions.</li>
          <li><strong>Self-Review Rejection:</strong> An investigator cannot review evidence they created, even if they hold a reviewer role.</li>
          <li>Direct mutation of <code>review_state</code> via PATCH or UPDATE is rejected by trigger.</li>
          <li>Every decision creates an immutable entry in <code>public.decisions</code> and triggers an audit event.</li>
        </ul>
      </section>

      {/* Workspace Grid */}
      <section className="grid gap-6 lg:grid-cols-3">
        {/* Evidence Selection List (Left Column) */}
        <div className="space-y-3 lg:col-span-1">
          <div className="flex items-center justify-between pb-1">
            <h2 className="text-base font-medium">Evidence Ledger ({evidenceList.length})</h2>
            <button
              type="button"
              onClick={fetchEvidence}
              className="text-xs text-[#d7b56d] hover:underline"
            >
              Refresh ↻
            </button>
          </div>

          {loading && evidenceList.length === 0 ? (
            <p className="text-xs text-[#93a39b]">Loading evidence...</p>
          ) : evidenceList.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-white/15 p-6 text-center text-xs text-[#c9d5cf]">
              No evidence submitted for this incident yet.
            </div>
          ) : (
            evidenceList.map((ev) => {
              const isSelected = ev.id === selectedEvidenceId;
              return (
                <div
                  key={ev.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => setSelectedEvidenceId(ev.id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") setSelectedEvidenceId(ev.id);
                  }}
                  className={`cursor-pointer rounded-2xl border p-4 text-xs transition ${
                    isSelected
                      ? "border-[#d7b56d] bg-[#141d1a]"
                      : "border-white/10 bg-[#121716] hover:border-white/20"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-white line-clamp-1">{ev.title}</span>
                    <span
                      className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${
                        ev.review_state === "accepted"
                          ? "bg-emerald-500/20 text-emerald-300"
                          : ev.review_state === "rejected"
                          ? "bg-rose-500/20 text-rose-300"
                          : "bg-amber-500/20 text-amber-300"
                      }`}
                    >
                      {ev.review_state}
                    </span>
                  </div>

                  <p className="mt-1 text-[11px] text-[#c9d5cf] line-clamp-2">{ev.summary}</p>

                  <div className="mt-2 flex items-center justify-between text-[10px] text-[#556961]">
                    <span className="font-mono text-[#d7b56d]">{ev.claim_level}</span>
                    <span>{new Date(ev.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Review Form & Inspection (Right Column) */}
        <div className="lg:col-span-2">
          {selectedEvidence ? (
            <div className="space-y-6 rounded-3xl border border-white/10 bg-[#121716] p-6">
              {/* Evidence Details */}
              <div className="border-b border-white/10 pb-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-mono text-xs tracking-wider text-[#d7b56d]">EVIDENCE ITEM</span>
                  <span
                    className={`rounded-full px-3 py-1 text-xs font-semibold uppercase ${
                      selectedEvidence.review_state === "accepted"
                        ? "bg-emerald-500/20 text-emerald-300"
                        : selectedEvidence.review_state === "rejected"
                        ? "bg-rose-500/20 text-rose-300"
                        : "bg-amber-500/20 text-amber-300"
                    }`}
                  >
                    State: {selectedEvidence.review_state}
                  </span>
                </div>
                <h3 className="mt-2 text-xl font-semibold text-white">{selectedEvidence.title}</h3>
                <p className="mt-1 text-xs text-[#c9d5cf]">{selectedEvidence.summary}</p>
              </div>

              <div className="grid gap-3 sm:grid-cols-2 text-xs">
                <div>
                  <p className="text-[#93a39b]">Claim Level</p>
                  <p className="mt-0.5 font-mono text-[#d7b56d] uppercase">{selectedEvidence.claim_level}</p>
                </div>
                <div>
                  <p className="text-[#93a39b]">Evidence Kind</p>
                  <p className="mt-0.5 text-white">{selectedEvidence.evidence_kind}</p>
                </div>
                <div>
                  <p className="text-[#93a39b]">Source Path</p>
                  <p className="mt-0.5 font-mono text-white">{selectedEvidence.source_path}</p>
                </div>
                <div>
                  <p className="text-[#93a39b]">Creator (UUID)</p>
                  <p className="mt-0.5 font-mono text-white">{selectedEvidence.created_by}</p>
                </div>
              </div>

              {/* Reviewer Action Box */}
              <div className="rounded-2xl border border-white/10 bg-[#0c100f] p-5">
                <h4 className="text-sm font-semibold text-white">Record Formal Review Decision</h4>

                {decisionError ? (
                  <div className="mt-3 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300">
                    {decisionError}
                  </div>
                ) : null}

                {decisionSuccess ? (
                  <div className="mt-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-300">
                    {decisionSuccess}
                  </div>
                ) : null}

                {!isEligibleReviewer ? (
                  <p className="mt-3 text-xs text-amber-300">
                    Your current role is <strong>{currentRole || "viewer"}</strong>. Only <strong>owners</strong> and{" "}
                    <strong>reviewers</strong> have permissions to record formal decisions.
                  </p>
                ) : isCreator ? (
                  <div className="mt-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-300">
                    <strong>Self-Review Prohibited:</strong> You are the creator of this evidence record. The database
                    enforces strict conflict-of-interest isolation; an independent reviewer must evaluate this submission.
                  </div>
                ) : (
                  <form onSubmit={handleSubmitDecision} className="mt-4 space-y-4">
                    <div>
                      <label className="block text-xs font-medium uppercase tracking-wide text-[#93a39b]">
                        Decision Verdict
                      </label>
                      <select
                        value={decision}
                        onChange={(e) =>
                          setDecision(e.target.value as "accept" | "reject" | "needs_investigation")
                        }
                        className="mt-1 w-full rounded-xl border border-white/15 bg-[#141b19] px-3.5 py-2 text-sm text-white focus:border-[#d7b56d] focus:outline-none"
                      >
                        <option value="accept">Accept (Evidence validated against methodology)</option>
                        <option value="reject">Reject (Fails provenance or comparability criteria)</option>
                        <option value="needs_investigation">Needs Investigation (Requires independent sources)</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-medium uppercase tracking-wide text-[#93a39b]">
                        Scientific Rationale & Review Findings
                      </label>
                      <textarea
                        rows={3}
                        required
                        value={rationale}
                        onChange={(e) => setRationale(e.target.value)}
                        placeholder="Verified that CRID matches P05023 Group D40 and that the valid-samples mask is not treated as a water classification..."
                        className="mt-1 w-full rounded-xl border border-white/15 bg-[#141b19] px-3.5 py-2 text-xs text-white focus:border-[#d7b56d] focus:outline-none"
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={submitting}
                      className="rounded-full bg-[#d7b56d] px-6 py-2 text-xs font-semibold text-[#1a1408] transition hover:bg-[#c9a65c] disabled:opacity-50"
                    >
                      {submitting ? "Recording..." : "Record Official Review Decision"}
                    </button>
                  </form>
                )}
              </div>
            </div>
          ) : (
            <div className="flex h-64 items-center justify-center rounded-3xl border border-white/10 bg-[#121716] text-sm text-[#93a39b]">
              Select an evidence record from the ledger to inspect and review.
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
