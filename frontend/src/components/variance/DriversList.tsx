import { EmptyState } from "../ui/EmptyState";
import type { DriverEntry } from "../../lib/types";

interface DriversListProps {
  title: string;
  drivers: DriverEntry[];
  tone: "favorable" | "unfavorable";
}

export function DriversList({ title, drivers, tone }: DriversListProps) {
  const toneClass = tone === "favorable" ? "text-[var(--color-good)]" : "text-[var(--color-critical)]";
  const dotClass = tone === "favorable" ? "bg-[var(--color-good)]" : "bg-[var(--color-critical)]";

  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-ink-secondary)]">{title}</h3>
      {drivers.length === 0 ? (
        <EmptyState message="No material drivers this period." />
      ) : (
        <ul className="mt-2 flex flex-col gap-2">
          {drivers.map((driver) => (
            <li key={driver.line_item} className="flex items-center justify-between gap-3 text-sm">
              <span className="flex items-center gap-2 text-[var(--color-ink)]">
                <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${dotClass}`} aria-hidden="true" />
                {driver.line_item}
              </span>
              <span className={`font-semibold tabular-nums ${toneClass}`}>{driver.contribution_label}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
