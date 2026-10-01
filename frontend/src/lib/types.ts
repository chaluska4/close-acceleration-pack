// Types mirror the JSON shape written by scripts/export_frontend_data.py
// field-for-field. If the export script's payload changes, update here —
// this is the only place the frontend encodes that contract.

export type Rag = "Green" | "Amber" | "Red" | "N/A";
export type KpiFormat = "currency" | "pct";
export type Direction = "higher_is_better" | "lower_is_better";
export type TargetKind = "budget" | "kpi_target";
export type Comparison = "budget" | "forecast";

export interface Meta {
  product_name: string;
  company_name: string;
  company_name_full: string;
  current_period: string;
  current_period_label: string;
  data_disclosure: string;
  github_url: string;
  generated_at: string;
}

export interface KpiTrend {
  delta: number | null;
  pct_change: number | null;
  favorable: boolean | null;
}

export interface KpiCard {
  key: string;
  label: string;
  value: number;
  target: number;
  target_kind: TargetKind;
  direction: Direction;
  fmt: KpiFormat;
  rag: Rag;
  prior: number | null;
  trend: KpiTrend;
}

export interface KpiSeriesPoint {
  month: string;
  month_label: string;
  revenue_actual: number;
  revenue_budget: number;
  revenue_forecast: number;
  gross_margin_pct: number;
  operating_margin_pct: number;
  revenue_per_unit: number;
  total_cost_per_unit: number;
}

export interface KpisPayload {
  cards: KpiCard[];
  series: KpiSeriesPoint[];
}

export interface ManagementInsights {
  top_favorable: string;
  top_unfavorable: string;
  risk_action: string;
}

export interface VarianceRow {
  line_item: string;
  is_subtotal: boolean;
  actual: number | null;
  comparison: number | null;
  variance: number | null;
  variance_pct: number | null;
  favorable: boolean | null;
  material: boolean;
}

export interface DriverEntry {
  line_item: string;
  contribution: number | null;
  contribution_label: string;
}

export interface VarianceComparison {
  label: string;
  rows: VarianceRow[];
  top_favorable: DriverEntry[];
  top_unfavorable: DriverEntry[];
}

export interface WaterfallComponent {
  line_item: string;
  contribution: number | null;
  contribution_label: string;
}

export interface WaterfallReconciliation {
  sum_components: number | null;
  oi_variance: number | null;
  difference: number | null;
}

export interface Waterfall {
  components: WaterfallComponent[];
  reconciliation: WaterfallReconciliation;
  budget_oi: number | null;
  actual_oi: number | null;
}

export interface VariancePayload {
  month: string;
  month_label: string;
  threshold_pct: number;
  threshold_abs: number;
  convention_note: string;
  narrative: {
    headline: string;
    management_summary: string;
  };
  waterfall: Waterfall;
  comparisons: Record<Comparison, VarianceComparison>;
}

export type TaskStatus =
  | "Complete"
  | "In Progress"
  | "Exception"
  | "Blocked"
  | "Not Started";

export interface CalendarTask {
  task_id: string;
  day: number;
  task: string;
  owner: string;
  reviewer: string;
  dependency: string;
  depends_on: string[];
  evidence_ref: string;
  status: TaskStatus;
  exception_notes: string;
  approved_workaround: string;
}

export interface CloseSummary {
  tasks_complete: number;
  tasks_total: number;
  tasks_open: number;
  exception_tasks: number;
  blocked_tasks: number;
  current_close_day: number;
}

export type ControlStatus = "Effective" | "Exception";
export type ControlCategory = "Completeness" | "Accuracy" | "Authorization";

export interface ControlRow {
  control_id: string;
  category: ControlCategory;
  process_area: string;
  risk: string;
  control_activity: string;
  owner: string;
  reviewer: string;
  frequency: string;
  evidence_ref: string;
  status: ControlStatus;
  detail: string;
  exception_remediation: string;
}

export interface ControlsSummary {
  controls_total: number;
  controls_effective: number;
  controls_exception: number;
}

export interface ClosePayload {
  period_label: string;
  summary: CloseSummary;
  calendar: CalendarTask[];
  controls_summary: ControlsSummary;
  controls: ControlRow[];
}
