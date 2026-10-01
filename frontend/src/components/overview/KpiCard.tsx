import { formatCurrencyK, formatPercent, formatPpoints, formatSignedPercent } from "../../lib/format";
import { ragStyle, targetPositionLabel } from "../../lib/status";
import type { KpiCard as KpiCardData } from "../../lib/types";

function formatValue(value: number, fmt: KpiCardData["fmt"]): string {
  return fmt === "currency" ? formatCurrencyK(value) : formatPercent(value);
}

function momText(card: KpiCardData): string {
  const { trend } = card;
  if (trend.delta === null) return "no prior month";
  return card.fmt === "pct" ? formatPpoints(trend.delta) : formatSignedPercent(trend.pct_change);
}

export function KpiCard({ card }: { card: KpiCardData }) {
  const style = ragStyle(card.rag);
  const position = targetPositionLabel(card.value, card.target);
  const targetPhrase = card.target_kind === "budget" ? "vs. Budget" : "vs. KPI Target";

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-sm">
      <div className={`mb-3 h-1 rounded-full ${style.dotClass}`} aria-hidden="true" />
      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-ink-secondary)]">
        {card.label}
      </p>
      <p className="mt-1 text-2xl font-bold text-[var(--color-navy)]">{formatValue(card.value, card.fmt)}</p>
      <p className="mt-0.5 text-xs text-[var(--color-ink-muted)]">
        {targetPhrase} {formatValue(card.target, card.fmt)}
      </p>
      <p className={`mt-3 text-xs font-semibold ${style.textClass}`}>
        Status: {position}
        <br />
        MoM: {momText(card)}
      </p>
    </div>
  );
}
