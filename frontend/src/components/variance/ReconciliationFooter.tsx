import { formatCurrency, formatSignedCurrencyK } from "../../lib/format";
import type { WaterfallReconciliation } from "../../lib/types";

export function ReconciliationFooter({ reconciliation }: { reconciliation: WaterfallReconciliation }) {
  const reconciles = Math.abs(reconciliation.difference ?? 0) < 0.01;
  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-1 rounded-lg bg-[var(--color-surface-muted)] px-4 py-3 text-xs text-[var(--color-ink-secondary)]">
      <span>
        Sum of drivers: <strong className="text-[var(--color-ink)]">{formatSignedCurrencyK(reconciliation.sum_components)}</strong>
      </span>
      <span>
        OI variance: <strong className="text-[var(--color-ink)]">{formatSignedCurrencyK(reconciliation.oi_variance)}</strong>
      </span>
      <span>
        Difference:{" "}
        <strong className={reconciles ? "text-[var(--color-good)]" : "text-[var(--color-critical)]"}>
          {formatCurrency(reconciliation.difference ?? 0)}
        </strong>
      </span>
      {reconciles ? (
        <span className="text-[var(--color-good)]">✓ Bridge reconciles exactly to the Operating Income variance</span>
      ) : null}
    </div>
  );
}
