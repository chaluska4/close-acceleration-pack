import { Card, CardHeader } from "../components/ui/Card";
import { CalendarTimeline } from "../components/close/CalendarTimeline";
import { CloseSummaryBar } from "../components/close/CloseSummaryBar";
import { ControlsTable } from "../components/close/ControlsTable";
import { getClose } from "../lib/adapter";

export function Close() {
  const close = getClose();

  return (
    <div className="flex flex-col gap-6">
      <CloseSummaryBar summary={close.summary} controlsSummary={close.controls_summary} />

      <Card as="section" aria-labelledby="close-calendar-heading">
        <CardHeader
          title={<span id="close-calendar-heading">Month-End Close Calendar</span>}
          subtitle={`Day 1–5 · ${close.period_label} · a task can't stay Complete or In Progress while a prerequisite is unresolved — it becomes Blocked instead`}
        />
        <div className="p-5">
          <CalendarTimeline tasks={close.calendar} currentDay={close.summary.current_close_day} />
        </div>
      </Card>

      <Card as="section" aria-labelledby="controls-log-heading">
        <CardHeader
          title={<span id="controls-log-heading">Controls Log</span>}
          subtitle="Completeness, Accuracy, and Authorization controls — evaluated live against the dataset where a data trail exists"
        />
        <div className="p-5">
          <ControlsTable controls={close.controls} />
        </div>
      </Card>
    </div>
  );
}
