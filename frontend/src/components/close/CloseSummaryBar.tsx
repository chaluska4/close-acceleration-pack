import type { CloseSummary, ControlsSummary } from "../../lib/types";

interface CloseSummaryBarProps {
  summary: CloseSummary;
  controlsSummary: ControlsSummary;
}

export function CloseSummaryBar({ summary, controlsSummary }: CloseSummaryBarProps) {
  const tiles = [
    { label: "Tasks Complete / Total", value: `${summary.tasks_complete} / ${summary.tasks_total}` },
    { label: "Open Tasks", value: summary.tasks_open },
    { label: "Current Close Day", value: `Day ${summary.current_close_day}` },
    {
      label: "Controls Effective",
      value: `${controlsSummary.controls_effective} / ${controlsSummary.controls_total}`,
    },
    {
      label: "Controls with Exceptions",
      value: controlsSummary.controls_exception,
      emphasize: controlsSummary.controls_exception > 0,
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      {tiles.map((tile) => (
        <div key={tile.label} className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3">
          <p className="text-xs font-medium text-[var(--color-ink-muted)]">{tile.label}</p>
          <p
            className={`mt-1 text-xl font-bold ${
              tile.emphasize ? "text-[var(--color-critical)]" : "text-[var(--color-navy)]"
            }`}
          >
            {tile.value}
          </p>
        </div>
      ))}
    </div>
  );
}
