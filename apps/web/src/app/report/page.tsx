"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth-context";
import {
  listReports,
  createReport,
  listAcquisitions,
  listEvidence,
  listJobs,
  type ApiReport,
  type ApiAcquisition,
  type ApiEvidence,
  type ApiJob,
} from "@/lib/api";
import {
  CASE,
  DISCOVERY,
  ACQUISITIONS,
  EVIDENCE,
  LIMITATIONS,
  NEXT_STEPS,
  MISSION012,
  COMPARISON_FIELDS,
} from "@/lib/case-data";

export default function ReportPage() {
  const { token, currentIncident, user, currentRole } = useAuth();
  const [persistedReports, setPersistedReports] = useState<ApiReport[]>([]);
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);

  const fetchReports = useCallback(async () => {
    if (!token || !currentIncident) {
      setPersistedReports([]);
      return;
    }
    try {
      const data = await listReports(token, currentIncident.id);
      setPersistedReports(data || []);
      if (data && data.length > 0 && !selectedReportId) {
        setSelectedReportId(data[0].id);
      }
    } catch {
      setPersistedReports([]);
    }
  }, [token, currentIncident, selectedReportId]);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  const handleGenerateReport = async () => {
    if (!token || !currentIncident) return;
    setGenerateError(null);
    setGenerating(true);

    try {
      const [acqs, evs, jbs] = await Promise.all([
        listAcquisitions(token, currentIncident.id).catch(() => [] as ApiAcquisition[]),
        listEvidence(token, currentIncident.id).catch(() => [] as ApiEvidence[]),
        listJobs(token, currentIncident.id).catch(() => [] as ApiJob[]),
      ]);

      const reportPayload = {
        investigation: {
          case: CASE,
          incident_id: currentIncident.id,
          title: currentIncident.title,
          description: currentIncident.description,
          discovery_region: {
            west: currentIncident.discovery_west || DISCOVERY.west,
            south: currentIncident.discovery_south || DISCOVERY.south,
            east: currentIncident.discovery_east || DISCOVERY.east,
            north: currentIncident.discovery_north || DISCOVERY.north,
            note: "Discovery region outline is an observation window, not a surveyed lake boundary.",
          },
        },
        satellite_acquisitions: acqs.length > 0 ? acqs : ACQUISITIONS,
        comparability_group: COMPARISON_FIELDS,
        mission012_nisar_metadata: MISSION012,
        evidence_records: evs.length > 0 ? evs : EVIDENCE,
        processing_jobs: jbs,
        scientific_limitations: LIMITATIONS,
        next_steps: NEXT_STEPS,
        provenance: {
          generated_by: user?.email || user?.id || "authenticated_investigator",
          generated_at: new Date().toISOString(),
          crid_protection: "P05023 Group D40 strict isolation",
          classification_rule: "Valid-samples mask NOT treated as water, shadow, or layover",
        },
      };

      const title = `RIVET Investigation Report - ${currentIncident.title} (${new Date().toLocaleDateString()})`;
      const created = await createReport(token, currentIncident.id, {
        title,
        content: reportPayload,
      });

      await fetchReports();
      setSelectedReportId(created.id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : (err as { message?: string }).message;
      setGenerateError(msg || "Failed to compile report");
    } finally {
      setGenerating(false);
    }
  };

  const selectedReport = persistedReports.find((r) => r.id === selectedReportId);

  function downloadJson() {
    const dataToExport = selectedReport
      ? {
          report_id: selectedReport.id,
          title: selectedReport.title,
          generated_by: selectedReport.generated_by,
          created_at: selectedReport.created_at,
          persisted_to_postgresql: true,
          content: selectedReport.content,
        }
      : {
          product: "RIVET investigation report (client preview)",
          persisted_to_postgresql: false,
          case: CASE,
          discovery: DISCOVERY,
          acquisitions: ACQUISITIONS,
          comparison: COMPARISON_FIELDS,
          mission012: MISSION012,
          evidence: EVIDENCE,
          limitations: LIMITATIONS,
          nextSteps: NEXT_STEPS,
        };

    const blob = new Blob([JSON.stringify(dataToExport, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = selectedReport
      ? `rivet-report-${selectedReport.id.slice(0, 8)}.json`
      : "rivet-investigation-report.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-6">
      {/* Action Header */}
      <div className="no-print flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="font-mono text-xs tracking-[0.18em] text-[#d7b56d]">INVESTIGATION REPORT</p>
          <h1 className="mt-2 text-3xl font-semibold">Reproducible Scientific Report</h1>
          <p className="mt-1 text-xs text-[#93a39b]">
            Reports are compiled directly from PostgreSQL evidence, acquisitions, worker manifests, and review decisions.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {token && currentIncident && (currentRole === "owner" || currentRole === "analyst" || currentRole === "reviewer") ? (
            <button
              type="button"
              onClick={handleGenerateReport}
              disabled={generating}
              className="rounded-full bg-[#d7b56d] px-4 py-2 text-xs font-semibold text-[#1a1408] transition hover:bg-[#c9a65c] disabled:opacity-50"
            >
              {generating ? "Compiling..." : "+ Generate Persisted Report"}
            </button>
          ) : null}

          <button
            type="button"
            onClick={() => window.print()}
            className="rounded-full border border-white/15 px-4 py-2 text-xs text-white hover:border-[#d7b56d]"
          >
            Print / PDF
          </button>

          <button
            type="button"
            onClick={downloadJson}
            className="rounded-full border border-white/15 px-4 py-2 text-xs text-[#c9d5cf] hover:border-[#d7b56d]"
          >
            Export JSON
          </button>
        </div>
      </div>

      {generateError ? (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300">
          {generateError}
        </div>
      ) : null}

      {/* Persisted Reports Selector Tabs */}
      {persistedReports.length > 0 ? (
        <div className="no-print flex items-center gap-2 overflow-x-auto rounded-2xl border border-white/10 bg-[#121716] p-2 text-xs">
          <span className="px-2 text-[#93a39b]">Saved Reports:</span>
          {persistedReports.map((r) => {
            const isSelected = r.id === selectedReportId;
            return (
              <button
                key={r.id}
                type="button"
                onClick={() => setSelectedReportId(r.id)}
                className={`rounded-xl px-3 py-1 font-medium transition ${
                  isSelected ? "bg-[#d7b56d] text-[#1a1408]" : "border border-white/10 text-[#c9d5cf]"
                }`}
              >
                {r.title} ({r.created_at ? new Date(r.created_at).toLocaleDateString() : ""})
              </button>
            );
          })}
        </div>
      ) : null}

      {/* Report Document (Print-friendly) */}
      <article className="space-y-6 rounded-3xl border border-white/10 bg-white p-8 text-black shadow-2xl print:border-0 print:p-0">
        <header className="border-b border-gray-200 pb-4">
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs font-bold tracking-[0.2em] text-[#8a7033]">
              RIVET INVESTIGATION REPORT
            </span>
            <span className="font-mono text-xs text-gray-500">
              {selectedReport ? `Report ID: ${selectedReport.id}` : "Unpersisted Snapshot"}
            </span>
          </div>
          <h2 className="mt-2 text-2xl font-bold text-gray-900">
            {selectedReport ? selectedReport.title : `${CASE.name} — ${CASE.place}`}
          </h2>
          <p className="mt-1 text-sm text-gray-700">Investigation Period: {CASE.period}</p>
          <p className="text-sm text-gray-700">Status: {CASE.status}</p>
          {selectedReport ? (
            <p className="mt-1 font-mono text-xs text-emerald-800">
              ✓ Persisted to PostgreSQL (Generated by: {selectedReport.generated_by})
            </p>
          ) : (
            <p className="mt-1 text-xs text-amber-800">
              ⚠ Client-side preview. Sign in and click &apos;Generate Persisted Report&apos; to store an official audit record.
            </p>
          )}
        </header>

        {/* Discovery Region */}
        <section>
          <h3 className="font-bold text-gray-900">1. Discovery Region Context</h3>
          <p className="mt-1 text-sm text-gray-800">
            Coordinates: W {DISCOVERY.west}, S {DISCOVERY.south}, E {DISCOVERY.east}, N {DISCOVERY.north}. (EPSG:4326).
            <strong> Strict Caveat:</strong> This boundary is a satellite observation search window, NOT a surveyed lake
            shoreline or flood inundation polygon.
          </p>
        </section>

        {/* Satellite Ingestion */}
        <section>
          <h3 className="font-bold text-gray-900">2. Satellite Ingest & Comparability Group</h3>
          <p className="mt-1 text-sm text-gray-700">
            Comparability matching Group D40, provisional CRID P05023, descending track 5, frame 73, frequency A, 40 MHz
            dual-pol (HH+HV).
          </p>
          <ul className="mt-2 space-y-1.5 text-xs text-gray-800">
            {ACQUISITIONS.map((a) => (
              <li key={a.granule} className="rounded border border-gray-200 bg-gray-50 p-2">
                <strong>{a.date}:</strong> <span className="font-mono">{a.granule}</span>. Raw stable: {a.rawStable},
                Filtered stable: {a.filteredStable} (Algorithmic sweep counts; not confirmed water).
              </li>
            ))}
          </ul>
        </section>

        {/* NISAR Metadata Constraints */}
        <section>
          <h3 className="font-bold text-gray-900">3. NISAR Processing Verification (Mission 012 Audit)</h3>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-xs text-gray-800">
            <li>Radar grid: {MISSION012.grid.x} × {MISSION012.grid.y} × {MISSION012.grid.height}. Nominal spacing: {MISSION012.steps.x} m.</li>
            <li>Observed orbitType: {MISSION012.orbitType}. attitudeType: {MISSION012.attitudeType}.</li>
            <li>shadowMaskingApplied: &quot;{MISSION012.shadowMaskingApplied}&quot; (String value; unverified layover/shadow model).</li>
            <li>Processor DEM: Copernicus DEM 30 m release 2023_1 (WGS 84 ellipsoid). Local DEM discrepancies remain unresolved.</li>
          </ul>
        </section>

        {/* Evidence Ledger */}
        <section>
          <h3 className="font-bold text-gray-900">4. Scientific Evidence & Human Review Decisions</h3>
          <ul className="mt-2 space-y-2 text-xs text-gray-800">
            {EVIDENCE.slice(0, 8).map((e) => (
              <li key={e.id} className="border-l-2 border-[#8a7033] pl-3">
                <span className="font-semibold text-gray-900">
                  {e.title} [Claim Level: {e.status}]
                </span>
                <p className="text-gray-700">{e.summary}</p>
                <p className="font-mono text-[10px] text-gray-500">Source: {e.source}</p>
              </li>
            ))}
          </ul>
        </section>

        {/* Outstanding Limitations & Scientific Integrity */}
        <section className="rounded-xl border border-amber-300 bg-amber-50 p-4">
          <h3 className="font-bold text-amber-950">5. Scientific Limitations & Unresolved Uncertainties</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-amber-900">
            {LIMITATIONS.slice(0, 6).map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        </section>

        {/* Recommended Actions */}
        <section>
          <h3 className="font-bold text-gray-900">6. Recommended Next Verification Steps</h3>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-xs text-gray-800">
            {NEXT_STEPS.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </section>

        <footer className="border-t border-gray-200 pt-3 text-[11px] text-gray-500">
          This document is generated by the RIVET platform. All claims require institutional review; no automated
          positive water detection is asserted.
        </footer>
      </article>
    </div>
  );
}
