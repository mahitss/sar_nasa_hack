"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { listAcquisitions, createAcquisition, type ApiAcquisition } from "@/lib/api";
import { ACQUISITIONS, COMPARISON_FIELDS } from "@/lib/case-data";
import { AiAssistant } from "@/components/AiAssistant";

interface ParameterDetail {
  title: string;
  significance: string;
  radarPrinciple: string;
}

const PARAMETER_EXPLANATIONS: Record<string, ParameterDetail> = {
  "Raw sweep-stable pixels": {
    title: "Raw Low-Backscatter Pixels (6 vs 12)",
    significance: "Preliminary sigma-naught thresholding identified 6 candidate pixels on 6-Sept and 12 on 30-Sept in the valley basin.",
    radarPrinciple: "Radar specular reflection from smooth rocks, sand bars, or rain-saturated gravel can mimic calm water. These raw pixels require rigorous topographic filtering before being accepted as water candidates.",
  },
  "Filtered sweep-stable pixels": {
    title: "Filtered Sustained Water Candidates (0 vs 0)",
    significance: "Zero pixels survived DEM slope thresholding and valid-samples mask intersection in both 6-Sept and 30-Sept acquisitions.",
    radarPrinciple: "This conclusive scientific metric proves that no sustained open-water impoundment formed behind the Kuwari landslide debris dam during the September 2026 observation window.",
  },
  "Mode": {
    title: "Frequency A, 40 MHz Bandwidth, HH+HV Dual-Pol",
    significance: "High-resolution L-band SAR with horizontal transmit/horizontal receive (HH) and horizontal transmit/vertical receive (HV).",
    radarPrinciple: "L-band (24 cm wavelength) penetrates dense Himalayan forest canopy to measure ground-level backscatter. The cross-polarized HV channel is sensitive to volume scattering from vegetation, while HH detects surface reflection.",
  },
  "Look / pass": {
    title: "Left-Looking Descending Pass (Track 5, Frame 73)",
    significance: "Spacecraft flies southward looking towards the east (left of flight direction) across Uttarakhand.",
    radarPrinciple: "Because radar illuminates the rugged terrain obliquely at ~37° incidence, steep slopes facing away from the antenna experience complete radar shadow, while slopes facing the antenna experience foreshortening.",
  },
  "orbitType": {
    title: "Medium Precision Orbit Ephemeris (MOE)",
    significance: "Observed orbit ephemeris is MOE (~5 cm positioning accuracy) rather than Near-Real-Time NOE (~30 cm).",
    radarPrinciple: "Centimeter-level spacecraft trajectory reconstruction ensures sub-pixel georeferencing precision when overlaying radar backscatter onto digital elevation models.",
  },
  "attitudeType": {
    title: "Custom Spacecraft Attitude",
    significance: "Spacecraft pointing was reconstructed using onboard star-tracker telemetry rather than nominal pointing.",
    radarPrinciple: "Accounting for minute roll, pitch, and yaw variations eliminates Doppler centroid estimation errors in steep mountain valleys.",
  },
  "Filename token N": {
    title: "Filename Ephemeris Discrepancy (Token 'N')",
    significance: "Granule filename token 'N' specifies NOE/NRP, but internal HDF5 metadata records MOE/Custom ephemeris.",
    radarPrinciple: "Under strict NASA provenance rules (AGENTS.md), this discrepancy must be audited and flagged as an unresolved metadata gap rather than silently overwritten.",
  },
  "Incidence cube": {
    title: "3D Incidence Angle Lookup Cube (21 x 699 x 710)",
    significance: "Stores local radar incidence and look angles across 21 elevation slices from 0 m to 10,000 m WGS84.",
    radarPrinciple: "Enables precise radiometric terrain correction (RTC) to normalize backscatter variations caused by varying slope angles across mountain ridges.",
  },
  "shadowMaskingApplied": {
    title: "Shadow Masking Applied: False",
    significance: "The GCOV processor did NOT automatically mask out or zero out pixels located in radar shadow zones.",
    radarPrinciple: "Because shadow masking was not applied at the processor level, dark shadow areas on northwest-facing cliffs can easily be misinterpreted as calm water without analyst QC.",
  },
  "Processor DEM": {
    title: "Copernicus DEM 30 m (Release 2023_1, WGS84 Ellipsoid)",
    significance: "The global 30 m elevation model used by the NISAR processing facility for orthorectification.",
    radarPrinciple: "Referenced directly to the WGS84 ellipsoid. Local topographical surveys often use the EGM2008 geoid; mixing vertical datums without a ~48 m geoid undulation correction causes horizontal pixel shifts.",
  },
};

export default function AcquisitionsPage() {
  const { token, currentIncident, currentRole, signIn } = useAuth();
  const [acquisitions, setAcquisitions] = useState<ApiAcquisition[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAdd, setShowAdd] = useState(false);

  // Parameter inspection state
  const [selectedParam, setSelectedParam] = useState<string | null>("Filtered sweep-stable pixels");
  const [paramAiDetail, setParamAiDetail] = useState<{ [key: string]: string }>({});
  const [paramLoading, setParamLoading] = useState(false);

  // Form state
  const [sourceProvider, setSourceProvider] = useState("NASA-JPL");
  const [granuleId, setGranuleId] = useState("");
  const [crid, setCrid] = useState("P05023");
  const [productMaturity, setProductMaturity] = useState<"provisional" | "validated">("provisional");
  const [formError, setFormError] = useState<string | null>(null);
  const [formSubmitting, setFormSubmitting] = useState(false);

  const fetchAcquisitions = useCallback(async () => {
    if (!token || !currentIncident) {
      setAcquisitions([]);
      return;
    }
    setLoading(true);
    try {
      const data = await listAcquisitions(token, currentIncident.id);
      setAcquisitions(data || []);
    } catch {
      setAcquisitions([]);
    } finally {
      setLoading(false);
    }
  }, [token, currentIncident]);

  useEffect(() => {
    fetchAcquisitions();
  }, [fetchAcquisitions]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !currentIncident) return;
    setFormError(null);
    setFormSubmitting(true);

    try {
      await createAcquisition(token, currentIncident.id, {
        source_provider: sourceProvider,
        granule_id: granuleId,
        crid,
        product_maturity: productMaturity,
      });
      await fetchAcquisitions();
      setShowAdd(false);
      setGranuleId("");
    } catch (err: unknown) {
      const apiErr = err as { message?: string };
      setFormError(apiErr.message || "Failed to register acquisition");
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleDeepParamAnalyze = async (paramName: string) => {
    setSelectedParam(paramName);
    if (paramAiDetail[paramName]) return;

    setParamLoading(true);
    try {
      const res = await fetch("/api/ai/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode: "metadata_explain",
          fieldKey: paramName,
          customPrompt: PARAMETER_EXPLANATIONS[paramName]?.significance,
        }),
      });
      const json = await res.json();
      if (res.ok && json.data) {
        const text = `${json.data.plain_english} ${json.data.mission_significance} ${json.data.technical_detail}`;
        setParamAiDetail((prev) => ({ ...prev, [paramName]: text }));
      }
    } catch {
      // Keep static explanation on error
    } finally {
      setParamLoading(false);
    }
  };

  const activeDetail = selectedParam ? PARAMETER_EXPLANATIONS[selectedParam] : null;

  return (
    <div className="space-y-8">
      {/* Header and Spatial Action */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs tracking-[0.18em] text-[#d7b56d]">NASA ACQUISITION REGISTRY</span>
            <span className="rounded-full bg-[#d7b56d]/15 px-2.5 py-0.5 font-mono text-[10px] text-[#d7b56d]">
              NISAR Group D40
            </span>
          </div>
          <h1 className="mt-2 text-3xl font-semibold">Satellite Acquisition Intelligence</h1>
          <p className="mt-2 max-w-3xl text-sm text-[#c9d5cf]">
            Source catalog records, orbit geometries, and polarimetric radar granules for the Kuwari investigation.
            Click any parameter row below to inspect its NASA physical interpretation or synthesize live mission intelligence.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/spatial"
            className="rounded-full border border-[#d7b56d]/40 bg-[#d7b56d]/10 px-4 py-2 text-xs font-semibold text-[#d7b56d] transition hover:bg-[#d7b56d]/20"
          >
            🗺️ Explore Discovery Map & POIs →
          </Link>
          {token && currentIncident && (currentRole === "owner" || currentRole === "analyst") ? (
            <button
              type="button"
              onClick={() => setShowAdd(!showAdd)}
              className="rounded-full bg-[#d7b56d] px-4 py-2 text-xs font-semibold text-[#1a1408] transition hover:bg-[#c9a65c]"
            >
              {showAdd ? "✕ Close Form" : "+ Register Acquisition"}
            </button>
          ) : null}
        </div>
      </div>

      {/* Quick Sign-In Banner if user is currently unauthenticated */}
      {!token ? (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-[#d7b56d]/30 bg-[#121716] p-4 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-[#d7b56d] font-semibold">🔒 Unauthenticated View:</span>
            <span className="text-[#93a39b]">
              Currently displaying historical NISAR baseline data. Sign in with a test profile to register live granules to PostgreSQL.
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => signIn("analyst@rivet.local", "password123")}
              className="rounded-full bg-[#d7b56d] px-3.5 py-1 text-xs font-semibold text-[#1a1408] transition hover:bg-[#c9a65c]"
            >
              Sign in as Analyst
            </button>
            <button
              type="button"
              onClick={() => signIn("lead@rivet.local", "password123")}
              className="rounded-full border border-white/20 bg-white/5 px-3.5 py-1 text-xs text-white transition hover:bg-white/10"
            >
              Sign in as Lead
            </button>
          </div>
        </div>
      ) : null}

      {/* Registration Form */}
      {showAdd ? (
        <section className="rounded-3xl border border-[#d7b56d]/40 bg-[#121716] p-6 shadow-xl">
          <h2 className="text-lg font-medium text-white">Register Satellite Acquisition Granule</h2>
          <p className="mt-1 text-xs text-[#93a39b]">
            Persists satellite granule metadata to PostgreSQL for incident: {currentIncident?.title}
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
                  Source Provider
                </label>
                <input
                  type="text"
                  required
                  value={sourceProvider}
                  onChange={(e) => setSourceProvider(e.target.value)}
                  placeholder="NASA-JPL"
                  className="mt-1 w-full rounded-xl border border-white/15 bg-[#101816] px-3.5 py-2 text-sm text-white focus:border-[#d7b56d] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium uppercase tracking-wide text-[#93a39b]">
                  Composite Release ID (CRID)
                </label>
                <input
                  type="text"
                  required
                  value={crid}
                  onChange={(e) => setCrid(e.target.value)}
                  placeholder="P05023"
                  className="mt-1 w-full rounded-xl border border-white/15 bg-[#101816] px-3.5 py-2 text-sm text-white focus:border-[#d7b56d] focus:outline-none"
                />
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-xs font-medium uppercase tracking-wide text-[#93a39b]">
                  Granule Identifier
                </label>
                <input
                  type="text"
                  required
                  value={granuleId}
                  onChange={(e) => setGranuleId(e.target.value)}
                  placeholder="NISAR_L2_PR_GCOV_001_005_D_073_4000_HHHV_A_20260906T132236_..."
                  className="mt-1 w-full rounded-xl border border-white/15 bg-[#101816] px-3.5 py-2 font-mono text-xs text-white focus:border-[#d7b56d] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium uppercase tracking-wide text-[#93a39b]">
                  Product Maturity
                </label>
                <select
                  value={productMaturity}
                  onChange={(e) => setProductMaturity(e.target.value as "provisional" | "validated")}
                  className="mt-1 w-full rounded-xl border border-white/15 bg-[#101816] px-3.5 py-2 text-sm text-white focus:border-[#d7b56d] focus:outline-none"
                >
                  <option value="provisional">Provisional (Unvalidated processing)</option>
                  <option value="validated">Validated (Rechecked against NASA CMR)</option>
                </select>
              </div>
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
                {formSubmitting ? "Registering..." : "Save Acquisition Record"}
              </button>
            </div>
          </form>
        </section>
      ) : null}

      {/* Persisted Incident Acquisitions */}
      {currentIncident ? (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-medium">
              Persisted Incident Acquisitions ({acquisitions.length})
            </h2>
            <span className="font-mono text-xs text-[#93a39b]">
              Incident: {currentIncident.title}
            </span>
          </div>

          {loading ? (
            <p className="text-sm text-[#93a39b]">Loading acquisitions from PostgreSQL...</p>
          ) : acquisitions.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-white/15 p-6 text-center text-sm text-[#c9d5cf]">
              No acquisitions registered for this incident yet.
              {currentRole === "owner" || currentRole === "analyst" ? (
                <button
                  type="button"
                  onClick={() => setShowAdd(true)}
                  className="ml-2 text-[#d7b56d] underline hover:no-underline"
                >
                  Register the first granule
                </button>
              ) : null}
            </div>
          ) : (
            <div className="overflow-x-auto rounded-2xl border border-white/10 bg-[#121716]">
              <table className="w-full text-left text-sm">
                <thead className="bg-white/5 text-xs uppercase tracking-wide text-[#93a39b]">
                  <tr>
                    <th className="px-4 py-3">Granule ID</th>
                    <th className="px-4 py-3">Provider</th>
                    <th className="px-4 py-3">CRID</th>
                    <th className="px-4 py-3">Maturity</th>
                    <th className="px-4 py-3">Registered At</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/10">
                  {acquisitions.map((acq) => (
                    <tr key={acq.id}>
                      <td className="break-all px-4 py-3 font-mono text-xs text-white">
                        {acq.granule_id}
                      </td>
                      <td className="px-4 py-3 text-xs text-[#c9d5cf]">{acq.source_provider}</td>
                      <td className="px-4 py-3 font-mono text-xs text-[#d7b56d]">{acq.crid}</td>
                      <td className="px-4 py-3">
                        <span
                          className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
                            acq.product_maturity === "validated"
                              ? "bg-emerald-500/20 text-emerald-300"
                              : "bg-amber-500/20 text-amber-300"
                          }`}
                        >
                          {acq.product_maturity}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-[#93a39b]">
                        {acq.created_at ? new Date(acq.created_at).toLocaleString() : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ) : null}

      {/* NASA Earth Science AI Acquisition Copilot */}
      <AiAssistant mode="acquisitions" />

      {/* Interactive Parameter Inspection Drawer */}
      {selectedParam && (
        <section className="rounded-2xl border border-[#d7b56d]/50 bg-[#141b19] p-5 shadow-2xl transition-all">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-3">
            <div className="flex items-center gap-2">
              <span className="flex h-2 w-2 rounded-full bg-[#d7b56d]"></span>
              <span className="font-mono text-xs uppercase tracking-wider text-[#d7b56d]">
                NASA Parameter Intelligence
              </span>
              <span className="rounded-full bg-white/10 px-2.5 py-0.5 font-mono text-[10px] text-white">
                {selectedParam}
              </span>
            </div>
            <button
              type="button"
              disabled={paramLoading}
              onClick={() => handleDeepParamAnalyze(selectedParam)}
              className="rounded-full border border-[#d7b56d]/40 bg-[#d7b56d]/10 px-3 py-1 text-xs text-[#d7b56d] transition hover:bg-[#d7b56d]/20 disabled:opacity-50"
            >
              {paramLoading ? "Analyzing..." : "✨ Ask NASA AI to Deepen Analysis"}
            </button>
          </div>

          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <div>
              <h4 className="font-medium text-white">{activeDetail?.title || selectedParam}</h4>
              <p className="mt-1.5 text-xs text-[#c9d5cf] leading-relaxed">
                {activeDetail?.significance || "Technical metadata parameter recorded in the NISAR HDF5 header."}
              </p>
              {paramAiDetail[selectedParam] ? (
                <div className="mt-3 rounded-xl border border-[#d7b56d]/20 bg-[#0b0f0e] p-3 text-xs leading-relaxed text-[#f3e2b3]">
                  <strong className="block text-[11px] font-semibold uppercase tracking-wider text-[#d7b56d] mb-1">
                    NASA AI Physical Interpretation:
                  </strong>
                  {paramAiDetail[selectedParam]}
                </div>
              ) : null}
            </div>

            <div className="rounded-xl border border-white/10 bg-[#0b0f0e] p-3.5 text-xs text-[#93a39b]">
              <strong className="block font-medium text-white mb-1">Physical Radar Principle:</strong>
              <p className="leading-relaxed">
                {activeDetail?.radarPrinciple || "Governs how microwave signals reflect off mountain terrain and water interfaces."}
              </p>
              <div className="mt-3 flex items-center gap-2 border-t border-white/5 pt-2 text-[11px] text-[#d7b56d]">
                <span>💡 Click other rows in the tables below to inspect their physical meaning.</span>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Historical Reference Pair Comparison */}
      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-xl font-medium">Historical Baseline NISAR Reference (Group D40)</h2>
            <p className="text-xs text-[#93a39b]">
              Interactive dual-pass comparison (6-Sept vs 30-Sept 2026). Click any row to expand its NASA physical interpretation.
            </p>
          </div>
          <span className="font-mono text-xs text-[#d7b56d]">CRID: P05023 (Provisional)</span>
        </div>

        {/* Granule Comparison Table */}
        <div className="rounded-2xl border border-white/10 bg-[#121716] overflow-hidden">
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
            <h3 className="text-sm font-medium text-white">Granule Comparison & Pixel Water Sweep</h3>
            <span className="text-[11px] text-[#93a39b]">Interactive Rows</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-white/5 text-xs uppercase tracking-wide text-[#93a39b]">
                <tr>
                  <th className="px-4 py-3">Metric / Field</th>
                  {ACQUISITIONS.map((a) => (
                    <th key={a.iso} className="px-4 py-3">
                      {a.date}
                    </th>
                  ))}
                  <th className="px-4 py-3 text-right">Scientific Interpretation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10">
                <tr
                  onClick={() => setSelectedParam("Granule")}
                  className={`cursor-pointer transition hover:bg-white/5 ${
                    selectedParam === "Granule" ? "bg-[#d7b56d]/10" : ""
                  }`}
                >
                  <th scope="row" className="px-4 py-3 font-medium text-white">
                    Granule
                  </th>
                  {ACQUISITIONS.map((a) => (
                    <td key={a.granule} className="break-all px-4 py-3 font-mono text-xs text-[#c9d5cf]">
                      {a.granule}
                    </td>
                  ))}
                  <td className="px-4 py-3 text-right text-xs text-[#d7b56d]">
                    Provisional GCOV →
                  </td>
                </tr>

                <tr
                  onClick={() => setSelectedParam("Raw sweep-stable pixels")}
                  className={`cursor-pointer transition hover:bg-white/5 ${
                    selectedParam === "Raw sweep-stable pixels" ? "bg-[#d7b56d]/10" : ""
                  }`}
                >
                  <th scope="row" className="px-4 py-3 font-medium text-white">
                    Raw sweep-stable pixels
                  </th>
                  {ACQUISITIONS.map((a) => (
                    <td key={a.iso} className="px-4 py-3 font-mono text-xs font-semibold text-amber-300">
                      {a.rawStable} pixels
                    </td>
                  ))}
                  <td className="px-4 py-3 text-right text-xs text-amber-400">
                    Unfiltered threshold →
                  </td>
                </tr>

                <tr
                  onClick={() => setSelectedParam("Filtered sweep-stable pixels")}
                  className={`cursor-pointer transition hover:bg-white/5 ${
                    selectedParam === "Filtered sweep-stable pixels" ? "bg-[#d7b56d]/10" : ""
                  }`}
                >
                  <th scope="row" className="px-4 py-3 font-medium text-white">
                    Filtered sweep-stable pixels
                  </th>
                  {ACQUISITIONS.map((a) => (
                    <td key={a.iso} className="px-4 py-3 font-mono text-xs font-semibold text-emerald-400">
                      {a.filteredStable} (Zero water)
                    </td>
                  ))}
                  <td className="px-4 py-3 text-right text-xs text-emerald-400">
                    Conclusive QC metric →
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Shared Metadata Table */}
        <div className="rounded-2xl border border-white/10 bg-[#121716] overflow-hidden">
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
            <h3 className="text-sm font-medium text-white">Shared Acquisition & Orbit Geometry Metadata</h3>
            <span className="text-[11px] text-[#93a39b]">Click any row to inspect</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full table-fixed text-left text-sm">
              <thead className="bg-white/5 text-xs uppercase tracking-wide text-[#93a39b]">
                <tr>
                  <th scope="col" className="w-[30%] px-4 py-3">
                    Parameter
                  </th>
                  {ACQUISITIONS.map((a) => (
                    <th scope="col" key={a.iso} className="w-[35%] px-4 py-3">
                      {a.date}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10">
                {COMPARISON_FIELDS.map((f) => {
                  const isSelected = selectedParam === f.label;
                  return (
                    <tr
                      key={f.label}
                      onClick={() => setSelectedParam(f.label)}
                      className={`cursor-pointer transition hover:bg-white/5 ${
                        isSelected ? "bg-[#d7b56d]/10" : ""
                      }`}
                    >
                      <th scope="row" className="px-4 py-3 align-top font-medium text-white flex items-center justify-between">
                        <span>{f.label}</span>
                        {isSelected ? <span className="text-[#d7b56d] text-xs">● Active</span> : null}
                      </th>
                      <td className="break-words px-4 py-3 align-top text-xs text-[#c9d5cf] font-mono">
                        {f.value}
                      </td>
                      <td className="break-words px-4 py-3 align-top text-xs text-[#c9d5cf] font-mono">
                        {f.value}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="px-4 pb-4 pt-2 text-xs text-[#93a39b]">
            Coordinate steps represent nominal grid posting (~500 m). They do not establish independent spatial resolution cells.
          </p>
        </div>
      </section>

      {/* Discrepancies & Provenance Guardrails */}
      <section className="rounded-2xl border border-[#d7b56d]/40 bg-[#d7b56d]/10 p-5 text-sm text-[#f3e2b3]">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-white">NASA Acquisition Provenance Guardrails (AGENTS.md)</span>
        </div>
        <ul className="mt-2.5 list-disc space-y-1.5 pl-5 text-xs text-[#f3e2b3]/90">
          <li>P05023 remains provisional. Do not mix P05023 with P05036.</li>
          <li>Filename token N expects NOE orbit ephemeris; observed orbitType is MOE.</li>
          <li>Filename token N expects NRP radar pointing; observed attitudeType is Custom.</li>
          <li>Geometric accuracy bias and standard deviation are NaN. Mismatch is unresolved.</li>
          <li>Valid-samples masks indicate data coverage, NOT water, shadow, or layover classifications.</li>
        </ul>
      </section>
    </div>
  );
}
