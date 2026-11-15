"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth-context";
import { listAcquisitions, createAcquisition, type ApiAcquisition } from "@/lib/api";
import { ACQUISITIONS, COMPARISON_FIELDS } from "@/lib/case-data";

export default function AcquisitionsPage() {
  const { token, currentIncident, currentRole } = useAuth();
  const [acquisitions, setAcquisitions] = useState<ApiAcquisition[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAdd, setShowAdd] = useState(false);

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

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="font-mono text-xs tracking-[0.18em] text-[#d7b56d]">ACQUISITION REGISTRY</p>
          <h1 className="mt-2 text-3xl font-semibold">Acquisition Records</h1>
          <p className="mt-2 max-w-3xl text-sm text-[#c9d5cf]">
            Source catalog records and satellite granules. Comparability groups strictly match track, frame, polarization,
            and CRID. Do not mix provisional P05023 with P05036.
          </p>
        </div>

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

      {/* Historical Reference Pair Comparison */}
      <section className="space-y-4">
        <h2 className="text-xl font-medium">Historical Baseline NISAR Reference (Group D40)</h2>
        <div className="rounded-2xl border border-white/10 bg-[#121716]">
          <h3 className="px-4 pt-4 text-base font-medium">Granule Comparison</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-white/5 text-xs uppercase tracking-wide text-[#93a39b]">
                <tr>
                  <th className="px-4 py-3">Field</th>
                  {ACQUISITIONS.map((a) => (
                    <th key={a.iso} className="px-4 py-3">
                      {a.date}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr className="border-t border-white/10">
                  <th scope="row" className="px-4 py-3 font-medium">
                    Granule
                  </th>
                  {ACQUISITIONS.map((a) => (
                    <td key={a.granule} className="break-all px-4 py-3 font-mono text-xs">
                      {a.granule}
                    </td>
                  ))}
                </tr>
                <tr className="border-t border-white/10">
                  <th scope="row" className="px-4 py-3 font-medium">
                    Raw sweep-stable pixels
                  </th>
                  {ACQUISITIONS.map((a) => (
                    <td key={a.iso} className="px-4 py-3">
                      {a.rawStable}
                    </td>
                  ))}
                </tr>
                <tr className="border-t border-white/10">
                  <th scope="row" className="px-4 py-3 font-medium">
                    Filtered sweep-stable pixels
                  </th>
                  {ACQUISITIONS.map((a) => (
                    <td key={a.iso} className="px-4 py-3">
                      {a.filteredStable}
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-[#121716]">
          <h3 className="px-4 pt-4 text-base font-medium">Shared Metadata</h3>
          <div className="overflow-x-auto">
            <table className="w-full table-fixed text-left text-sm">
              <thead className="bg-white/5 text-xs uppercase tracking-wide text-[#93a39b]">
                <tr>
                  <th scope="col" className="w-[28%] px-4 py-3">
                    Field
                  </th>
                  {ACQUISITIONS.map((a) => (
                    <th scope="col" key={a.iso} className="px-4 py-3">
                      {a.date}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {COMPARISON_FIELDS.map((f) => (
                  <tr key={f.label} className="border-t border-white/10">
                    <th scope="row" className="px-4 py-3 align-top font-medium">
                      {f.label}
                    </th>
                    <td className="break-words px-4 py-3 align-top">{f.value}</td>
                    <td className="break-words px-4 py-3 align-top">{f.value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="px-4 pb-4 pt-2 text-sm text-[#93a39b]">
            Coordinate steps represent nominal grid posting. They do not establish independent spatial resolution cells.
          </p>
        </div>
      </section>

      {/* Discrepancies & Provenance Guardrails */}
      <section className="rounded-2xl border border-[#d7b56d]/40 bg-[#d7b56d]/10 p-5 text-sm text-[#f3e2b3]">
        <p className="font-medium">Acquisition Provenance Guardrails</p>
        <ul className="mt-2 list-disc space-y-1 pl-5">
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
