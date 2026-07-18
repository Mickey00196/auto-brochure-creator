import type { ComparisonRow } from "@/lib/types";
import { Badge, Card } from "@/components/ui";
import { formatArea, formatMoney, formatRate } from "@/lib/format";

export function ComparisonTable({ rows }: { rows: ComparisonRow[] }) {
  return (
    <Card>
      <h2 className="text-lg font-semibold">§16 Comparison</h2>
      <p className="mt-1 text-sm text-muted">
        All-in rate and estimated annual cost are computed, not hand-typed — sorted ascending by all-in rate, TBD
        rows last.
      </p>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[720px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
              <th className="pb-2 pr-4">Location</th>
              <th className="pb-2 pr-4">Floor</th>
              <th className="pb-2 pr-4">Area</th>
              <th className="pb-2 pr-4">All-in €/m²/yr</th>
              <th className="pb-2 pr-4">Est. Annual Cost</th>
              <th className="pb-2">Energy</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.unit_id} className="border-b border-border/60 last:border-none">
                <td className="py-2 pr-4">{row.building_name}</td>
                <td className="py-2 pr-4">{row.floor ?? "—"}</td>
                <td className="py-2 pr-4">{formatArea(row.available_area_m2)}</td>
                <td className="py-2 pr-4 font-semibold">
                  {row.is_tbd ? <Badge tone="warn">TBD</Badge> : formatRate(row.all_in_rate_eur_per_m2_year)}
                </td>
                <td className="py-2 pr-4">{row.is_tbd ? "TBD" : formatMoney(row.estimated_annual_cost_eur)}</td>
                <td className="py-2">{row.energy_label ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
