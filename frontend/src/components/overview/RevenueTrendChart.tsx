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
import { formatCurrencyK, formatMonthShort } from "../../lib/format";
import type { KpiSeriesPoint } from "../../lib/types";
import { CHART_COLORS, axisTickStyle, gridStroke, tooltipContentStyle } from "./chartTheme";

export function RevenueTrendChart({ series }: { series: KpiSeriesPoint[] }) {
  const data = series.map((point) => ({
    month: formatMonthShort(point.month_label),
    Actual: point.revenue_actual,
    Budget: point.revenue_budget,
    Forecast: point.revenue_forecast,
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
          tickFormatter={(v: number) => formatCurrencyK(v)}
          width={56}
        />
        <Tooltip
          contentStyle={tooltipContentStyle}
          formatter={(value) => formatCurrencyK(Number(value))}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line type="monotone" dataKey="Actual" stroke={CHART_COLORS.actual} strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="Budget" stroke={CHART_COLORS.budget} strokeWidth={2} dot={false} />
        <Line
          type="monotone"
          dataKey="Forecast"
          stroke={CHART_COLORS.forecast}
          strokeWidth={2}
          strokeDasharray="5 4"
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
