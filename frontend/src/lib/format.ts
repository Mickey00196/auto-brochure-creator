export function formatMoney(value: number | null | undefined): string {
  if (value === null || value === undefined) return "TBD";
  return `€${value.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}

export function formatRate(value: number | null | undefined): string {
  if (value === null || value === undefined) return "TBD";
  return `${formatMoney(value)}/m²/yr`;
}

// §24 — TBD renders cleanly as "TBD", never blank, zero, or a crash.
export function formatRent(value: number | null | undefined, priceType: string): string {
  if (priceType === "tbd" || value === null || value === undefined) return "TBD";
  if (priceType === "on_request") return "On request";
  const prefix = priceType === "from" ? "from " : "";
  return `${prefix}${formatRate(value)}`;
}

export function formatArea(value: number): string {
  return `${value.toLocaleString("en-US", { maximumFractionDigits: 0 })} m²`;
}
