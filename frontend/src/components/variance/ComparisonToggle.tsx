import type { Comparison } from "../../lib/types";

interface ComparisonToggleProps {
  value: Comparison;
  onChange: (value: Comparison) => void;
}

const OPTIONS: { value: Comparison; label: string }[] = [
  { value: "budget", label: "Actual vs. Budget" },
  { value: "forecast", label: "Actual vs. Forecast" },
];

export function ComparisonToggle({ value, onChange }: ComparisonToggleProps) {
  return (
    <div
      role="radiogroup"
      aria-label="Variance comparison basis"
      className="inline-flex rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-1"
    >
      {OPTIONS.map((option) => {
        const selected = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(option.value)}
            className={`rounded-md px-3.5 py-1.5 text-sm font-medium transition-colors ${
              selected
                ? "bg-[var(--color-navy)] text-white shadow-sm"
                : "text-[var(--color-ink-secondary)] hover:text-[var(--color-navy)]"
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
