"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { AuthProvider, useAuth } from "@/lib/auth-context";

const navLinks = [
  { href: "/", label: "Overview" },
  { href: "/spatial", label: "Spatial" },
  { href: "/acquisitions", label: "Acquisitions" },
  { href: "/evidence", label: "Evidence" },
  { href: "/jobs", label: "Worker Jobs" },
  { href: "/reviews", label: "Reviews" },
  { href: "/report", label: "Report" },
  { href: "/audit", label: "Audit" },
];

function ShellInner({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { user, incidents, currentIncident, setCurrentIncident, currentRole, signOut, loading } = useAuth();

  return (
    <div className="min-h-screen">
      <a
        href="#content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-[#d7b56d] focus:px-3 focus:py-2 focus:text-black"
      >
        Skip to content
      </a>
      <header className="no-print sticky top-0 z-40 border-b border-white/10 bg-[#0b0f0e]/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-3 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="flex items-baseline gap-3 rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#d7b56d]"
            >
              <span className="font-mono text-base font-bold tracking-[0.24em] text-[#d7b56d]">RIVET</span>
              <span className="hidden text-xs text-[#93a39b] sm:inline">SAR Investigation</span>
            </Link>

            {user && incidents.length > 0 ? (
              <div className="flex items-center gap-2">
                <span className="text-xs text-[#93a39b]">Incident:</span>
                <select
                  value={currentIncident?.id || ""}
                  onChange={(e) => {
                    const found = incidents.find((i) => i.id === e.target.value);
                    setCurrentIncident(found || null);
                  }}
                  className="rounded-lg border border-white/15 bg-[#121716] px-2.5 py-1 text-xs text-white focus:border-[#d7b56d] focus:outline-none"
                >
                  {incidents.map((inc) => (
                    <option key={inc.id} value={inc.id}>
                      {inc.title}
                    </option>
                  ))}
                </select>
                {currentRole ? (
                  <span className="rounded-md border border-[#d7b56d]/30 bg-[#d7b56d]/10 px-2 py-0.5 font-mono text-[11px] font-medium uppercase text-[#f3e2b3]">
                    {currentRole}
                  </span>
                ) : null}
              </div>
            ) : null}
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <nav aria-label="Investigation" className="flex flex-wrap gap-1.5 text-xs">
              {navLinks.map((link) => {
                const active = pathname === link.href;
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    aria-current={active ? "page" : undefined}
                    className={`rounded-full border px-3 py-1 transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#d7b56d] ${
                      active
                        ? "border-[#d7b56d] bg-[#d7b56d]/10 text-white"
                        : "border-white/10 text-[#c9d5cf] hover:border-[#d7b56d]/60 hover:text-white"
                    }`}
                  >
                    {link.label}
                  </Link>
                );
              })}
            </nav>

            <div className="flex items-center gap-2 border-l border-white/10 pl-3">
              {loading ? (
                <span className="text-xs text-[#93a39b]">...</span>
              ) : user ? (
                <div className="flex items-center gap-2">
                  <span className="hidden font-mono text-xs text-[#c9d5cf] lg:inline" title={user.id}>
                    {user.email}
                  </span>
                  <button
                    type="button"
                    onClick={signOut}
                    className="rounded-full border border-white/15 px-3 py-1 text-xs text-[#c9d5cf] transition hover:border-[#d7b56d] hover:text-white"
                  >
                    Sign Out
                  </button>
                </div>
              ) : (
                <Link
                  href="/login"
                  className="rounded-full bg-[#d7b56d] px-3.5 py-1 text-xs font-semibold text-[#1a1408] transition hover:bg-[#c9a65c]"
                >
                  Sign In
                </Link>
              )}
            </div>
          </div>
        </div>
      </header>
      <main id="content" className="mx-auto max-w-7xl px-4 py-8">
        {children}
      </main>
    </div>
  );
}

export function Shell({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <ShellInner>{children}</ShellInner>
    </AuthProvider>
  );
}
