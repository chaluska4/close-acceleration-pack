import { formatCurrency, formatSignedCurrencyK, formatSignedPercent } from "../../lib/format";
import { favorableTextClass } from "../../lib/status";
import type { VarianceComparison } from "../../lib/types";

export function PnlVarianceTable({ comparison }: { comparison: VarianceComparison }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-sm">
        <caption className="sr-only">
          P&amp;L variance table, Actual vs. {comparison.label}, with variance amount, variance percent, and
          materiality flag per line item
        </caption>
        <thead>
          <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase tracking-wide text-[var(--color-ink-muted)]">
            <th scope="col" className="py-2 pr-4 font-semibold">
              Line Item
            </th>
            <th scope="col" className="py-2 pr-4 text-right font-semibold">
              Actual
            </th>
            <th scope="col" className="py-2 pr-4 text-right font-semibold">
              {comparison.label}
            </th>
            <th scope="col" className="py-2 pr-4 text-right font-semibold">
              Variance $
            </th>
            <th scope="col" className="py-2 pr-4 text-right font-semibold">
              Variance %
            </th>
            <th scope="col" className="py-2 pl-2 text-center font-semibold">
              Material
            </th>
          </tr>
        </thead>
        <tbody>
          {comparison.rows.map((row) => (
            <tr
              key={row.line_item}
              className={`border-b border-[var(--color-border)] last:border-0 ${
                row.is_subtotal ? "bg-[var(--color-surface-muted)] font-semibold" : ""
              }`}
            >
              <th scope="row" className="py-2 pr-4 text-left font-medium text-[var(--color-navy)]">
                {row.line_item}
              </th>
              <td className="py-2 pr-4 text-right tabular-nums text-[var(--color-ink)]">
                {formatCurrency(row.actual)}
              </td>
              <td className="py-2 pr-4 text-right tabular-nums text-[var(--color-ink-secondary)]">
                {formatCurrency(row.comparison)}
              </td>
              <td className={`py-2 pr-4 text-right tabular-nums font-medium ${favorableTextClass(row.favorable)}`}>
                {formatSignedCurrencyK(row.variance)}
              </td>
              <td className={`py-2 pr-4 text-right tabular-nums ${favorableTextClass(row.favorable)}`}>
                {row.variance_pct === null ? "N/M" : formatSignedPercent(row.variance_pct)}
              </td>
              <td className="py-2 pl-2 text-center">
                {row.material ? (
                  <span
                    className="inline-block rounded-full bg-[var(--color-warning-bg)] px-2 py-0.5 text-xs font-semibold text-[var(--color-warning)]"
                    title="Breaches the materiality threshold (±5% or ±$10K)"
                  >
                    Material
                  </span>
                ) : (
                  <span className="text-xs text-[var(--color-ink-muted)]">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
