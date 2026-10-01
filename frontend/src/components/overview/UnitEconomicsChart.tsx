import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatCurrency, formatMonthShort } from "../../lib/format";
import type { KpiSeriesPoint } from "../../lib/types";
import { CHART_COLORS, axisTickStyle, gridStroke, tooltipContentStyle } from "./chartTheme";

export function UnitEconomicsChart({ series }: { series: KpiSeriesPoint[] }) {
  const data = series.map((point) => ({
    month: formatMonthShort(point.month_label),
    "Revenue per Unit": point.revenue_per_unit,
    "Cost per Unit": point.total_cost_per_unit,
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid stroke={gridStroke} vertical={false} />
        <XAxis dataKey="month" tick={axisTickStyle} axisLine={{ stroke: gridStroke }} tickLine={false} />
        <YAxis
          tick={axisTickStyle}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v: number) => formatCurrency(v)}
          width={60}
        />
        <Tooltip contentStyle={tooltipContentStyle} formatter={(value) => formatCurrency(Number(value))} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line
          type="monotone"
          dataKey="Revenue per Unit"
          stroke={CHART_COLORS.budget}
          strokeWidth={2}
          dot={false}
        />
        <Line
          type="monotone"
          dataKey="Cost per Unit"
          stroke={CHART_COLORS.actual}
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
