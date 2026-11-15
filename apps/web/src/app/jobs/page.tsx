"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth-context";
import { listJobs, createJob, type ApiJob } from "@/lib/api";

const allowedTaskTypes = [
  { id: "raster.inspect", name: "Raster Inspection (Dimensions, CRS, Bands)" },
  { id: "checksum", name: "Streaming Checksum Verification (SHA-256)" },
  { id: "metadata.manifest", name: "NISAR Metadata Manifest Verification" },
  { id: "water_candidate.check", name: "Water Candidate Evaluation (Vetted Approval Required)" },
];

export default function JobsPage() {
  const { token, currentIncident, user, currentRole } = useAuth();
  const [jobs, setJobs] = useState<ApiJob[]>([]);
  const [loading, setLoading] = useState(false);
  const [showSubmit, setShowSubmit] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  // Form states
  const [jobType, setJobType] = useState("raster.inspect");
  const [inputPath, setInputPath] = useState("data/manifests/mission006_sweep.json");
  const [expectedHash, setExpectedHash] = useState("");
  // Water candidate parameters
  const [thresholdDb, setThresholdDb] = useState("-14.0");
  const [minPixels, setMinPixels] = useState("5");
  const [maxPixels, setMaxPixels] = useState("500");
  const [approvedBy, setApprovedBy] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const fetchJobs = useCallback(async () => {
    if (!token || !currentIncident) {
      setJobs([]);
      return;
    }
    setLoading(true);
    try {
      const data = await listJobs(token, currentIncident.id);
      setJobs(data || []);
      if (data && data.length > 0 && !selectedJobId) {
        setSelectedJobId(data[0].id);
      }
    } finally {
      setLoading(false);
    }
  }, [token, currentIncident, selectedJobId]);

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 6000);
    return () => clearInterval(interval);
  }, [fetchJobs]);

  const handleSubmitJob = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !currentIncident) return;
    setFormError(null);
    setSubmitting(true);

    try {
      const payload: Record<string, unknown> = {
        task_type: jobType,
        path: inputPath,
      };

      if (jobType === "checksum" && expectedHash) {
        payload.expected_sha256 = expectedHash.trim();
      }

      if (jobType === "water_candidate.check") {
        if (!approvedBy.trim()) {
          throw new Error("Water candidate task strictly requires explicit 'approved_by' identity");
        }
        payload.threshold_db = parseFloat(thresholdDb);
        payload.min_pixels = parseInt(minPixels, 10);
        payload.max_pixels = parseInt(maxPixels, 10);
        payload.approved_by = approvedBy.trim();
        payload.approved_at = new Date().toISOString();
      }

      const idempotencyKey = `job-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

      const created = await createJob(token, currentIncident.id, {
        job_type: jobType,
        idempotency_key: idempotencyKey,
        payload,
      });

      await fetchJobs();
      setSelectedJobId(created.id);
      setShowSubmit(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : (err as { message?: string }).message;
      setFormError(msg || "Failed to submit processing job");
    } finally {
      setSubmitting(false);
    }
  };

  const selectedJob = jobs.find((j) => j.id === selectedJobId);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="font-mono text-xs tracking-[0.18em] text-[#d7b56d]">SCIENTIFIC WORKER</p>
          <h1 className="mt-2 text-3xl font-semibold">Processing Jobs & Execution Pipeline</h1>
          <p className="mt-2 max-w-3xl text-sm text-[#c9d5cf]">
            Authorized scientific jobs execute inside isolated Python worker environments. Workers connect via
            Ed25519-signed machine API with atomic leasing (<code>FOR UPDATE SKIP LOCKED</code>).
          </p>
        </div>

        {token && currentIncident && (currentRole === "owner" || currentRole === "analyst") ? (
          <button
            type="button"
            onClick={() => setShowSubmit(!showSubmit)}
            className="rounded-full bg-[#d7b56d] px-4 py-2 text-xs font-semibold text-[#1a1408] transition hover:bg-[#c9a65c]"
          >
            {showSubmit ? "✕ Close Form" : "+ Submit Processing Job"}
          </button>
        ) : null}
      </div>

      {/* Job Submission Form */}
      {showSubmit ? (
        <section className="rounded-3xl border border-[#d7b56d]/40 bg-[#121716] p-6 shadow-xl">
          <h2 className="text-lg font-medium text-white">Submit Authorized Scientific Task</h2>
          <p className="mt-1 text-xs text-[#93a39b]">
            Enqueued to PostgreSQL with atomic worker lease locking for incident: {currentIncident?.title}
          </p>

          {formError ? (
            <div className="mt-3 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-300">
              {formError}
            </div>
          ) : null}

          <form onSubmit={handleSubmitJob} className="mt-4 space-y-4">
            <div>
              <label className="block text-xs font-medium uppercase tracking-wide text-[#93a39b]">
                Scientific Task Type (Allowlisted)
              </label>
              <select
                value={jobType}
                onChange={(e) => setJobType(e.target.value)}
                className="mt-1 w-full rounded-xl border border-white/15 bg-[#101816] px-3.5 py-2 text-sm text-white focus:border-[#d7b56d] focus:outline-none"
              >
                {allowedTaskTypes.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium uppercase tracking-wide text-[#93a39b]">
                Input Target Path
              </label>
              <input
                type="text"
                required
                value={inputPath}
                onChange={(e) => setInputPath(e.target.value)}
                placeholder="data/manifests/mission006_sweep.json"
                className="mt-1 w-full rounded-xl border border-white/15 bg-[#101816] px-3.5 py-2 font-mono text-xs text-white focus:border-[#d7b56d] focus:outline-none"
              />
              <p className="mt-1 text-[11px] text-[#93a39b]">
                Path traversal (<code>..</code>) and arbitrary shell execution are strictly blocked.
              </p>
            </div>

            {jobType === "checksum" ? (
              <div>
                <label className="block text-xs font-medium uppercase tracking-wide text-[#93a39b]">
                  Expected SHA-256 (Optional Verification)
                </label>
                <input
                  type="text"
                  value={expectedHash}
                  onChange={(e) => setExpectedHash(e.target.value)}
                  placeholder="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
                  className="mt-1 w-full rounded-xl border border-white/15 bg-[#101816] px-3.5 py-2 font-mono text-xs text-white focus:border-[#d7b56d] focus:outline-none"
                />
              </div>
            ) : null}

            {jobType === "water_candidate.check" ? (
              <div className="space-y-4 rounded-2xl border border-amber-500/30 bg-amber-500/5 p-4">
                <p className="text-xs font-semibold text-amber-300">
                  Preregistered Approval Parameters (Mandatory for Water Candidate Evaluation)
                </p>
                <div className="grid gap-3 sm:grid-cols-3">
                  <div>
                    <label className="block text-xs text-[#93a39b]">Threshold (dB)</label>
                    <input
                      type="number"
                      step="0.5"
                      required
                      value={thresholdDb}
                      onChange={(e) => setThresholdDb(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-white/15 bg-[#101816] px-3 py-1.5 text-xs text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-[#93a39b]">Min Pixels</label>
                    <input
                      type="number"
                      required
                      value={minPixels}
                      onChange={(e) => setMinPixels(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-white/15 bg-[#101816] px-3 py-1.5 text-xs text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-[#93a39b]">Max Pixels</label>
                    <input
                      type="number"
                      required
                      value={maxPixels}
                      onChange={(e) => setMaxPixels(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-white/15 bg-[#101816] px-3 py-1.5 text-xs text-white"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs text-[#93a39b]">Approved By (Investigator / Reviewer)</label>
                  <input
                    type="text"
                    required
                    value={approvedBy}
                    onChange={(e) => setApprovedBy(e.target.value)}
                    placeholder={user?.email || "reviewer1@example.com"}
                    className="mt-1 w-full rounded-lg border border-white/15 bg-[#101816] px-3 py-1.5 text-xs text-white"
                  />
                </div>
              </div>
            ) : null}

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowSubmit(false)}
                className="rounded-full border border-white/15 px-4 py-1.5 text-xs text-[#c9d5cf]"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="rounded-full bg-[#d7b56d] px-5 py-1.5 text-xs font-semibold text-[#1a1408] transition hover:bg-[#c9a65c] disabled:opacity-50"
              >
                {submitting ? "Enqueueing..." : "Enqueue Job to Worker Queue"}
              </button>
            </div>
          </form>
        </section>
      ) : null}

      {/* Jobs Grid & Details */}
      <section className="grid gap-6 lg:grid-cols-3">
        {/* Jobs List (Left Column) */}
        <div className="space-y-3 lg:col-span-1">
          <div className="flex items-center justify-between pb-1">
            <h2 className="text-base font-medium">Job Queue ({jobs.length})</h2>
            <button
              type="button"
              onClick={fetchJobs}
              className="text-xs text-[#d7b56d] hover:underline"
            >
              Refresh ↻
            </button>
          </div>

          {loading && jobs.length === 0 ? (
            <p className="text-xs text-[#93a39b]">Loading jobs...</p>
          ) : jobs.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-white/15 p-6 text-center text-xs text-[#c9d5cf]">
              No processing jobs found for this incident.
            </div>
          ) : (
            jobs.map((job) => {
              const isSelected = job.id === selectedJobId;
              return (
                <div
                  key={job.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => setSelectedJobId(job.id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") setSelectedJobId(job.id);
                  }}
                  className={`cursor-pointer rounded-2xl border p-4 text-xs transition ${
                    isSelected
                      ? "border-[#d7b56d] bg-[#141d1a]"
                      : "border-white/10 bg-[#121716] hover:border-white/20"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-white">{job.job_type}</span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${
                        job.state === "succeeded"
                          ? "bg-emerald-500/20 text-emerald-300"
                          : job.state === "failed"
                          ? "bg-rose-500/20 text-rose-300"
                          : job.state === "running"
                          ? "bg-sky-500/20 text-sky-300"
                          : job.state === "claimed"
                          ? "bg-purple-500/20 text-purple-300"
                          : "bg-amber-500/20 text-amber-300"
                      }`}
                    >
                      {job.state}
                    </span>
                  </div>

                  <p className="mt-2 font-mono text-[11px] text-[#93a39b]">{job.id.slice(0, 18)}...</p>

                  <div className="mt-2 flex items-center justify-between text-[11px] text-[#556961]">
                    <span>Worker: {job.claimed_by || "unassigned"}</span>
                    <span>{job.created_at ? new Date(job.created_at).toLocaleTimeString() : "-"}</span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Selected Job Details Inspector (Right Column) */}
        <div className="lg:col-span-2">
          {selectedJob ? (
            <div className="space-y-6 rounded-3xl border border-white/10 bg-[#121716] p-6">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4">
                <div>
                  <span className="font-mono text-xs tracking-wider text-[#d7b56d]">TASK DETAILS</span>
                  <h3 className="text-xl font-semibold text-white">{selectedJob.job_type}</h3>
                  <p className="font-mono text-xs text-[#93a39b]">UUID: {selectedJob.id}</p>
                </div>
                <span
                  className={`rounded-full px-3 py-1 text-xs font-semibold uppercase ${
                    selectedJob.state === "succeeded"
                      ? "bg-emerald-500/20 text-emerald-300"
                      : selectedJob.state === "failed"
                      ? "bg-rose-500/20 text-rose-300"
                      : selectedJob.state === "running"
                      ? "bg-sky-500/20 text-sky-300"
                      : "bg-amber-500/20 text-amber-300"
                  }`}
                >
                  {selectedJob.state}
                </span>
              </div>

              {/* Status Pipeline Diagram */}
              <div className="rounded-2xl border border-white/10 bg-[#0e1413] p-4 text-xs">
                <p className="font-semibold text-[#93a39b]">Execution Lifecycle Pipeline</p>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <span className="rounded-md bg-white/10 px-2 py-1 text-white">Queued in DB</span>
                  <span className="text-[#93a39b]">→</span>
                  <span
                    className={`rounded-md px-2 py-1 ${
                      selectedJob.claimed_by ? "bg-purple-500/20 text-purple-300" : "bg-white/5 text-[#556961]"
                    }`}
                  >
                    Claimed by Worker
                  </span>
                  <span className="text-[#93a39b]">→</span>
                  <span
                    className={`rounded-md px-2 py-1 ${
                      selectedJob.state === "running" || selectedJob.state === "succeeded"
                        ? "bg-sky-500/20 text-sky-300"
                        : "bg-white/5 text-[#556961]"
                    }`}
                  >
                    Isolated Execution
                  </span>
                  <span className="text-[#93a39b]">→</span>
                  <span
                    className={`rounded-md px-2 py-1 ${
                      selectedJob.state === "succeeded"
                        ? "bg-emerald-500/20 text-emerald-300"
                        : selectedJob.state === "failed"
                        ? "bg-rose-500/20 text-rose-300"
                        : "bg-white/5 text-[#556961]"
                    }`}
                  >
                    Result Manifest Persisted
                  </span>
                </div>
              </div>

              {/* Envelope Metadata */}
              <div className="grid gap-4 sm:grid-cols-2 text-xs">
                <div>
                  <p className="text-[#93a39b]">Assigned Worker</p>
                  <p className="mt-0.5 font-mono text-white">{selectedJob.claimed_by || "None (Waiting for claim)"}</p>
                </div>
                <div>
                  <p className="text-[#93a39b]">Idempotency Key</p>
                  <p className="mt-0.5 font-mono text-white">{selectedJob.idempotency_key}</p>
                </div>
                <div>
                  <p className="text-[#93a39b]">Created At</p>
                  <p className="mt-0.5 text-white">
                    {selectedJob.created_at ? new Date(selectedJob.created_at).toLocaleString() : "-"}
                  </p>
                </div>
                <div>
                  <p className="text-[#93a39b]">Updated At</p>
                  <p className="mt-0.5 text-white">
                    {selectedJob.updated_at ? new Date(selectedJob.updated_at).toLocaleString() : "-"}
                  </p>
                </div>
              </div>

              {/* Payload Parameters */}
              <div className="space-y-2">
                <p className="text-xs uppercase tracking-wide text-[#93a39b]">Input Payload (JSON)</p>
                <pre className="max-h-40 overflow-auto rounded-xl border border-white/10 bg-[#0c100f] p-3 font-mono text-xs text-[#c9d5cf]">
                  {JSON.stringify(selectedJob.payload || {}, null, 2)}
                </pre>
              </div>

              {/* Persisted Result Manifest */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-xs uppercase tracking-wide text-[#93a39b]">
                    Scientific Result Manifest (Versioned 1.0)
                  </p>
                  {selectedJob.result ? (
                    <span className="font-mono text-[11px] text-emerald-400">✓ Validated Manifest</span>
                  ) : null}
                </div>
                <pre className="max-h-60 overflow-auto rounded-xl border border-white/10 bg-[#0c100f] p-3 font-mono text-xs text-[#d7e2dc]">
                  {selectedJob.result
                    ? JSON.stringify(selectedJob.result, null, 2)
                    : selectedJob.state === "failed"
                    ? "Job failed during execution. See worker logs."
                    : "No result manifest persisted yet. Worker has not completed this task."}
                </pre>
              </div>
            </div>
          ) : (
            <div className="flex h-64 items-center justify-center rounded-3xl border border-white/10 bg-[#121716] text-sm text-[#93a39b]">
              Select a job from the queue to inspect parameters and execution outcome.
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
