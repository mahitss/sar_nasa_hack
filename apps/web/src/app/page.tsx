"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import {
  createIncident,
  listAcquisitions,
  listEvidence,
  listJobs,
  listReports,
  type ApiAcquisition,
  type ApiEvidence,
  type ApiJob,
  type ApiReport,
} from "@/lib/api";
import { CASE, DISCOVERY, ACQUISITIONS, LIMITATIONS } from "@/lib/case-data";

export default function OverviewPage() {
  const { user, token, currentIncident, setCurrentIncident, refreshIncidents, currentRole } = useAuth();

  // Real workspace metrics for active incident
  const [acquisitions, setAcquisitions] = useState<ApiAcquisition[]>([]);
  const [evidenceList, setEvidenceList] = useState<ApiEvidence[]>([]);
  const [jobs, setJobs] = useState<ApiJob[]>([]);
  const [reports, setReports] = useState<ApiReport[]>([]);
  const [metricsLoading, setMetricsLoading] = useState(false);

  // New incident modal/form state
  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);
  const [createLoading, setCreateLoading] = useState(false);

  useEffect(() => {
    if (!token || !currentIncident) {
      setAcquisitions([]);
      setEvidenceList([]);
      setJobs([]);
      setReports([]);
      return;
    }
    let cancelled = false;
    setMetricsLoading(true);

    Promise.all([
      listAcquisitions(token, currentIncident.id).catch(() => []),
      listEvidence(token, currentIncident.id).catch(() => []),
      listJobs(token, currentIncident.id).catch(() => []),
      listReports(token, currentIncident.id).catch(() => []),
    ]).then(([acqs, evs, jbs, reps]) => {
      if (!cancelled) {
        setAcquisitions(acqs || []);
        setEvidenceList(evs || []);
        setJobs(jbs || []);
        setReports(reps || []);
        setMetricsLoading(false);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [token, currentIncident]);

  const handleCreateIncident = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setCreateError(null);
    setCreateLoading(true);

    try {
      const created = await createIncident(token, {
        title: newTitle,
        description: newDescription,
        discovery_west: DISCOVERY.west,
        discovery_south: DISCOVERY.south,
        discovery_east: DISCOVERY.east,
        discovery_north: DISCOVERY.north,
      });
      await refreshIncidents();
      setCurrentIncident(created);
      setShowCreate(false);
      setNewTitle("");
      setNewDescription("");
    } catch (err: unknown) {
      const apiErr = err as { message?: string };
      setCreateError(apiErr.message || "Failed to create incident");
    } finally {
      setCreateLoading(false);
    }
  };

  const acceptedEvidenceCount = evidenceList.filter((e) => e.review_state === "accepted").length;
  const pendingReviewCount = evidenceList.filter(
    (e) => e.review_state === "submitted" || e.review_state === "needs_investigation"
  ).length;
  const succeededJobsCount = jobs.filter((j) => j.state === "succeeded").length;
  const failedJobsCount = jobs.filter((j) => j.state === "failed").length;

  return (
    <div className="space-y-10">
      {/* Top Banner / Hero */}
      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="font-mono text-xs tracking-[0.22em] text-[#d7b56d]">RIVET PLATFORM</p>
            <h1 className="mt-1 text-3xl font-semibold tracking-tight md:text-5xl">{CASE.name}</h1>
          </div>
          {user ? (
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setShowCreate(true)}
                className="rounded-full bg-[#d7b56d] px-4 py-2 text-xs font-semibold text-[#1a1408] transition hover:bg-[#c9a65c]"
              >
                + New Incident
              </button>
            </div>
          ) : (
            <Link
              href="/login"
              className="rounded-full bg-[#d7b56d] px-5 py-2 text-sm font-semibold text-[#1a1408] transition hover:bg-[#c9a65c]"
            >
              Sign In to Access Workspace
            </Link>
          )}
        </div>
        <p className="max-w-3xl text-lg text-[#c9d5cf]">{CASE.place}</p>
        <p className="max-w-3xl text-[#e6ede9]">
          Historical river blockage investigation. {CASE.period}. Status: {CASE.status}
        </p>
        <p className="max-w-3xl rounded-2xl border border-[#d7b56d]/40 bg-[#d7b56d]/10 px-4 py-3 text-sm text-[#f3e2b3]">
          {CASE.warning}
        </p>
        <p className="max-w-3xl text-sm text-[#93a39b]">
          Discovery window W {DISCOVERY.west} / S {DISCOVERY.south} / E {DISCOVERY.east} / N {DISCOVERY.north}. This is
          a discovery area, not a surveyed lake boundary.
        </p>
      </section>

      {/* Incident Creation Modal / Inline Form */}
      {showCreate ? (
        <section className="rounded-3xl border border-[#d7b56d]/40 bg-[#121716] p-6 shadow-xl">
          <div className="flex items-center justify-between pb-4">
            <h2 className="text-lg font-medium text-white">Create New Incident Workspace</h2>
            <button
              type="button"
              onClick={() => setShowCreate(false)}
              className="text-xs text-[#93a39b] hover:text-white"
            >
              ✕ Cancel
            </button>
          </div>
          {createError ? (
            <div className="mb-4 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-300">
              {createError}
            </div>
          ) : null}
          <form onSubmit={handleCreateIncident} className="space-y-4">
            <div>
              <label className="block text-xs font-medium uppercase tracking-wide text-[#93a39b]">
                Incident Title
              </label>
              <input
                type="text"
                required
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder="Kuwari River Dam Investigation - Sept 2026"
                className="mt-1 w-full rounded-xl border border-white/15 bg-[#101816] px-3.5 py-2 text-sm text-white focus:border-[#d7b56d] focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium uppercase tracking-wide text-[#93a39b]">
                Description & Research Objective
              </label>
              <textarea
                rows={2}
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                placeholder="Cross-comparability analysis of NISAR provisional GCOV and optical references..."
                className="mt-1 w-full rounded-xl border border-white/15 bg-[#101816] px-3.5 py-2 text-sm text-white focus:border-[#d7b56d] focus:outline-none"
              />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowCreate(false)}
                className="rounded-full border border-white/15 px-4 py-1.5 text-xs text-[#c9d5cf]"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={createLoading}
                className="rounded-full bg-[#d7b56d] px-5 py-1.5 text-xs font-semibold text-[#1a1408] transition hover:bg-[#c9a65c] disabled:opacity-50"
              >
                {createLoading ? "Creating..." : "Create & Initialize Owner"}
              </button>
            </div>
          </form>
        </section>
      ) : null}

      {/* Live Authenticated Workspace Dashboard */}
      {user ? (
        <section className="space-y-6">
          <div className="flex items-center justify-between border-b border-white/10 pb-3">
            <div>
              <h2 className="text-xl font-medium">Incident Workspace</h2>
              <p className="text-xs text-[#93a39b]">
                {currentIncident
                  ? `Active Incident: ${currentIncident.title} (${currentRole || "Member"})`
                  : "No incident selected. Create or select an incident above."}
              </p>
            </div>
            {currentIncident ? (
              <span className="font-mono text-xs text-[#93a39b]">ID: {currentIncident.id}</span>
            ) : null}
          </div>

          {currentIncident ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <article className="rounded-2xl border border-white/10 bg-[#121716] p-5">
                <p className="text-xs uppercase tracking-wide text-[#93a39b]">Acquisitions</p>
                <p className="mt-2 text-2xl font-semibold text-white">
                  {metricsLoading ? "..." : acquisitions.length}
                </p>
                <p className="mt-1 text-xs text-[#c9d5cf]">Registered satellite granules</p>
                <Link href="/acquisitions" className="mt-3 block text-xs text-[#d7b56d] hover:underline">
                  Manage acquisitions →
                </Link>
              </article>

              <article className="rounded-2xl border border-white/10 bg-[#121716] p-5">
                <p className="text-xs uppercase tracking-wide text-[#93a39b]">Evidence Records</p>
                <p className="mt-2 text-2xl font-semibold text-white">
                  {metricsLoading ? "..." : evidenceList.length}
                </p>
                <p className="mt-1 text-xs text-[#c9d5cf]">
                  {acceptedEvidenceCount} accepted, {pendingReviewCount} pending
                </p>
                <Link href="/evidence" className="mt-3 block text-xs text-[#d7b56d] hover:underline">
                  Open evidence ledger →
                </Link>
              </article>

              <article className="rounded-2xl border border-white/10 bg-[#121716] p-5">
                <p className="text-xs uppercase tracking-wide text-[#93a39b]">Processing Jobs</p>
                <p className="mt-2 text-2xl font-semibold text-white">
                  {metricsLoading ? "..." : jobs.length}
                </p>
                <p className="mt-1 text-xs text-[#c9d5cf]">
                  {succeededJobsCount} succeeded, {failedJobsCount} failed
                </p>
                <Link href="/jobs" className="mt-3 block text-xs text-[#d7b56d] hover:underline">
                  View worker jobs →
                </Link>
              </article>

              <article className="rounded-2xl border border-white/10 bg-[#121716] p-5">
                <p className="text-xs uppercase tracking-wide text-[#93a39b]">Reports</p>
                <p className="mt-2 text-2xl font-semibold text-white">
                  {metricsLoading ? "..." : reports.length}
                </p>
                <p className="mt-1 text-xs text-[#c9d5cf]">Persisted investigation reports</p>
                <Link href="/report" className="mt-3 block text-xs text-[#d7b56d] hover:underline">
                  Generate report →
                </Link>
              </article>
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-white/20 p-8 text-center">
              <p className="text-sm text-[#c9d5cf]">You are not currently a member of any active incident.</p>
              <button
                type="button"
                onClick={() => setShowCreate(true)}
                className="mt-3 rounded-full bg-[#d7b56d] px-4 py-2 text-xs font-semibold text-[#1a1408]"
              >
                Create your first incident
              </button>
            </div>
          )}
        </section>
      ) : null}

      {/* Historical Investigation Timeline & Baseline */}
      <section>
        <h2 className="text-xl font-medium">Historical Investigation Reference Pair</h2>
        <p className="text-xs text-[#93a39b]">Group D40, provisional CRID P05023</p>
        <ol className="mt-3 space-y-3">
          {ACQUISITIONS.map((a) => (
            <li key={a.iso} className="rounded-2xl border border-white/10 px-4 py-3">
              <p className="font-medium">{a.date}</p>
              <p className="mt-1 font-mono text-xs text-[#c9d5cf] break-all">{a.granule}</p>
              <p className="mt-2 text-sm text-[#93a39b]">
                Raw sweep-stable pixels: {a.rawStable}. Filtered sweep-stable pixels: {a.filteredStable}. (Algorithmic
                counts under recorded threshold; not verified water detections).
              </p>
            </li>
          ))}
        </ol>
      </section>

      {/* Scientific Limitations & Blockers */}
      <section>
        <h2 className="text-xl font-medium">Scientific Blockers & Provenance Limitations</h2>
        <ul className="mt-3 space-y-2 text-sm text-[#c9d5cf]">
          {LIMITATIONS.slice(0, 6).map((item) => (
            <li key={item} className="rounded-xl border border-white/10 px-4 py-3">
              {item}
            </li>
          ))}
        </ul>
      </section>

      {/* Navigation Quick Links */}
      <div className="no-print flex flex-wrap gap-3">
        <Link
          href="/spatial"
          className="rounded-full border border-[#d7b56d] bg-[#d7b56d] px-4 py-2 text-sm font-semibold text-[#1a1408]"
        >
          Open Spatial Investigation
        </Link>
        <Link
          href="/acquisitions"
          className="rounded-full border border-white/15 px-4 py-2 text-sm text-[#c9d5cf] hover:border-[#d7b56d]"
        >
          Compare Acquisitions
        </Link>
        <Link
          href="/evidence"
          className="rounded-full border border-white/15 px-4 py-2 text-sm text-[#c9d5cf] hover:border-[#d7b56d]"
        >
          Open Evidence Ledger
        </Link>
        <Link
          href="/jobs"
          className="rounded-full border border-white/15 px-4 py-2 text-sm text-[#c9d5cf] hover:border-[#d7b56d]"
        >
          Scientific Worker Jobs
        </Link>
        <Link
          href="/report"
          className="rounded-full border border-white/15 px-4 py-2 text-sm text-[#c9d5cf] hover:border-[#d7b56d]"
        >
          Investigation Report
        </Link>
      </div>
    </div>
  );
}
