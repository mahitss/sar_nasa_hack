"use client";

import { useState } from "react";
import type { InvestigationPoint } from "@/lib/case-data";

interface AiAssistantProps {
  onAddPoint?: (point: InvestigationPoint) => void;
  onAddAllPoints?: (points: InvestigationPoint[]) => void;
  onSelectPoint?: (point: InvestigationPoint) => void;
  mode?: "spatial" | "acquisitions";
}

interface AiAnalysisResult {
  summary?: string;
  risk_assessment?: string;
  radar_interpretation?: string;
  granule_evaluation?: string;
  temporal_change?: string;
  metadata_anomalies?: string;
  suggested_points?: InvestigationPoint[];
  recommended_actions?: string[];
}

const SPATIAL_PRESETS = [
  "🎯 Generate 4 Target Geospatial Points",
  "🌊 Landslide Dam & Valley Drainage",
  "📡 NISAR Track 5 Shadow & Layover",
  "🏘️ Downstream Settlement Exposure",
];

const ACQUISITION_PRESETS = [
  "📊 6-Sept vs 30-Sept Pixel Variance",
  "🛰️ Orbit Ephemeris & Pointing Gap",
  "📡 40 MHz Polarimetric Ratio Analysis",
  "🔄 Future Satellite Revisit Window",
];

export function AiAssistant({ onAddPoint, onAddAllPoints, onSelectPoint, mode = "spatial" }: AiAssistantProps) {
  const [customPrompt, setCustomPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AiAnalysisResult | null>(null);
  const [addedPointIds, setAddedPointIds] = useState<Set<string>>(new Set());

  const presets = mode === "spatial" ? SPATIAL_PRESETS : ACQUISITION_PRESETS;

  const handleGenerate = async (overridePrompt?: string) => {
    setError(null);
    setLoading(true);
    const promptToSend = overridePrompt !== undefined ? overridePrompt : customPrompt;

    try {
      const res = await fetch("/api/ai/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode,
          customPrompt: promptToSend.trim() || undefined,
        }),
      });

      const json = await res.json();
      if (!res.ok) {
        throw new Error(json.message || "Failed to generate NASA intelligence");
      }

      setResult(json.data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "NASA AI analysis request failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleAddPoint = (pt: InvestigationPoint) => {
    onAddPoint?.(pt);
    setAddedPointIds((prev) => new Set(prev).add(pt.id));
  };

  const handleAddAll = () => {
    if (!result?.suggested_points?.length) return;
    if (onAddAllPoints) {
      onAddAllPoints(result.suggested_points);
    } else {
      result.suggested_points.forEach((pt) => onAddPoint?.(pt));
    }
    const newIds = new Set(addedPointIds);
    result.suggested_points.forEach((pt) => newIds.add(pt.id));
    setAddedPointIds(newIds);
  };

  return (
    <section className="rounded-2xl border border-[#d7b56d]/30 bg-[#121716] p-5 shadow-xl">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-2 w-2 rounded-full bg-[#d7b56d] animate-pulse"></span>
            <span className="font-mono text-xs uppercase tracking-widest text-[#d7b56d]">
              NASA Earth Science AI Copilot
            </span>
            <span className="rounded-full bg-[#d7b56d]/15 px-2 py-0.5 font-mono text-[10px] text-[#d7b56d]">
              Live Engine Active
            </span>
          </div>
          <h3 className="mt-1 text-lg font-semibold text-white">
            {mode === "spatial"
              ? "NASA Geospatial Intelligence & Multi-Point Synthesis"
              : "NASA NISAR Polarimetric Acquisition Synthesis"}
          </h3>
          <p className="mt-0.5 text-xs text-[#93a39b]">
            Direct NASA mission intelligence synthesizing terrain risk models, polarimetric SAR backscatter, and tactical coordinates.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={loading}
            onClick={() => handleGenerate()}
            className="flex items-center gap-2 rounded-full bg-[#d7b56d] px-4 py-2 text-xs font-semibold text-[#1a1408] transition hover:bg-[#c9a65c] disabled:opacity-50"
          >
            {loading ? (
              <>
                <svg className="h-3.5 w-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                </svg>
                <span>Synthesizing NASA Intelligence...</span>
              </>
            ) : (
              <span>✨ Synthesize NASA Intelligence</span>
            )}
          </button>
        </div>
      </div>

      {/* Preset Quick Focus Prompts */}
      <div className="mt-4">
        <label className="block text-[11px] font-medium uppercase tracking-wider text-[#93a39b]">
          Quick Mission Focus Chips
        </label>
        <div className="mt-2 flex flex-wrap gap-2">
          {presets.map((preset) => (
            <button
              key={preset}
              type="button"
              disabled={loading}
              onClick={() => {
                setCustomPrompt(preset);
                handleGenerate(preset);
              }}
              className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-[#c9d5cf] transition hover:border-[#d7b56d]/50 hover:bg-[#d7b56d]/10 hover:text-white disabled:opacity-50"
            >
              {preset}
            </button>
          ))}
        </div>
      </div>

      {/* Custom Prompt Input */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleGenerate();
        }}
        className="mt-3 flex gap-2"
      >
        <input
          type="text"
          value={customPrompt}
          onChange={(e) => setCustomPrompt(e.target.value)}
          placeholder={
            mode === "spatial"
              ? "Or enter custom NASA investigation focus: e.g. Analyze drainage channels toward Saryu river..."
              : "Or enter custom focus: e.g. Interpret why 6 raw pixels became 0 filtered stable pixels..."
          }
          className="flex-1 rounded-xl border border-white/15 bg-[#0b0f0e] px-3.5 py-2 text-xs text-white placeholder:text-[#666] focus:border-[#d7b56d] focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-xs font-medium text-white transition hover:bg-white/10 disabled:opacity-50"
        >
          Run Focus
        </button>
      </form>

      {error ? (
        <div className="mt-3 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300">
          {error}
        </div>
      ) : null}

      {/* Generated Intelligence Output */}
      {result ? (
        <div className="mt-6 space-y-4 border-t border-white/10 pt-4">
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs uppercase tracking-wider text-[#d7b56d]">
              NASA Earth Science Analysis Synthesis
            </span>
            <span className="rounded-full bg-[#d7b56d]/15 px-2.5 py-0.5 text-[10px] font-medium text-[#d7b56d]">
              Hypothesis Level
            </span>
          </div>

          {result.summary ? (
            <div className="rounded-xl border border-white/10 bg-[#0b0f0e] p-3.5 text-xs leading-relaxed text-[#e6ede9]">
              <strong className="block font-medium text-[#d7b56d] mb-1">NASA Science Synthesis:</strong>
              {result.summary}
            </div>
          ) : null}

          <div className="grid gap-3 sm:grid-cols-2">
            {result.risk_assessment ? (
              <div className="rounded-xl border border-white/10 bg-[#0b0f0e] p-3 text-xs text-[#c9d5cf]">
                <strong className="block font-medium text-amber-400 mb-1">Slope & Hydrological Risk Assessment:</strong>
                {result.risk_assessment}
              </div>
            ) : null}

            {result.radar_interpretation ? (
              <div className="rounded-xl border border-white/10 bg-[#0b0f0e] p-3 text-xs text-[#c9d5cf]">
                <strong className="block font-medium text-cyan-400 mb-1">NISAR SAR Geometry & Radar Shadow:</strong>
                {result.radar_interpretation}
              </div>
            ) : null}

            {result.granule_evaluation ? (
              <div className="rounded-xl border border-white/10 bg-[#0b0f0e] p-3 text-xs text-[#c9d5cf]">
                <strong className="block font-medium text-amber-400 mb-1">Granule Evaluation (Group D40):</strong>
                {result.granule_evaluation}
              </div>
            ) : null}

            {result.temporal_change ? (
              <div className="rounded-xl border border-white/10 bg-[#0b0f0e] p-3 text-xs text-[#c9d5cf]">
                <strong className="block font-medium text-cyan-400 mb-1">Temporal Change & Pixel Filtering:</strong>
                {result.temporal_change}
              </div>
            ) : null}

            {result.metadata_anomalies ? (
              <div className="rounded-xl border border-white/10 bg-[#0b0f0e] p-3 text-xs text-[#c9d5cf] sm:col-span-2">
                <strong className="block font-medium text-purple-400 mb-1">Orbit Ephemeris & Pointing Metadata Evaluation:</strong>
                {result.metadata_anomalies}
              </div>
            ) : null}
          </div>

          {/* Suggested Multi-Point Coordinates */}
          {result.suggested_points && result.suggested_points.length > 0 ? (
            <div className="space-y-3 pt-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-white">
                  NASA Target Investigation Coordinates ({result.suggested_points.length} Points)
                </h4>
                <button
                  type="button"
                  onClick={handleAddAll}
                  className="rounded-full bg-[#d7b56d] px-3 py-1 text-xs font-semibold text-[#1a1408] transition hover:bg-[#c9a65c]"
                >
                  + Add All {result.suggested_points.length} Points to Map
                </button>
              </div>

              <div className="grid gap-2.5 sm:grid-cols-2">
                {result.suggested_points.map((pt) => {
                  const isAdded = addedPointIds.has(pt.id);
                  return (
                    <div
                      key={pt.id}
                      className="group flex flex-col justify-between rounded-xl border border-white/10 bg-[#0b0f0e] p-3 text-xs transition hover:border-[#d7b56d]/50"
                    >
                      <div>
                        <div className="flex items-center justify-between">
                          <span
                            className="rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase"
                            style={{ backgroundColor: `${pt.color || "#d7b56d"}20`, color: pt.color || "#d7b56d" }}
                          >
                            {pt.category}
                          </span>
                          <span className="font-mono text-[10px] text-[#93a39b]">{pt.elevation}</span>
                        </div>
                        <h5
                          className="mt-1.5 font-medium text-white group-hover:text-[#d7b56d] cursor-pointer"
                          onClick={() => onSelectPoint?.(pt)}
                        >
                          {pt.name}
                        </h5>
                        <p className="mt-1 text-[#93a39b] line-clamp-2">{pt.description}</p>
                        {pt.scientificContext ? (
                          <p className="mt-1 text-[11px] text-[#c9d5cf]/80 italic">
                            {pt.scientificContext}
                          </p>
                        ) : null}
                      </div>

                      <div className="mt-3 flex items-center justify-between border-t border-white/5 pt-2">
                        <span className="font-mono text-[10px] text-[#c9d5cf]">
                          {pt.coordinates[1].toFixed(4)}°N, {pt.coordinates[0].toFixed(4)}°E
                        </span>
                        <div className="flex items-center gap-1.5">
                          {onSelectPoint ? (
                            <button
                              type="button"
                              onClick={() => onSelectPoint(pt)}
                              className="rounded-full border border-white/15 px-2 py-0.5 text-[10px] text-white transition hover:bg-white/10"
                            >
                              Inspect
                            </button>
                          ) : null}
                          <button
                            type="button"
                            onClick={() => handleAddPoint(pt)}
                            disabled={isAdded}
                            className={`rounded-full px-2.5 py-1 text-[11px] font-medium transition ${
                              isAdded
                                ? "bg-emerald-500/20 text-emerald-300"
                                : "bg-[#d7b56d] text-[#1a1408] hover:bg-[#c9a65c]"
                            }`}
                          >
                            {isAdded ? "✓ Added to Map" : "+ Add to Map"}
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : null}

          {/* Recommended Actions */}
          {result.recommended_actions && result.recommended_actions.length > 0 ? (
            <div className="rounded-xl border border-white/10 bg-[#0b0f0e] p-3 text-xs">
              <strong className="block font-medium text-white mb-1.5">NASA Recommended Scientific Follow-Up:</strong>
              <ul className="list-disc space-y-1 pl-4 text-[#c9d5cf]">
                {result.recommended_actions.map((act, i) => (
                  <li key={i}>{act}</li>
                ))}
              </ul>
            </div>
          ) : null}

          <p className="text-[10px] text-[#93a39b] italic">
            NASA Scientific Provenance Note: Per RIVET engineering rules (AGENTS.md), AI-synthesized points and backscatter assessments are provisional hypotheses. They do not constitute surveyed lake perimeters or confirmed surface water detections.
          </p>
        </div>
      ) : null}
    </section>
  );
}
