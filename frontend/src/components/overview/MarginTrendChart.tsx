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
import { formatMonthShort, formatPercent } from "../../lib/format";
import type { KpiSeriesPoint } from "../../lib/types";
import { CHART_COLORS, axisTickStyle, gridStroke, tooltipContentStyle } from "./chartTheme";

export function MarginTrendChart({ series }: { series: KpiSeriesPoint[] }) {
  const data = series.map((point) => ({
    month: formatMonthShort(point.month_label),
    "Gross Margin %": point.gross_margin_pct,
    "Operating Margin %": point.operating_margin_pct,
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
          tickFormatter={(v: number) => formatPercent(v, 0)}
          width={48}
        />
        <Tooltip contentStyle={tooltipContentStyle} formatter={(value) => formatPercent(Number(value))} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line
          type="monotone"
          dataKey="Gross Margin %"
          stroke={CHART_COLORS.budget}
          strokeWidth={2}
          dot={false}
        />
        <Line
          type="monotone"
          dataKey="Operating Margin %"
          stroke={CHART_COLORS.actual}
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
