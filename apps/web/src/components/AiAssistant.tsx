"use client";

import { useState, useEffect } from "react";
import type { InvestigationPoint } from "@/lib/case-data";

interface AiAssistantProps {
  onAddPoint?: (point: InvestigationPoint) => void;
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
  next_satellite_passes?: string[];
}

const POPULAR_MODELS = [
  { id: "google/gemini-2.0-flash-001", name: "Gemini 2.0 Flash (Fast & Smart)" },
  { id: "anthropic/claude-3.5-sonnet", name: "Claude 3.5 Sonnet (Deep Reasoning)" },
  { id: "meta-llama/llama-3.3-70b-instruct", name: "Llama 3.3 70B (Open Weights)" },
  { id: "deepseek/deepseek-chat", name: "DeepSeek Chat" },
];

export function AiAssistant({ onAddPoint, mode = "spatial" }: AiAssistantProps) {
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [model, setModel] = useState("google/gemini-2.0-flash-001");
  const [customPrompt, setCustomPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AiAnalysisResult | null>(null);
  const [addedPointIds, setAddedPointIds] = useState<Set<string>>(new Set());

  // Load stored API key on client
  useEffect(() => {
    const saved = localStorage.getItem("rivet_openrouter_api_key");
    if (saved) setApiKey(saved);
  }, []);

  const handleSaveKey = (key: string) => {
    setApiKey(key);
    if (key.trim()) {
      localStorage.setItem("rivet_openrouter_api_key", key.trim());
    } else {
      localStorage.removeItem("rivet_openrouter_api_key");
    }
  };

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await fetch("/api/ai/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          apiKey: apiKey.trim(),
          model,
          mode,
          customPrompt: customPrompt.trim() || undefined,
        }),
      });

      const json = await res.json();
      if (!res.ok) {
        throw new Error(json.message || "Failed to generate AI intelligence");
      }

      setResult(json.data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Analysis request failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleAddPoint = (pt: InvestigationPoint) => {
    onAddPoint?.(pt);
    setAddedPointIds((prev) => new Set(prev).add(pt.id));
  };

  return (
    <section className="rounded-2xl border border-[#d7b56d]/30 bg-[#121716] p-5 shadow-xl">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-2 w-2 rounded-full bg-[#d7b56d] animate-pulse"></span>
            <span className="font-mono text-xs uppercase tracking-widest text-[#d7b56d]">
              OpenRouter AI Copilot
            </span>
          </div>
          <h3 className="mt-1 text-lg font-semibold text-white">
            {mode === "spatial" ? "Geospatial Intelligence & Point Synthesis" : "Acquisition Radar Synthesis"}
          </h3>
          <p className="mt-0.5 text-xs text-[#93a39b]">
            Powered by OpenRouter. Generates hypotheses, terrain risk assessments, and multi-point telemetry.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="rounded-xl border border-white/15 bg-[#0b0f0e] px-3 py-1.5 text-xs text-white focus:border-[#d7b56d] focus:outline-none"
          >
            {POPULAR_MODELS.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <form onSubmit={handleGenerate} className="mt-4 space-y-3">
        {/* API Key Input */}
        <div>
          <label className="block text-xs font-medium text-[#c9d5cf]">
            OpenRouter API Key <span className="text-[#93a39b] font-normal">(Stored locally in browser)</span>
          </label>
          <div className="mt-1 flex items-center gap-2">
            <input
              type={showKey ? "text" : "password"}
              value={apiKey}
              onChange={(e) => handleSaveKey(e.target.value)}
              placeholder="sk-or-v1-..."
              className="w-full rounded-xl border border-white/15 bg-[#0b0f0e] px-3 py-2 font-mono text-xs text-white placeholder:text-[#555] focus:border-[#d7b56d] focus:outline-none"
            />
            <button
              type="button"
              onClick={() => setShowKey(!showKey)}
              className="rounded-xl border border-white/15 px-3 py-2 text-xs text-[#c9d5cf] transition hover:bg-white/5"
            >
              {showKey ? "Hide" : "Show"}
            </button>
          </div>
        </div>

        {/* Custom Focus Query */}
        <div>
          <label className="block text-xs font-medium text-[#c9d5cf]">
            Investigation Focus / Prompt <span className="text-[#93a39b] font-normal">(Optional)</span>
          </label>
          <input
            type="text"
            value={customPrompt}
            onChange={(e) => setCustomPrompt(e.target.value)}
            placeholder={
              mode === "spatial"
                ? "e.g. Identify candidate breach runoff points toward Saryu river..."
                : "e.g. Synthesize why 6 raw pixels became 0 filtered stable pixels..."
            }
            className="mt-1 w-full rounded-xl border border-white/15 bg-[#0b0f0e] px-3 py-2 text-xs text-white placeholder:text-[#555] focus:border-[#d7b56d] focus:outline-none"
          />
        </div>

        {error ? (
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300">
            {error}
          </div>
        ) : null}

        <div className="flex justify-end pt-1">
          <button
            type="submit"
            disabled={loading}
            className="rounded-full bg-[#d7b56d] px-5 py-2 text-xs font-semibold text-[#1a1408] transition hover:bg-[#c9a65c] disabled:opacity-50"
          >
            {loading ? "Generating Intelligence..." : "✨ Synthesize AI Intelligence"}
          </button>
        </div>
      </form>

      {/* Generated Intelligence Report */}
      {result ? (
        <div className="mt-6 space-y-4 border-t border-white/10 pt-4">
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs uppercase tracking-wider text-[#d7b56d]">
              AI Synthesis Output ({model})
            </span>
            <span className="rounded-full bg-[#d7b56d]/15 px-2.5 py-0.5 text-[10px] font-medium text-[#d7b56d]">
              Hypothesis Level
            </span>
          </div>

          {result.summary ? (
            <div className="rounded-xl border border-white/10 bg-[#0b0f0e] p-3 text-xs leading-relaxed text-[#e6ede9]">
              <strong className="block font-medium text-[#d7b56d] mb-1">Executive Summary:</strong>
              {result.summary}
            </div>
          ) : null}

          <div className="grid gap-3 sm:grid-cols-2">
            {result.risk_assessment ? (
              <div className="rounded-xl border border-white/10 bg-[#0b0f0e] p-3 text-xs text-[#c9d5cf]">
                <strong className="block font-medium text-amber-400 mb-1">Slope & Hydrological Risk:</strong>
                {result.risk_assessment}
              </div>
            ) : null}

            {result.radar_interpretation ? (
              <div className="rounded-xl border border-white/10 bg-[#0b0f0e] p-3 text-xs text-[#c9d5cf]">
                <strong className="block font-medium text-cyan-400 mb-1">SAR Geometry & Backscatter:</strong>
                {result.radar_interpretation}
              </div>
            ) : null}

            {result.granule_evaluation ? (
              <div className="rounded-xl border border-white/10 bg-[#0b0f0e] p-3 text-xs text-[#c9d5cf]">
                <strong className="block font-medium text-amber-400 mb-1">Granule Evaluation:</strong>
                {result.granule_evaluation}
              </div>
            ) : null}

            {result.temporal_change ? (
              <div className="rounded-xl border border-white/10 bg-[#0b0f0e] p-3 text-xs text-[#c9d5cf]">
                <strong className="block font-medium text-cyan-400 mb-1">Temporal Change Analysis:</strong>
                {result.temporal_change}
              </div>
            ) : null}
          </div>

          {/* AI Suggested Coordinates / Points */}
          {result.suggested_points && result.suggested_points.length > 0 ? (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-white">
                AI Suggested Investigation Points ({result.suggested_points.length})
              </h4>
              <div className="grid gap-2 sm:grid-cols-2">
                {result.suggested_points.map((pt) => {
                  const isAdded = addedPointIds.has(pt.id);
                  return (
                    <div
                      key={pt.id}
                      className="flex flex-col justify-between rounded-xl border border-white/10 bg-[#0b0f0e] p-3 text-xs"
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
                        <h5 className="mt-1 font-medium text-white">{pt.name}</h5>
                        <p className="mt-1 text-[#93a39b]">{pt.description}</p>
                      </div>

                      <div className="mt-3 flex items-center justify-between border-t border-white/5 pt-2">
                        <span className="font-mono text-[10px] text-[#c9d5cf]">
                          {pt.coordinates[1].toFixed(4)}°N, {pt.coordinates[0].toFixed(4)}°E
                        </span>
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
                  );
                })}
              </div>
            </div>
          ) : null}

          {/* Recommended Actions */}
          {result.recommended_actions && result.recommended_actions.length > 0 ? (
            <div className="rounded-xl border border-white/10 bg-[#0b0f0e] p-3 text-xs">
              <strong className="block font-medium text-white mb-1.5">Recommended Field & Satellite Actions:</strong>
              <ul className="list-disc space-y-1 pl-4 text-[#c9d5cf]">
                {result.recommended_actions.map((act, i) => (
                  <li key={i}>{act}</li>
                ))}
              </ul>
            </div>
          ) : null}

          <p className="text-[10px] text-[#93a39b] italic">
            Notice: In accordance with RIVET AGENTS.md engineering rules, AI-generated points and analyses represent hypotheses and interpretations. They do not constitute surveyed physical ground truth or verified water detections.
          </p>
        </div>
      ) : null}
    </section>
  );
}
