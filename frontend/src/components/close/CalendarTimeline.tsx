import type { CalendarTask } from "../../lib/types";
import { TaskRow } from "./TaskRow";

function groupByDay(tasks: CalendarTask[]): Map<number, CalendarTask[]> {
  const groups = new Map<number, CalendarTask[]>();
  for (const task of tasks) {
    const group = groups.get(task.day) ?? [];
    group.push(task);
    groups.set(task.day, group);
  }
  return groups;
}

export function CalendarTimeline({ tasks, currentDay }: { tasks: CalendarTask[]; currentDay: number }) {
  const days = Array.from(groupByDay(tasks).entries()).sort(([a], [b]) => a - b);

  return (
    <ol className="flex flex-col gap-6">
      {days.map(([day, dayTasks]) => (
        <li key={day}>
          <div className="mb-2 flex items-center gap-2">
            <span
              className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold ${
                day === currentDay
                  ? "bg-[var(--color-navy)] text-white"
                  : "bg-[var(--color-surface-muted)] text-[var(--color-ink-secondary)]"
              }`}
              aria-hidden="true"
            >
              {day}
            </span>
            <h3 className="text-sm font-semibold text-[var(--color-navy)]">
              Day {day}
              {day === currentDay ? <span className="ml-2 text-xs font-normal text-[var(--color-accent)]">— current</span> : null}
            </h3>
          </div>
          <ul className="flex flex-col gap-3 border-l-2 border-[var(--color-border)] pl-5">
            {dayTasks.map((task) => (
              <TaskRow key={task.task_id} task={task} />
            ))}
          </ul>
        </li>
      ))}
    </ol>
  );
}
