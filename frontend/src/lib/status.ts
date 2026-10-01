import type { ControlStatus, Rag, TaskStatus } from "./types";

// Centralized status -> Tailwind class mapping. Every component that shows
// a RAG badge, a task-status pill, or a control-status pill pulls from
// here, so "what does red mean" stays defined in exactly one place.

export interface StatusStyle {
  label: string;
  badgeClass: string;
  dotClass: string;
  textClass: string;
}

// RAG drives COLOR only. The "Green"/"Amber"/"Red" name is not shown as
// text anywhere — a KPI card's visible status word (e.g. "Above Target")
// is a separate, direction-agnostic positional label (see
// targetPositionLabel below), because for a lower-is-better KPI (cost per
// unit), Green means the value is AT OR BELOW target, not "above" it. RAG
// color is what tells the reader whether that position is good or bad.
const RAG_STYLES: Record<Rag, StatusStyle> = {
  Green: {
    label: "Green",
    badgeClass: "bg-[var(--color-good-bg)] text-[var(--color-good)]",
    dotClass: "bg-[var(--color-good)]",
    textClass: "text-[var(--color-good)]",
  },
  Amber: {
    label: "Amber",
    badgeClass: "bg-[var(--color-warning-bg)] text-[var(--color-warning)]",
    dotClass: "bg-[var(--color-warning)]",
    textClass: "text-[var(--color-warning)]",
  },
  Red: {
    label: "Red",
    badgeClass: "bg-[var(--color-critical-bg)] text-[var(--color-critical)]",
    dotClass: "bg-[var(--color-critical)]",
    textClass: "text-[var(--color-critical)]",
  },
  "N/A": {
    label: "N/A",
    badgeClass: "bg-slate-100 text-slate-500",
    dotClass: "bg-slate-400",
    textClass: "text-slate-500",
  },
};

export function ragStyle(rag: Rag): StatusStyle {
  return RAG_STYLES[rag];
}

/** Plain positional language for where `value` sits vs `target` — a fact,
 * not a favorability judgment (RAG color carries that). Mirrors
 * close_pack/excel_export.py's _card_status_label() exactly, so the web
 * app and the KPI Dashboard workbook describe the same card the same way. */
export function targetPositionLabel(value: number, target: number): string {
  if (target === 0) {
    if (value === 0) return "On Target";
    return value > 0 ? "Above Target" : "Under Target";
  }
  const relativeDiff = (value - target) / Math.abs(target);
  if (Math.abs(relativeDiff) < 0.005) return "On Target";
  return value > target ? "Above Target" : "Under Target";
}

const TASK_STATUS_STYLES: Record<TaskStatus, StatusStyle> = {
  Complete: {
    label: "Complete",
    badgeClass: "bg-[var(--color-good-bg)] text-[var(--color-good)]",
    dotClass: "bg-[var(--color-good)]",
    textClass: "text-[var(--color-good)]",
  },
  "In Progress": {
    label: "In Progress",
    badgeClass: "bg-[var(--color-accent-light)] text-[var(--color-accent)]",
    dotClass: "bg-[var(--color-accent)]",
    textClass: "text-[var(--color-accent)]",
  },
  Exception: {
    label: "Exception",
    badgeClass: "bg-[var(--color-critical-bg)] text-[var(--color-critical)]",
    dotClass: "bg-[var(--color-critical)]",
    textClass: "text-[var(--color-critical)]",
  },
  Blocked: {
    label: "Blocked",
    badgeClass: "bg-[var(--color-critical-bg)] text-[var(--color-critical)]",
    dotClass: "bg-[var(--color-critical)]",
    textClass: "text-[var(--color-critical)]",
  },
  "Not Started": {
    label: "Not Started",
    badgeClass: "bg-slate-100 text-slate-500",
    dotClass: "bg-slate-400",
    textClass: "text-slate-500",
  },
};

export function taskStatusStyle(status: TaskStatus): StatusStyle {
  return TASK_STATUS_STYLES[status];
}

const CONTROL_STATUS_STYLES: Record<ControlStatus, StatusStyle> = {
  Effective: {
    label: "Effective",
    badgeClass: "bg-[var(--color-good-bg)] text-[var(--color-good)]",
    dotClass: "bg-[var(--color-good)]",
    textClass: "text-[var(--color-good)]",
  },
  Exception: {
    label: "Exception",
    badgeClass: "bg-[var(--color-critical-bg)] text-[var(--color-critical)]",
    dotClass: "bg-[var(--color-critical)]",
    textClass: "text-[var(--color-critical)]",
  },
};

export function controlStatusStyle(status: ControlStatus): StatusStyle {
  return CONTROL_STATUS_STYLES[status];
}

export function favorableTextClass(favorable: boolean | null): string {
  if (favorable === null) return "text-[var(--color-ink-secondary)]";
  return favorable ? "text-[var(--color-good)]" : "text-[var(--color-critical)]";
}
