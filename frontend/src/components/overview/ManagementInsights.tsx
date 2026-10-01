import type { ManagementInsights as ManagementInsightsData } from "../../lib/types";

export function ManagementInsights({ insights }: { insights: ManagementInsightsData }) {
  const rows: { label: string; text: string; colorClass: string }[] = [
    { label: "Top Favorable Driver", text: insights.top_favorable, colorClass: "text-[var(--color-good)]" },
    { label: "Top Unfavorable Driver", text: insights.top_unfavorable, colorClass: "text-[var(--color-critical)]" },
    { label: "Risk & Action", text: insights.risk_action, colorClass: "text-[var(--color-navy)]" },
  ];

  return (
    <dl className="grid gap-4 sm:grid-cols-3">
      {rows.map((row) => (
        <div key={row.label} className="rounded-lg bg-[var(--color-surface-muted)] p-4">
          <dt className="text-xs font-semibold uppercase tracking-wide text-[var(--color-ink-secondary)]">
            {row.label}
          </dt>
          <dd className={`mt-1.5 text-sm leading-relaxed ${row.colorClass}`}>{row.text}</dd>
        </div>
      ))}
    </dl>
  );
}
