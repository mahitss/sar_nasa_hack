"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import {
  listAcquisitions,
  listEvidence,
  listJobs,
  listReports,
  createIncident,
  type ApiAcquisition,
  type ApiEvidence,
  type ApiJob,
  type ApiReport,
} from "@/lib/api";
import { CASE, DISCOVERY, ACQUISITIONS } from "@/lib/case-data";
import { FIFTY_EVIDENCE_RECORDS } from "@/lib/evidence-50";
import { SCIENTIFIC_JOBS } from "@/lib/jobs-data";

export default function OverviewPage() {
  const { user, token, currentIncident, setCurrentIncident, refreshIncidents, currentRole, signOut } = useAuth();
  const [acquisitions, setAcquisitions] = useState<ApiAcquisition[]>([]);
  const [evidenceList, setEvidenceList] = useState<ApiEvidence[]>([]);
  const [jobs, setJobs] = useState<ApiJob[]>([]);
  const [reports, setReports] = useState<ApiReport[]>([]);
  const [loading, setLoading] = useState(false);

  // Modal for new incident
  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  useEffect(() => {
    if (!token || !currentIncident) {
      setAcquisitions([]);
      setEvidenceList([]);
      setJobs([]);
      setReports([]);
      return;
    }

    let isMounted = true;
    setLoading(true);

    Promise.all([
      listAcquisitions(token, currentIncident.id).catch(() => []),
      listEvidence(token, currentIncident.id).catch(() => []),
      listJobs(token, currentIncident.id).catch(() => []),
      listReports(token, currentIncident.id).catch(() => []),
    ])
      .then(([acqs, evs, jbs, reps]) => {
        if (!isMounted) return;
        setAcquisitions(acqs || []);
        setEvidenceList(evs || []);
        setJobs(jbs || []);
        setReports(reps || []);
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [token, currentIncident]);

  const handleCreateIncident = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !newTitle.trim()) return;
    setCreateLoading(true);
    setCreateError(null);

    try {
      const inc = await createIncident(token, {
        title: newTitle.trim(),
        description: newDescription.trim() || undefined,
      });
      await refreshIncidents();
      setCurrentIncident(inc);
      setShowCreate(false);
      setNewTitle("");
      setNewDescription("");
    } catch (err: unknown) {
      const apiErr = err as { message?: string };
      setCreateError(apiErr.message || "Failed to create incident workspace");
    } finally {
      setCreateLoading(false);
    }
  };

  const displayAcqCount = acquisitions.length > 0 ? acquisitions.length : ACQUISITIONS.length;
  const displayEvidenceCount = evidenceList.length > 0 ? evidenceList.length : FIFTY_EVIDENCE_RECORDS.length;
  const displayJobsCount = jobs.length > 0 ? jobs.length : SCIENTIFIC_JOBS.length;

  return (
    <div className="space-y-20 pb-24 text-[#fcfaf5]">
      {/* Discreet Brand & Sign-In Header for Landing Page */}
      <div className="flex items-center justify-between pb-4 border-b border-white/10">
        <div className="flex items-center gap-3">
          <span className="font-mono text-base font-bold tracking-[0.24em] text-[#d7b56d]">RIVET</span>
          <span className="hidden text-xs text-[#8fa79b] sm:inline">NASA SAR Investigation</span>
        </div>
        <div className="flex items-center gap-3 text-xs">
          {user ? (
            <div className="flex items-center gap-3">
              <span className="hidden font-mono text-[#a3b8ad] sm:inline">{user.email}</span>
              <button
                type="button"
                onClick={signOut}
                className="rounded-full border border-white/20 px-3.5 py-1 text-xs text-[#c9d5cf] transition hover:text-white"
              >
                Sign Out
              </button>
            </div>
          ) : (
            <Link
              href="/login"
              className="rounded-full bg-[#fcfaf5] px-4 py-1.5 font-medium text-[#07140e] transition hover:bg-[#eae4d5]"
            >
              Sign In
            </Link>
          )}
        </div>
      </div>

      {/* 1. HERO SECTION — Split Editorial Layout (Water & Lake Image Visible Immediately Above the Fold) */}
      <section className="grid gap-10 lg:grid-cols-12 lg:items-center">
        {/* Left Column: Clean Typography & Telemetry */}
        <div className="space-y-6 lg:col-span-7">
          <div className="flex flex-wrap items-center gap-2.5 text-xs font-mono tracking-wider">
            <span className="text-[#a7f3d0] font-semibold">● NASA NISAR OBSERVATION</span>
            <span className="text-[#8e9f95]">/</span>
            <span className="text-[#d7b56d]">HIMALAYAN FLUVIAL INVESTIGATION</span>
            <span className="text-[#8e9f95]">/</span>
            <span className="text-[#c4beaf]">UTTARAKHAND</span>
          </div>

          <h1 className="text-3xl font-light tracking-tight text-[#fcfaf5] sm:text-5xl lg:text-6xl leading-[1.1]">
            Monitoring water, lakes, and mountain river dynamics.
          </h1>

          <p className="max-w-xl text-base sm:text-lg font-normal leading-relaxed text-[#ded8cb]">
            An open, evidence-grounded satellite radar investigation of the reported landslide dam
            along the Kuwari River in the high-relief Himalayan gorge of Bageshwar.
          </p>

          {/* Action Pills */}
          <div className="flex flex-wrap items-center gap-3 text-xs sm:text-sm pt-1">
            <Link
              href="/spatial"
              className="rounded-full bg-[#fcfaf5] px-5 py-2 font-medium text-[#07140e] transition hover:bg-[#eae4d5]"
            >
              Open Spatial Map
            </Link>
            <Link
              href="/acquisitions"
              className="rounded-full border border-white/20 px-4 py-2 text-[#fcfaf5] transition hover:border-[#d7b56d] hover:text-[#d7b56d]"
            >
              Compare Satellite Radar
            </Link>
            <Link
              href="/evidence"
              className="rounded-full border border-white/20 px-4 py-2 text-[#fcfaf5] transition hover:border-[#d7b56d] hover:text-[#d7b56d]"
            >
              50 Evidence Records
            </Link>
            {user && (currentRole === "owner" || currentRole === "analyst") ? (
              <button
                type="button"
                onClick={() => setShowCreate(true)}
                className="rounded-full border border-[#d7b56d]/50 bg-[#d7b56d]/10 px-4 py-2 text-xs font-medium text-[#f8ebd0] transition hover:bg-[#d7b56d]/20"
              >
                + New Workspace
              </button>
            ) : null}
          </div>

          {/* Evenly Spread Telemetry */}
          <div className="grid grid-cols-4 gap-4 border-t border-white/10 pt-6">
            <div>
              <p className="font-mono text-2xl sm:text-3xl font-light text-[#fcfaf5]">{displayAcqCount}</p>
              <p className="mt-0.5 text-[11px] text-[#a3b8ad] uppercase tracking-wider">NISAR Passes</p>
              <p className="text-[10px] text-[#7d9387]">40 MHz Dual-Pol</p>
            </div>
            <div>
              <p className="font-mono text-2xl sm:text-3xl font-light text-[#fcfaf5]">{displayEvidenceCount}</p>
              <p className="mt-0.5 text-[11px] text-[#a3b8ad] uppercase tracking-wider">Evidence Records</p>
              <p className="text-[10px] text-[#7d9387]">Peer reviewed</p>
            </div>
            <div>
              <p className="font-mono text-2xl sm:text-3xl font-light text-[#fcfaf5]">{displayJobsCount}</p>
              <p className="mt-0.5 text-[11px] text-[#a3b8ad] uppercase tracking-wider">Specialist Roles</p>
              <p className="text-[10px] text-[#7d9387]">JPL & ISRO</p>
            </div>
            <div>
              <p className="font-mono text-2xl sm:text-3xl font-light text-[#fcfaf5]">2,450 m</p>
              <p className="mt-0.5 text-[11px] text-[#a3b8ad] uppercase tracking-wider">Valley Elev</p>
              <p className="text-[10px] text-[#7d9387]">WGS 84</p>
            </div>
          </div>
        </div>

        {/* Right Column: Hero Alpine Lake & Mountain Water Image (INSTANTLY VISIBLE ON SCREEN) */}
        <div className="lg:col-span-5">
          <div className="relative overflow-hidden rounded-3xl bg-[#0a1711] shadow-2xl border border-white/10 group">
            <img
              src="/images/lake-2.jpg"
              alt="Himalayan alpine lake and mountain water"
              className="h-80 sm:h-[26rem] w-full object-cover object-center filter brightness-[0.92] transition duration-700 group-hover:scale-105"
            />
            {/* Subtle floating badge on the image */}
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/20" />
            <div className="absolute top-4 right-4">
              <span className="rounded-full bg-black/60 px-3 py-1 font-mono text-[11px] text-[#a7f3d0] backdrop-blur-md border border-white/10">
                Live Catchment Context
              </span>
            </div>
            <div className="absolute bottom-5 left-5 right-5 text-xs">
              <h3 className="text-base font-medium text-white">
                Himalayan Glacial Catchment & Alpine Waters
              </h3>
              <p className="mt-1 text-xs text-[#ded8cb] leading-relaxed">
                Pristine mountain reservoirs and active drainages monitored via satellite synthetic aperture radar.
              </p>
              <div className="mt-2.5 flex items-center justify-between font-mono text-[10px] text-[#d7b56d] border-t border-white/15 pt-2">
                <span>Elevation: 2,450 m</span>
                <span>Bageshwar, Uttarakhand</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. EDITORIAL STORY SECTION: THE WATER QUESTION WITH RIVER GORGE PHOTO */}
      <section className="grid gap-12 lg:grid-cols-12 lg:items-center border-t border-white/10 pt-16">
        <div className="space-y-6 lg:col-span-6">
          <p className="font-mono text-xs uppercase tracking-widest text-[#d7b56d]">
            RESEARCH FOCUS · WATER VERIFICATION
          </p>
          <h2 className="text-3xl sm:text-4xl font-light leading-tight text-[#fcfaf5]">
            Is there an impounded lake behind the Kuwari debris?
          </h2>
          <div className="space-y-4 text-base leading-relaxed text-[#c4beaf]">
            <p>
              In September 2026, initial regional sensors flagged potential water candidates along the Kuwari River gorge.
              In mountainous terrain, steep topography and narrow canyon geometry frequently create false positives in automated algorithms.
            </p>
            <p>
              Using dual-polarization NASA-ISRO Synthetic Aperture Radar (NISAR L-band, 40 MHz) coupled with high-resolution DEM modeling,
              our investigation evaluated 1,092 parameter configurations across two orbital passes.
            </p>
            <p className="text-[#a7f3d0] font-medium">
              Conclusion: 0 pixels remained stable water candidates after temporal cross-filtering.
              The Kuwari River continues to flow freely through a 34 m constriction throat with no confirmed impounded lake.
            </p>
          </div>

          <div className="pt-2 flex items-center gap-6 text-sm">
            <Link
              href="/spatial"
              className="text-[#d7b56d] hover:text-[#f8ebd0] font-medium flex items-center gap-1.5 transition"
            >
              <span>Inspect coordinates on interactive map</span>
              <span>→</span>
            </Link>
          </div>
        </div>

        {/* River Gorge Local Image */}
        <div className="lg:col-span-6 overflow-hidden rounded-3xl bg-[#091811] border border-white/10 shadow-2xl">
          <div className="relative h-80 sm:h-96 w-full">
            <img
              src="/images/river-1.jpg"
              alt="Himalayan mountain river carving through steep valley"
              className="h-full w-full object-cover object-center filter brightness-[0.88]"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-[#06110c]/80 via-transparent to-transparent" />
            <div className="absolute bottom-4 left-4 right-4 text-xs font-mono text-[#d7b56d]">
              Kuwari Fluvial Gorge Corridor · Active Incision & Rapid Discharge
            </div>
          </div>
        </div>
      </section>

      {/* 3. THREE EVENLY SPREAD PILLARS (NO BOXES, JUST CLEAN TEXT) */}
      <section className="border-t border-white/10 pt-16">
        <div className="max-w-2xl">
          <p className="font-mono text-xs uppercase tracking-widest text-[#d7b56d]">
            SCIENTIFIC STANDARDS
          </p>
          <h2 className="mt-2 text-3xl font-light text-[#fcfaf5]">
            How RIVET handles satellite observations.
          </h2>
        </div>

        <div className="mt-12 grid gap-12 sm:grid-cols-3">
          <div className="space-y-3">
            <p className="font-mono text-sm font-semibold text-[#a7f3d0]">01 / Satellite Geometry</p>
            <h3 className="text-xl font-normal text-[#fcfaf5]">Radar Shadow vs. Water</h3>
            <p className="text-sm leading-relaxed text-[#c4beaf]">
              Left-looking descending radar passes create terrain shadows behind west-facing ridges.
              These shadows mimic low radar backscatter values of flat water bodies. RIVET strictly differentiates
              specular water returns from geometric radar shadows.
            </p>
          </div>

          <div className="space-y-3">
            <p className="font-mono text-sm font-semibold text-[#a7f3d0]">02 / Strict Provenance</p>
            <h3 className="text-xl font-normal text-[#fcfaf5]">No Mixed Release IDs</h3>
            <p className="text-sm leading-relaxed text-[#c4beaf]">
              Comparability groups strictly match track, frame, polarization, and Composite Release ID (CRID).
              Provisional P05023 products are never mixed with non-comparable P05036 releases or differing bandwidth modes.
            </p>
          </div>

          <div className="space-y-3">
            <p className="font-mono text-sm font-semibold text-[#a7f3d0]">03 / Mask Integrity</p>
            <h3 className="text-xl font-normal text-[#fcfaf5]">Subswath Validity Masks</h3>
            <p className="text-sm leading-relaxed text-[#c4beaf]">
              GSLC native-grid subswath validity masks indicate valid sampling regions, not water or layover classifications.
              Every claim is tagged with its explicit uncertainty and reproducible manifest path.
            </p>
          </div>
        </div>
      </section>

      {/* 4. VISUAL GALLERY: LAKES & MOUNTAIN RIVERS GALLERY */}
      <section className="space-y-6 border-t border-white/10 pt-16">
        <div className="flex flex-wrap items-baseline justify-between gap-4">
          <div>
            <p className="font-mono text-xs uppercase tracking-widest text-[#d7b56d]">IMAGE GALLERY</p>
            <h2 className="mt-1 text-2xl sm:text-3xl font-light text-[#fcfaf5]">
              Alpine lakes, river channels, and watershed topography.
            </h2>
          </div>
          <p className="text-xs text-[#a3b8ad] font-mono">High-Relief Fluvial Basins</p>
        </div>

        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {/* Lake 1 */}
          <div className="group space-y-2">
            <div className="overflow-hidden rounded-2xl bg-[#091811] border border-white/10">
              <img
                src="/images/water-2.jpg"
                alt="Turquoise high altitude alpine lake"
                className="h-64 w-full object-cover transition duration-500 group-hover:scale-105 filter brightness-90"
              />
            </div>
            <p className="text-sm font-medium text-[#fcfaf5]">Glacial Lake Baselines</p>
            <p className="text-xs text-[#8fa79b]">
              High-altitude glacial tarns exhibit characteristic specular radar reflection when calm.
            </p>
          </div>

          {/* Lake 2 */}
          <div className="group space-y-2">
            <div className="overflow-hidden rounded-2xl bg-[#091811] border border-white/10">
              <img
                src="/images/lake-3.jpg"
                alt="River canyon winding through green mountain slopes"
                className="h-64 w-full object-cover transition duration-500 group-hover:scale-105 filter brightness-90"
              />
            </div>
            <p className="text-sm font-medium text-[#fcfaf5]">Narrow River Canyons</p>
            <p className="text-xs text-[#8fa79b]">
              Kuwari river channel width narrows to 34 meters at the rock avalanche constriction toe.
            </p>
          </div>

          {/* Lake 3 */}
          <div className="group space-y-2">
            <div className="overflow-hidden rounded-2xl bg-[#091811] border border-white/10">
              <img
                src="/images/lake-1.jpg"
                alt="Alpine mountain peaks with clear lake and blue skies"
                className="h-64 w-full object-cover transition duration-500 group-hover:scale-105 filter brightness-90"
              />
            </div>
            <p className="text-sm font-medium text-[#fcfaf5]">Bageshwar Mountain Catchment</p>
            <p className="text-xs text-[#8fa79b]">
              Surrounding ridge elevations reach 3,680 m, casting steep radar shadow angles.
            </p>
          </div>
        </div>
      </section>

      {/* 5. PRIMARY SATELLITE RADAR SENSING (REAL NISAR RADAR IMAGES) */}
      <section className="space-y-6 border-t border-white/10 pt-16">
        <div className="flex flex-wrap items-baseline justify-between gap-4">
          <div>
            <p className="font-mono text-xs uppercase tracking-widest text-[#d7b56d]">PRIMARY SATELLITE OBSERVATIONS</p>
            <h2 className="mt-1 text-2xl sm:text-3xl font-light text-[#fcfaf5]">
              NISAR Polarimetric SAR Radar Diagnostics (Sept 6 vs Sept 30)
            </h2>
          </div>
          <Link
            href="/acquisitions"
            className="text-xs font-mono text-[#d7b56d] hover:underline"
          >
            Open Acquisition Comparison →
          </Link>
        </div>

        <div className="grid gap-6 sm:grid-cols-2">
          <div className="space-y-2">
            <div className="overflow-hidden rounded-2xl border border-white/10 bg-[#091811]">
              <img
                src="/images/radar-sept06.png"
                alt="NISAR 6 September 2026 Radar Observation"
                className="h-72 w-full object-cover filter contrast-125"
              />
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="font-mono text-[#fcfaf5]">6 September 2026 Pass</span>
              <span className="text-[#a7f3d0]">6 Raw Candidate Pixels</span>
            </div>
            <p className="text-xs text-[#8fa79b]">
              Descending track 5, frame 73. Low-dB returns correlated with steep ridge geometric radar shadows.
            </p>
          </div>

          <div className="space-y-2">
            <div className="overflow-hidden rounded-2xl border border-white/10 bg-[#091811]">
              <img
                src="/images/radar-sept30.png"
                alt="NISAR 30 September 2026 Radar Observation"
                className="h-72 w-full object-cover filter contrast-125"
              />
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="font-mono text-[#fcfaf5]">30 September 2026 Pass</span>
              <span className="text-[#a7f3d0]">12 Raw Candidate Pixels</span>
            </div>
            <p className="text-xs text-[#8fa79b]">
              Repeat orbit pass. Temporal cross-filtering eliminated all 12 pixels; 0 stable candidates confirmed.
            </p>
          </div>
        </div>
      </section>

      {/* 6. CLEAN EDITORIAL NAVIGATION (DIRECT WORKSPACE ACCESS) */}
      <section className="border-t border-white/10 pt-16 space-y-8">
        <div>
          <p className="font-mono text-xs uppercase tracking-widest text-[#d7b56d]">EXPLORE WORKSPACES</p>
          <h2 className="mt-1 text-3xl font-light text-[#fcfaf5]">
            Direct investigation channels.
          </h2>
          <p className="mt-1 text-sm text-[#c4beaf]">
            Select an area of the scientific inquiry to inspect primary satellite data, run AI synthesis, or verify audit logs.
          </p>
        </div>

        <div className="divide-y divide-white/10">
          {/* Link 1 */}
          <Link
            href="/spatial"
            className="group flex flex-col sm:flex-row sm:items-center justify-between py-6 transition hover:text-[#d7b56d]"
          >
            <div className="space-y-1">
              <span className="font-mono text-xs text-[#a7f3d0]">01 / SPATIAL INVESTIGATION</span>
              <h3 className="text-xl font-normal text-white group-hover:text-[#d7b56d] transition">
                Interactive Geospatial Map & Discovery Window
              </h3>
              <p className="text-sm text-[#8fa79b]">
                Inspect verified terrain points, Kuwari throat constriction, and synthesize new coordinates with NASA AI.
              </p>
            </div>
            <span className="mt-3 sm:mt-0 font-mono text-sm text-[#d7b56d] group-hover:translate-x-1 transition-transform">
              Launch Map →
            </span>
          </Link>

          {/* Link 2 */}
          <Link
            href="/acquisitions"
            className="group flex flex-col sm:flex-row sm:items-center justify-between py-6 transition hover:text-[#d7b56d]"
          >
            <div className="space-y-1">
              <span className="font-mono text-xs text-[#a7f3d0]">02 / SATELLITE RADAR REGISTRY</span>
              <h3 className="text-xl font-normal text-white group-hover:text-[#d7b56d] transition">
                NISAR Dual-Pol Backscatter Comparison (6-Sept vs 30-Sept)
              </h3>
              <p className="text-sm text-[#8fa79b]">
                Compare raw candidate pixels (6 raw vs 12 raw) and observe why 0 filtered stable pixels remain.
              </p>
            </div>
            <span className="mt-3 sm:mt-0 font-mono text-sm text-[#d7b56d] group-hover:translate-x-1 transition-transform">
              Compare Passes →
            </span>
          </Link>

          {/* Link 3 */}
          <Link
            href="/evidence"
            className="group flex flex-col sm:flex-row sm:items-center justify-between py-6 transition hover:text-[#d7b56d]"
          >
            <div className="space-y-1">
              <span className="font-mono text-xs text-[#a7f3d0]">03 / EVIDENCE LEDGER</span>
              <h3 className="text-xl font-normal text-white group-hover:text-[#d7b56d] transition">
                50 Benchmark Records & Observation Spectrograms
              </h3>
              <p className="text-sm text-[#8fa79b]">
                Browse the complete scientific record catalog across Missions M001–M012 with interactive observation inspection.
              </p>
            </div>
            <span className="mt-3 sm:mt-0 font-mono text-sm text-[#d7b56d] group-hover:translate-x-1 transition-transform">
              Open Ledger →
            </span>
          </Link>

          {/* Link 4 */}
          <Link
            href="/jobs"
            className="group flex flex-col sm:flex-row sm:items-center justify-between py-6 transition hover:text-[#d7b56d]"
          >
            <div className="space-y-1">
              <span className="font-mono text-xs text-[#a7f3d0]">04 / SCIENTIFIC WORKER JOBS</span>
              <h3 className="text-xl font-normal text-white group-hover:text-[#d7b56d] transition">
                17 Authentic Specialist Roles & Execution Pipeline
              </h3>
              <p className="text-sm text-[#8fa79b]">
                Inspect Python worker execution tasks, cryptographic idempotency keys, and output manifests.
              </p>
            </div>
            <span className="mt-3 sm:mt-0 font-mono text-sm text-[#d7b56d] group-hover:translate-x-1 transition-transform">
              View Worker Jobs →
            </span>
          </Link>

          {/* Link 5 */}
          <Link
            href="/audit"
            className="group flex flex-col sm:flex-row sm:items-center justify-between py-6 transition hover:text-[#d7b56d]"
          >
            <div className="space-y-1">
              <span className="font-mono text-xs text-[#a7f3d0]">05 / IMMUTABLE AUDIT TRAIL</span>
              <h3 className="text-xl font-normal text-white group-hover:text-[#d7b56d] transition">
                PostgreSQL Audit Trail & Tamper Verification
              </h3>
              <p className="text-sm text-[#8fa79b]">
                Cryptographically sealed database audit events with before/after state diffs and trigger verification.
              </p>
            </div>
            <span className="mt-3 sm:mt-0 font-mono text-sm text-[#d7b56d] group-hover:translate-x-1 transition-transform">
              Inspect Audit Log →
            </span>
          </Link>
        </div>
      </section>

      {/* 7. ACTIVE INCIDENT FOOTER STATUS */}
      <section className="border-t border-white/10 pt-8 flex flex-wrap items-center justify-between gap-4 text-xs font-mono text-[#8fa79b]">
        <div className="flex items-center gap-2">
          <span>Active Incident Workspace:</span>
          <strong className="text-white">{currentIncident?.title || CASE.name}</strong>
          <span className="text-[#d7b56d]">({currentRole || "viewer"})</span>
        </div>
        <div>
          <span>Discovery Window: W 79.75°E, S 30.03°N to E 79.87°E, N 30.15°N</span>
        </div>
      </section>

      {/* Create Incident Modal */}
      {showCreate ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-3xl border border-[#d7b56d]/40 bg-[#0c1813] p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <h3 className="text-lg font-bold text-white">Create New Incident Workspace</h3>
              <button
                type="button"
                onClick={() => setShowCreate(false)}
                className="text-xs text-[#93a39b] hover:text-white"
              >
                ✕ Cancel
              </button>
            </div>
            {createError ? (
              <div className="mt-3 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300">
                {createError}
              </div>
            ) : null}
            <form onSubmit={handleCreateIncident} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium uppercase text-[#a3b8ad]">Incident Title</label>
                <input
                  type="text"
                  required
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="Kuwari River Dam Investigation - Sept 2026"
                  className="mt-1 w-full rounded-xl border border-white/15 bg-[#07130e] px-3.5 py-2 text-sm text-white focus:border-[#d7b56d] focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium uppercase text-[#a3b8ad]">Research Objective</label>
                <textarea
                  rows={2}
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  placeholder="Cross-comparability analysis of NISAR provisional GCOV and optical references..."
                  className="mt-1 w-full rounded-xl border border-white/15 bg-[#07130e] px-3.5 py-2 text-sm text-white focus:border-[#d7b56d] focus:outline-none"
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
                  className="rounded-full bg-[#d7b56d] px-5 py-1.5 text-xs font-semibold text-[#1a1408] hover:bg-[#c9a65c]"
                >
                  {createLoading ? "Creating..." : "Create Incident"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
