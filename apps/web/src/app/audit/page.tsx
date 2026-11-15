"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth-context";
import { listAuditEvents, type ApiAuditEvent } from "@/lib/api";

export default function AuditPage() {
  const { token, currentIncident } = useAuth();
  const [events, setEvents] = useState<ApiAuditEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState("");

  const fetchEvents = useCallback(async () => {
    if (!token || !currentIncident) {
      setEvents([]);
      return;
    }
    setLoading(true);
    try {
      const data = await listAuditEvents(token, currentIncident.id);
      setEvents(data || []);
    } catch {
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }, [token, currentIncident]);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  const filteredEvents = events.filter((e) => {
    const q = query.trim().toLowerCase();
    return (
      q === "" ||
      e.id.toLowerCase().includes(q) ||
      e.action.toLowerCase().includes(q) ||
      e.entity_table.toLowerCase().includes(q) ||
      e.entity_id.toLowerCase().includes(q) ||
      e.actor_id.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="font-mono text-xs tracking-[0.18em] text-[#d7b56d]">AUDIT TRAIL</p>
          <h1 className="mt-2 text-3xl font-semibold">Incident Audit History</h1>
          <p className="mt-2 max-w-3xl text-sm text-[#c9d5cf]">
            Every change to incidents, acquisitions, evidence, review decisions, and processing runs triggers an
            immutable audit event recorded by PostgreSQL database triggers.
          </p>
        </div>

        <button
          type="button"
          onClick={fetchEvents}
          className="rounded-full border border-white/15 px-4 py-1.5 text-xs text-[#c9d5cf] hover:border-[#d7b56d]"
        >
          Refresh Log ↻
        </button>
      </div>

      {/* Security Properties Alert */}
      <section className="rounded-2xl border border-white/10 bg-[#121716] p-4 text-xs text-[#c9d5cf]">
        <p className="font-semibold text-white">Database Audit Immutability Guarantees:</p>
        <p className="mt-1">
          The <code>public.audit_events</code> table is append-only. UPDATE and DELETE statements are strictly rejected
          by database triggers (<code>deny_audit_tampering</code>). Actor identity is automatically captured via
          transaction session claims.
        </p>
      </section>

      {/* Search Input */}
      <div>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Filter by table, action, actor UUID, entity ID..."
          className="w-full rounded-xl border border-white/15 bg-[#101816] px-3.5 py-2.5 text-sm text-white placeholder-[#556961] focus:border-[#d7b56d] focus:outline-none"
        />
      </div>

      {/* Audit Events Table */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-medium">Persisted Audit Events ({filteredEvents.length})</h2>
          {currentIncident ? (
            <span className="font-mono text-xs text-[#93a39b]">Incident: {currentIncident.title}</span>
          ) : null}
        </div>

        {loading && events.length === 0 ? (
          <p className="text-sm text-[#93a39b]">Loading audit events from PostgreSQL...</p>
        ) : filteredEvents.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-white/15 p-6 text-center text-sm text-[#c9d5cf]">
            No audit events recorded for this incident yet.
          </div>
        ) : (
          <div className="overflow-x-auto rounded-2xl border border-white/10 bg-[#121716]">
            <table className="w-full text-left text-xs">
              <thead className="bg-white/5 text-[11px] uppercase tracking-wide text-[#93a39b]">
                <tr>
                  <th className="px-4 py-3">Timestamp</th>
                  <th className="px-4 py-3">Action</th>
                  <th className="px-4 py-3">Table</th>
                  <th className="px-4 py-3">Entity ID</th>
                  <th className="px-4 py-3">Actor ID</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10 font-mono">
                {filteredEvents.map((ev) => (
                  <tr key={ev.id} className="hover:bg-white/[0.02]">
                    <td className="px-4 py-3 text-[#c9d5cf]">
                      {new Date(ev.occurred_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${
                          ev.action === "INSERT"
                            ? "bg-emerald-500/20 text-emerald-300"
                            : ev.action === "UPDATE"
                            ? "bg-sky-500/20 text-sky-300"
                            : "bg-rose-500/20 text-rose-300"
                        }`}
                      >
                        {ev.action}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-[#d7b56d]">{ev.entity_table}</td>
                    <td className="px-4 py-3 text-white" title={ev.entity_id}>
                      {ev.entity_id.slice(0, 12)}...
                    </td>
                    <td className="px-4 py-3 text-[#93a39b]" title={ev.actor_id}>
                      {ev.actor_id ? `${ev.actor_id.slice(0, 12)}...` : "system"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
