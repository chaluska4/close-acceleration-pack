import { Badge } from "../ui/Badge";
import { taskStatusStyle } from "../../lib/status";
import type { CalendarTask } from "../../lib/types";

const NEEDS_CALLOUT: CalendarTask["status"][] = ["Exception", "Blocked"];

export function TaskRow({ task }: { task: CalendarTask }) {
  const style = taskStatusStyle(task.status);
  const showCallout = NEEDS_CALLOUT.includes(task.status) && task.exception_notes;

  return (
    <li className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-medium text-[var(--color-navy)]">{task.task}</p>
          <p className="mt-1 text-xs text-[var(--color-ink-muted)]">
            Owner: <span className="text-[var(--color-ink-secondary)]">{task.owner}</span> &middot; Reviewer:{" "}
            <span className="text-[var(--color-ink-secondary)]">{task.reviewer}</span>
          </p>
          <p className="mt-1 text-xs text-[var(--color-ink-muted)]">
            Dependency: <span className="text-[var(--color-ink-secondary)]">{task.dependency}</span>
          </p>
        </div>
        <Badge className={style.badgeClass} dotClassName={style.dotClass}>
          {style.label}
        </Badge>
      </div>

      {showCallout ? (
        <p className="mt-3 rounded-md border-l-4 border-l-[var(--color-critical)] bg-[var(--color-critical-bg)] px-3 py-2 text-xs leading-relaxed text-[var(--color-ink)]">
          {task.exception_notes}
        </p>
      ) : null}
    </li>
  );
}
