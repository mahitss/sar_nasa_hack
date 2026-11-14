import Link from "next/link";

const links = [
  { href: "/", label: "Dashboard" },
  { href: "/map", label: "Map" },
  { href: "/evidence", label: "Evidence" },
  { href: "/review", label: "Review" },
  { href: "/report", label: "Report" },
];

export function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <header className="no-print border-b border-white/10 bg-[#101816]/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-4 md:flex-row md:items-center md:justify-between">
          <Link href="/" className="flex items-baseline gap-3">
            <span className="font-mono text-sm tracking-[0.22em] text-[#d7b56d]">RIVET</span>
            <span className="text-sm text-[#c9d5cf]">Kuwari investigation</span>
          </Link>
          <nav className="flex flex-wrap gap-2 text-sm">
            {links.map((link) => (
              <Link key={link.href} href={link.href} className="rounded-full border border-white/10 px-3 py-1 text-[#d7e2dc] hover:border-[#d7b56d] hover:text-white">
                {link.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
    </div>
  );
}
