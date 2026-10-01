import type { CSSProperties } from "react";

// Shared recharts styling so all dashboard charts look like one family —
// navy/blue only (green/red are reserved for favorable/unfavorable and
// status meaning elsewhere in the app, never used as an arbitrary series
// color here).
export const CHART_COLORS = {
  actual: "#1f2a44", // navy
  budget: "#2d5fb0", // accent blue
  forecast: "#94a3b8", // slate (muted — a plan, not a result)
  secondary: "#1f2a44",
};

export const axisTickStyle = { fontSize: 12, fill: "#52514e" };
export const gridStroke = "#e3e6ea";
export const tooltipContentStyle: CSSProperties = {
  borderRadius: 8,
  border: "1px solid #e3e6ea",
  fontSize: 13,
  boxShadow: "0 4px 12px rgba(15, 23, 42, 0.08)",
};
