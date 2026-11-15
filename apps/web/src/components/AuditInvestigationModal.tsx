"use client";

import { useEffect, useState } from "react";
import type { InvestigatableAuditEvent } from "@/lib/audit-data";

interface AuditInvestigationModalProps {
  event: InvestigatableAuditEvent | null;
  onClose: () => void;
}

export function AuditInvestigationModal({ event, onClose }: AuditInvestigationModalProps) {
  const [activeTab, setActiveTab] = useState<"after" | "before" | "raw">("after");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (!event) return null;

  const handleCopy = (data: unknown) => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const actionColor =
    event.action.includes("INSERT")
      ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
      : event.action.includes("UPDATE")
      ? "bg-sky-500/20 text-sky-300 border-sky-500/30"
      : "bg-rose-500/20 text-rose-300 border-rose-500/30";

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 p-4 backdrop-blur-md transition-opacity"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="relative max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-3xl border border-white/15 bg-[#0e1413] p-6 shadow-2xl sm:p-8">
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          className="absolute right-5 top-5 flex h-8 w-8 items-center justify-center rounded-full border border-white/15 bg-white/5 text-sm text-[#c9d5cf] transition hover:bg-white/10 hover:text-white"
          aria-label="Close audit investigation modal"
        >
          ✕
        </button>

        {/* Header */}
        <div className="space-y-2 border-b border-white/10 pb-5">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs tracking-wider text-[#d7b56d]">
              IMMUTABLE AUDIT RECORD
            </span>
            <span className={`rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase ${actionColor}`}>
              {event.action}
            </span>
            <span className="rounded-full border border-[#d7b56d]/30 bg-[#d7b56d]/10 px-2.5 py-0.5 font-mono text-[11px] text-[#f3e2b3]">
              {event.entity_table}
            </span>
            <span className="rounded-full border border-white/15 bg-white/5 px-2 py-0.5 text-[10px] text-[#93a39b]">
              {event.category}
            </span>
          </div>

          <h2 className="text-xl font-bold text-white sm:text-2xl">
            Audit Event Investigation
          </h2>
          <p className="text-xs text-[#93a39b] leading-relaxed">
            {event.summary}
          </p>
        </div>

        {/* Actor Profile & Security Claims */}
        <div className="mt-5 grid gap-4 rounded-2xl border border-white/10 bg-[#121917] p-4 sm:grid-cols-2 text-xs">
          <div>
            <p className="text-[11px] uppercase tracking-wider text-[#93a39b]">
              Authenticated Investigator
            </p>
            <p className="mt-1 text-sm font-semibold text-white flex items-center gap-1.5">
              <span className="text-[#d7b56d]">👤</span> {event.actor_name}
            </p>
            <div className="mt-1 flex items-center gap-2">
              <span className="rounded bg-white/5 px-1.5 py-0.5 font-mono text-[10px] text-[#d7b56d] uppercase">
                Role: {event.actor_role}
              </span>
              <span className="text-[10px] text-[#556961]">
                Session Verified
              </span>
            </div>
            <p className="mt-1.5 font-mono text-[10px] text-[#556961] truncate" title={event.actor_id}>
              Actor UUID: {event.actor_id}
            </p>
          </div>

          <div className="border-t border-white/10 pt-3 sm:border-t-0 sm:border-l sm:pl-4 sm:pt-0">
            <p className="text-[11px] uppercase tracking-wider text-[#93a39b]">
              PostgreSQL Security Envelope
            </p>
            <div className="mt-1 space-y-1 font-mono text-[11px]">
              <p className="text-[#c9d5cf]">
                Trigger: <span className="text-emerald-400">private.write_audit_event()</span>
              </p>
              <p className="text-[#c9d5cf]">
                Mutation Guard: <span className="text-emerald-400">deny_audit_tampering</span>
              </p>
              <p className="text-[#93a39b] text-[10px]">
                Target Entity UUID: {event.entity_id}
              </p>
            </div>
          </div>
        </div>

        {/* Chronological Timestamp & Hash */}
        <div className="mt-4 grid gap-3 rounded-2xl border border-white/10 bg-[#101615] p-3 text-xs sm:grid-cols-2">
          <div>
            <span className="text-[11px] text-[#93a39b]">Occurred At (UTC):</span>
            <p className="font-mono text-white mt-0.5">{event.occurred_at}</p>
            <p className="text-[10px] text-[#556961]">
              Local: {new Date(event.occurred_at).toLocaleString()}
            </p>
          </div>
          <div>
            <span className="text-[11px] text-[#93a39b]">Cryptographic Seal Hash:</span>
            <p className="font-mono text-[10px] text-emerald-400 mt-0.5 truncate" title={event.tamper_seal_hash}>
              SHA-256: {event.tamper_seal_hash}
            </p>
            <p className="text-[10px] text-[#556961]">
              Immutable block verification passed
            </p>
          </div>
        </div>

        {/* Data Inspection Tabs */}
        <div className="mt-5 space-y-3">
          <div className="flex items-center justify-between border-b border-white/10 pb-2">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setActiveTab("after")}
                className={`rounded-lg px-3 py-1 text-xs font-medium transition ${
                  activeTab === "after"
                    ? "bg-[#d7b56d] text-[#1a1408] font-semibold"
                    : "text-[#93a39b] hover:text-white"
                }`}
              >
                Modified / New State (After)
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("before")}
                className={`rounded-lg px-3 py-1 text-xs font-medium transition ${
                  activeTab === "before"
                    ? "bg-[#d7b56d] text-[#1a1408] font-semibold"
                    : "text-[#93a39b] hover:text-white"
                }`}
              >
                Previous State (Before)
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("raw")}
                className={`rounded-lg px-3 py-1 text-xs font-medium transition ${
                  activeTab === "raw"
                    ? "bg-[#d7b56d] text-[#1a1408] font-semibold"
                    : "text-[#93a39b] hover:text-white"
                }`}
              >
                Full Envelope
              </button>
            </div>

            <button
              type="button"
              onClick={() => handleCopy(activeTab === "after" ? event.after_data : activeTab === "before" ? event.before_data : event)}
              className="flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-2.5 py-0.5 font-mono text-[10px] text-[#d7b56d] transition hover:bg-white/10"
            >
              {copied ? "✓ Copied JSON" : "📋 Copy JSON"}
            </button>
          </div>

          {/* Tab Content */}
          <div className="rounded-2xl border border-white/10 bg-[#090d0c] p-4">
            {activeTab === "after" ? (
              event.after_data ? (
                <pre className="max-h-64 overflow-auto font-mono text-xs text-[#d7e2dc]">
                  {JSON.stringify(event.after_data, null, 2)}
                </pre>
              ) : (
                <p className="text-xs text-[#93a39b] italic">
                  No subsequent state data recorded.
                </p>
              )
            ) : activeTab === "before" ? (
              event.before_data ? (
                <pre className="max-h-64 overflow-auto font-mono text-xs text-[#d7e2dc]">
                  {JSON.stringify(event.before_data, null, 2)}
                </pre>
              ) : (
                <div className="py-4 text-center text-xs text-[#93a39b]">
                  <p className="font-medium text-white">Initial Row Creation (INSERT)</p>
                  <p className="mt-0.5 text-[11px] text-[#556961]">
                    No previous state existed prior to this atomic transaction.
                  </p>
                </div>
              )
            ) : (
              <pre className="max-h-64 overflow-auto font-mono text-xs text-[#d7e2dc]">
                {JSON.stringify(event, null, 2)}
              </pre>
            )}
          </div>
        </div>

        {/* Footer Audit Guarantee */}
        <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-4 text-xs">
          <div className="flex items-center gap-2 text-[#93a39b]">
            <span className="text-emerald-400">🛡️</span>
            <span>Cryptographically sealed under PostgreSQL append-only security policy.</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full bg-[#d7b56d] px-5 py-1.5 font-semibold text-[#1a1408] transition hover:bg-[#c9a65c]"
          >
            Done Inspecting
          </button>
        </div>
      </div>
    </div>
  );
}
