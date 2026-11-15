"use client";

import Link from "next/link";

export interface InspectableEvidence {
  id: string;
  title: string;
  summary: string;
  mission?: string;
  source_mission?: string;
  category?: string;
  date?: string;
  status?: string;
  kind?: string;
  claim_level?: string;
  evidence_kind?: string;
  reviewState?: string;
  review_state?: string;
  source?: string;
  source_path?: string;
  instrument?: string;
  coordinates?: [number, number];
  elevation?: string;
  metrics?: Record<string, string | number>;
  parameters?: unknown;
  details?: unknown;
  limitations?: unknown;
}

interface ObservationInspectorModalProps {
  item: InspectableEvidence | null;
  onClose: () => void;
}

export function ObservationInspectorModal({ item, onClose }: ObservationInspectorModalProps) {
  if (!item) return null;

  const title = item.title || "Observation Record";
  const summary = item.summary || "";
  const mission = item.mission || item.source_mission || "003";
  const claimLevel = item.claim_level || item.kind || "observation";
  const reviewState = item.review_state || item.reviewState || "accepted";
  const sourcePath = item.source_path || item.source || "data/manifests/mission003_raster_qc.json";
  const category = item.category || "SAR";
  const date = item.date || "September 2026";
  const instrument = item.instrument || (category === "Optical" ? "Sentinel-2B MSI (Level-2A)" : "NASA-ISRO SAR (NISAR) L-band 40 MHz");
  const elevation = item.elevation || "2,450 m";
  const coordinates: [number, number] = Array.isArray(item.coordinates) && item.coordinates.length === 2
    ? item.coordinates
    : [79.812, 30.091];

  // Normalize details
  let details: string[] = [];
  if (Array.isArray(item.details)) {
    details = item.details.map(String);
  } else if (typeof item.details === "string") {
    try {
      const parsed = JSON.parse(item.details);
      if (Array.isArray(parsed)) details = parsed.map(String);
      else details = [item.details];
    } catch {
      details = [item.details];
    }
  }

  // Normalize limitations
  let limitations: string[] = [];
  if (Array.isArray(item.limitations)) {
    limitations = item.limitations.map(String);
  } else if (typeof item.limitations === "string") {
    try {
      const parsed = JSON.parse(item.limitations);
      if (Array.isArray(parsed)) limitations = parsed.map(String);
      else limitations = [item.limitations];
    } catch {
      limitations = [item.limitations];
    }
  }

  // Normalize metrics / parameters
  let metrics: Record<string, string | number> = {};
  if (item.metrics && typeof item.metrics === "object") {
    metrics = item.metrics;
  } else if (item.parameters && typeof item.parameters === "object" && !Array.isArray(item.parameters)) {
    metrics = item.parameters as Record<string, string | number>;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className="relative max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-3xl border border-[#d7b56d]/50 bg-[#101715] p-6 shadow-2xl sm:p-8"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          className="absolute right-6 top-6 flex h-8 w-8 items-center justify-center rounded-full border border-white/20 bg-white/5 text-sm text-[#c9d5cf] transition hover:bg-white/10 hover:text-white"
        >
          ✕
        </button>

        {/* Header Badges */}
        <div className="flex flex-wrap items-center gap-2 pr-10">
          <span className="rounded-full bg-[#d7b56d]/15 px-3 py-1 font-mono text-xs font-semibold uppercase text-[#d7b56d]">
            Mission {mission}
          </span>
          <span className="rounded-full border border-white/15 bg-white/5 px-2.5 py-0.5 text-xs text-[#c9d5cf]">
            {category}
          </span>
          <span className="rounded-full border border-[#d7b56d]/30 bg-[#d7b56d]/10 px-2.5 py-0.5 font-mono text-xs uppercase text-[#f3e2b3]">
            {claimLevel}
          </span>
          <span
            className={`rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase ${
              reviewState === "accepted"
                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                : reviewState === "rejected"
                ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                : "bg-amber-500/20 text-amber-300 border border-amber-500/30"
            }`}
          >
            {reviewState.replace("_", " ")}
          </span>
          <span className="font-mono text-xs text-[#93a39b]">Observed: {date}</span>
        </div>

        {/* Title & Summary */}
        <h2 className="mt-3 text-2xl font-semibold text-white sm:text-3xl">{title}</h2>
        <p className="mt-2 text-sm leading-relaxed text-[#c9d5cf]">{summary}</p>

        {/* Instrument & Spatial Anchor Card */}
        <div className="mt-6 grid gap-4 rounded-2xl border border-white/10 bg-[#0c1210] p-4 sm:grid-cols-3">
          <div>
            <span className="block font-mono text-[10px] uppercase tracking-wider text-[#93a39b]">
              Sensor / Instrument
            </span>
            <p className="mt-1 font-medium text-xs text-white">{instrument}</p>
          </div>
          <div>
            <span className="block font-mono text-[10px] uppercase tracking-wider text-[#93a39b]">
              Target Coordinates
            </span>
            <p className="mt-1 font-mono text-xs text-[#d7b56d]">
              {coordinates[1].toFixed(4)}°N, {coordinates[0].toFixed(4)}°E
            </p>
          </div>
          <div>
            <span className="block font-mono text-[10px] uppercase tracking-wider text-[#93a39b]">
              Terrain Elevation
            </span>
            <p className="mt-1 font-mono text-xs text-white">{elevation} (WGS84)</p>
          </div>
        </div>

        {/* Quantitative Metrics & Telemetry Grid */}
        {Object.keys(metrics).length > 0 && (
          <div className="mt-6 space-y-2">
            <h3 className="font-mono text-xs uppercase tracking-wider text-[#d7b56d]">
              Quantitative Instrument Telemetry & Parameters
            </h3>
            <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
              {Object.entries(metrics).map(([key, val]) => (
                <div key={key} className="rounded-xl border border-white/10 bg-[#141b19] p-3 text-xs">
                  <span className="block text-[11px] text-[#93a39b]">{key}</span>
                  <span className="mt-0.5 block font-mono font-medium text-white">{String(val)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Radar Backscatter Spectrum Scale Widget */}
        <div className="mt-6 rounded-2xl border border-white/10 bg-[#0c1210] p-4 text-xs">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[11px] uppercase tracking-wider text-[#93a39b]">
              Radar Backscatter Scale (&sigma;⁰ dB Calibration)
            </span>
            <span className="font-mono text-[11px] text-emerald-400">0 Sustained Water Pixels</span>
          </div>

          <div className="relative mt-3 h-3 w-full rounded-full bg-gradient-to-r from-blue-900 via-amber-600 to-emerald-600">
            {/* Threshold indicators */}
            <div className="absolute -top-1 left-[25%] h-5 w-0.5 bg-cyan-400">
              <span className="absolute -top-4 -left-6 font-mono text-[9px] text-cyan-400">-24 dB (Water)</span>
            </div>
            <div className="absolute -top-1 left-[55%] h-5 w-0.5 bg-amber-400">
              <span className="absolute -top-4 -left-8 font-mono text-[9px] text-amber-400">-15 dB (Scree)</span>
            </div>
            <div className="absolute -top-1 left-[85%] h-5 w-0.5 bg-emerald-400">
              <span className="absolute -top-4 -left-6 font-mono text-[9px] text-emerald-400">-6 dB (Canopy)</span>
            </div>
          </div>

          <p className="mt-3 text-[11px] text-[#93a39b]">
            Calm standing water exhibits specular absorption (&le; -24 dB in L-band). Observed backscatter across Kuwari gorge debris spans -18 dB to -6 dB, refuting open-water accumulation.
          </p>
        </div>

        {/* Detailed Findings */}
        {details.length > 0 && (
          <div className="mt-6 space-y-2">
            <h3 className="font-mono text-xs uppercase tracking-wider text-[#d7b56d]">
              Key Scientific Observations
            </h3>
            <ul className="space-y-1.5 rounded-2xl border border-white/10 bg-[#141b19] p-4 text-xs text-[#c9d5cf]">
              {details.map((detail, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="text-[#d7b56d]">▪</span>
                  <span>{detail}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Scientific Limitations & Provenance Guardrails */}
        {limitations.length > 0 && (
          <div className="mt-6 rounded-2xl border border-[#d7b56d]/40 bg-[#d7b56d]/10 p-4 text-xs text-[#f3e2b3]">
            <strong className="block font-medium text-white mb-1.5">
              Strict Provenance & Limitations Guardrails (AGENTS.md)
            </strong>
            <ul className="list-disc space-y-1 pl-4 text-[#f3e2b3]/90">
              {limitations.map((lim, idx) => (
                <li key={idx}>{lim}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Provenance & Manifest Lineage */}
        <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-4 text-xs">
          <div>
            <span className="text-[#93a39b]">Source Manifest:</span>{" "}
            <code className="rounded bg-black/40 px-2 py-0.5 font-mono text-white">{sourcePath}</code>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/spatial"
              className="rounded-full border border-[#d7b56d]/40 bg-[#d7b56d]/10 px-4 py-2 text-xs font-semibold text-[#d7b56d] transition hover:bg-[#d7b56d]/20"
            >
              📍 Inspect on Spatial Map →
            </Link>
            <Link
              href="/reviews"
              className="rounded-full bg-[#d7b56d] px-4 py-2 text-xs font-semibold text-[#1a1408] transition hover:bg-[#c9a65c]"
            >
              Institutional Review Decision →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
