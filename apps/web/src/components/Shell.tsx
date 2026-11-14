"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

const links = [
  { href: "/", label: "Overview" },
  { href: "/spatial", label: "Spatial" },
  { href: "/acquisitions", label: "Acquisitions" },
  { href: "/evidence", label: "Evidence" },
  { href: "/report", label: "Report" },
];

export function Shell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="min-h-screen">
      <a
        href="#content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-[#d7b56d] focus:px-3 focus:py-2 focus:text-black"
      >
        Skip to content
      </a>
      <header className="no-print sticky top-0 z-40 border-b border-white/10 bg-[#0b0f0e]/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-3 md:flex-row md:items-center md:justify-between">
          <Link href="/" className="flex items-baseline gap-3 rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#d7b56d]">
            <span className="font-mono text-sm tracking-[0.22em] text-[#d7b56d]">RIVET</span>
            <span className="text-sm text-[#93a39b]">Kuwari investigation</span>
          </Link>
          <nav aria-label="Investigation" className="flex flex-wrap gap-2 text-sm">
            {links.map((link) => {
              const active = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  aria-current={active ? "page" : undefined}
                  className={`rounded-full border px-3 py-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#d7b56d] ${
                    active ? "border-[#d7b56d] text-white" : "border-white/10 text-[#c9d5cf] hover:border-[#d7b56d]"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </header>
      <main id="content" className="mx-auto max-w-7xl px-4 py-8">{children}</main>
    </div>
  );
}
