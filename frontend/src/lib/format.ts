// Finance formatting helpers. These mirror the conventions already
// established in the Python backend (close_pack/variance.py format_k,
// close_pack/kpi.py _format_value) so a number reads identically here and
// in the Excel deliverables — never reformatted to a different convention
// just because it's now on a web page.

/** 83268 -> "$83K"; -58521 -> "-$59K"; 476 -> "$476" (amounts under $1,000
 * fall back to whole dollars rather than misleadingly rounding to "$0K"). */
export function formatCurrencyK(amount: number | null | undefined): string {
  if (amount === null || amount === undefined || Number.isNaN(amount)) return "N/M";
  const sign = amount < 0 ? "-" : "";
  const magnitude = Math.abs(amount);
  if (magnitude < 1_000) {
    return `${sign}$${magnitude.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
  }
  return `${sign}$${(magnitude / 1000).toLocaleString("en-US", { maximumFractionDigits: 0 })}K`;
}

/** Full-precision dollar amount, e.g. 775349.93 -> "$775,350". */
export function formatCurrency(amount: number | null | undefined): string {
  if (amount === null || amount === undefined || Number.isNaN(amount)) return "N/M";
  return amount.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

/** 0.4209 -> "42.1%". */
export function formatPercent(value: number | null | undefined, decimals = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "N/M";
  return `${(value * 100).toFixed(decimals)}%`;
}

/** 0.0829 -> "+8.3%"; -0.0202 -> "-2.0%" — always signed, for variance/trend display. */
export function formatSignedPercent(value: number | null | undefined, decimals = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "N/M";
  const pct = value * 100;
  const sign = pct >= 0 ? "+" : "";
  return `${sign}${pct.toFixed(decimals)}%`;
}

/** Percentage-point delta, e.g. 0.0208 -> "+2.1 pts". Used for MoM moves on
 * margin/ratio KPIs, where a relative-percent-of-a-percent is confusing. */
export function formatPpoints(value: number | null | undefined, decimals = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "N/M";
  const pts = value * 100;
  const sign = pts >= 0 ? "+" : "";
  return `${sign}${pts.toFixed(decimals)} pts`;
}

/** Signed dollar amount at $K scale, e.g. -83268 -> "-$83K", 27549 -> "+$28K". */
export function formatSignedCurrencyK(amount: number | null | undefined): string {
  if (amount === null || amount === undefined || Number.isNaN(amount)) return "N/M";
  const formatted = formatCurrencyK(Math.abs(amount));
  if (amount === 0) return formatted;
  return amount > 0 ? `+${formatted}` : `-${formatted}`;
}

/** 0.0241 absolute gap between two ratios -> "+241 bps". */
export function formatBps(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "N/M";
  const bps = value * 10_000;
  const sign = bps >= 0 ? "+" : "";
  return `${sign}${bps.toFixed(0)} bps`;
}

export function formatMonthShort(monthLabel: string): string {
  // "December 2025" -> "Dec"
  return monthLabel.split(" ")[0]?.slice(0, 3) ?? monthLabel;
}
