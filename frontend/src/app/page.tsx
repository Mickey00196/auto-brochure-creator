import Link from "next/link";
import { Button, Card } from "@/components/ui";

const PILLARS = [
  {
    title: "Import from URLs",
    description: "Paste a listing link and let extraction fill in the building & unit record for you.",
    href: "/import",
  },
  {
    title: "Buildings & Units",
    description: "One Building, many leasable Units — different floors, prices, and delivery conditions.",
    href: "/buildings",
  },
  {
    title: "Proposals",
    description: "A dated shortlist of units sent to a named client, ready to become a brochure.",
    href: "/proposals",
  },
];

export default function HomePage() {
  return (
    <div>
      <section className="flex flex-col items-center gap-6 py-16 text-center sm:py-24">
        <div className="text-xs font-bold uppercase tracking-wide text-accent">Office Shortlist</div>
        <h1 className="max-w-3xl text-4xl font-bold tracking-tight sm:text-6xl">
          The real estate brochure engine.
        </h1>
        <p className="max-w-xl text-lg text-muted">
          Turn a shortlist of office buildings into a client-ready proposal — import listings, curate units,
          and generate a polished brochure in minutes.
        </p>
        <div className="mt-2 flex flex-wrap items-center justify-center gap-3">
          <Link href="/dashboard">
            <Button variant="primary">Go to Dashboard</Button>
          </Link>
          <Link href="/buildings/new">
            <Button variant="ghost">+ Add Building</Button>
          </Link>
        </div>
      </section>

      <section className="grid gap-6 pb-16 sm:grid-cols-3">
        {PILLARS.map((pillar) => (
          <Link key={pillar.href} href={pillar.href}>
            <Card className="h-full transition hover:border-accent">
              <h2 className="text-lg font-semibold">{pillar.title}</h2>
              <p className="mt-2 text-sm text-muted">{pillar.description}</p>
            </Card>
          </Link>
        ))}
      </section>
    </div>
  );
}
