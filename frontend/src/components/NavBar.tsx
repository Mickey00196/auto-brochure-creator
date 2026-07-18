import Link from "next/link";

const LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/buildings", label: "Buildings & Units" },
  { href: "/clients", label: "Clients" },
  { href: "/proposals", label: "Proposals" },
];

export function NavBar() {
  return (
    <header className="sticky top-0 z-10 border-b border-border bg-background/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-baseline gap-2">
          <span className="text-sm font-bold tracking-wide text-accent">OFFICE SHORTLIST</span>
          <span className="hidden text-sm text-muted sm:inline">Real Estate Proposal Engine</span>
        </Link>
        <nav className="flex gap-6 text-sm font-medium">
          {LINKS.map((link) => (
            <Link key={link.href} href={link.href} className="text-muted transition hover:text-foreground">
              {link.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
