import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatCurrencyK } from "../../lib/format";
import type { Waterfall } from "../../lib/types";
import { axisTickStyle, gridStroke, tooltipContentStyle } from "../overview/chartTheme";

interface WaterfallBar {
  name: string;
  base: number;
  delta: number;
  isTotal: boolean;
  favorable: boolean | null;
  rawContribution: number | null;
}

const GOOD = "#0ca30c";
const CRITICAL = "#d03b3b";
const NAVY = "#1f2a44";

function buildBars(waterfall: Waterfall): WaterfallBar[] {
  const bars: WaterfallBar[] = [];
  const budgetOi = waterfall.budget_oi ?? 0;
  bars.push({ name: "Budget OI", base: 0, delta: budgetOi, isTotal: true, favorable: null, rawContribution: null });

  let running = budgetOi;
  for (const component of waterfall.components) {
    const contribution = component.contribution ?? 0;
    const base = Math.min(running, running + contribution);
    bars.push({
      name: component.line_item,
      base,
      delta: Math.abs(contribution),
      isTotal: false,
      favorable: contribution >= 0,
      rawContribution: contribution,
    });
    running += contribution;
  }

  bars.push({ name: "Actual OI", base: 0, delta: waterfall.actual_oi ?? running, isTotal: true, favorable: null, rawContribution: null });
  return bars;
}

function barFill(bar: WaterfallBar): string {
  if (bar.isTotal) return NAVY;
  return bar.favorable ? GOOD : CRITICAL;
}

interface TooltipPayloadItem {
  payload: WaterfallBar;
}

function WaterfallTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayloadItem[] }) {
  if (!active || !payload?.length) return null;
  const bar = payload[0]?.payload;
  if (!bar) return null;
  const value = bar.isTotal ? bar.delta : bar.rawContribution ?? 0;
  return (
    <div style={tooltipContentStyle} className="bg-white px-3 py-2">
      <p className="font-semibold text-[var(--color-navy)]">{bar.name}</p>
      <p className="tabular-nums">{formatCurrencyK(value)}</p>
    </div>
  );
}

export function WaterfallChart({ waterfall }: { waterfall: Waterfall }) {
  const data = buildBars(waterfall);

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }} barCategoryGap="20%">
        <CartesianGrid stroke={gridStroke} vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ ...axisTickStyle, fontSize: 11 }}
          axisLine={{ stroke: gridStroke }}
          tickLine={false}
          interval={0}
          angle={-20}
          textAnchor="end"
          height={56}
        />
        <YAxis
          tick={axisTickStyle}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v: number) => formatCurrencyK(v)}
          width={56}
        />
        <Tooltip content={<WaterfallTooltip />} cursor={{ fill: "rgba(31, 42, 68, 0.04)" }} />
        <Bar dataKey="base" stackId="bridge" fill="transparent" isAnimationActive={false} />
        <Bar dataKey="delta" stackId="bridge" radius={[3, 3, 0, 0]} isAnimationActive={false}>
          {data.map((bar) => (
            <Cell key={bar.name} fill={barFill(bar)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
