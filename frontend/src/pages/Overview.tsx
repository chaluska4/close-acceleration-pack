import { Card, CardHeader } from "../components/ui/Card";
import { KpiCard } from "../components/overview/KpiCard";
import { ManagementInsights } from "../components/overview/ManagementInsights";
import { MarginTrendChart } from "../components/overview/MarginTrendChart";
import { RevenueTrendChart } from "../components/overview/RevenueTrendChart";
import { UnitEconomicsChart } from "../components/overview/UnitEconomicsChart";
import { getKpis, getManagementInsights, getMeta } from "../lib/adapter";

export function Overview() {
  const { cards, series } = getKpis();
  const insights = getManagementInsights();
  const meta = getMeta();

  return (
    <div className="flex flex-col gap-6">
      <section aria-labelledby="exec-kpis-heading">
        <div className="mb-3 flex items-baseline justify-between">
          <h2 id="exec-kpis-heading" className="text-lg font-semibold text-[var(--color-navy)]">
            Executive KPIs
          </h2>
          <p className="text-xs text-[var(--color-ink-muted)]">{meta.current_period_label}</p>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {cards.map((card) => (
            <KpiCard key={card.key} card={card} />
          ))}
        </div>
      </section>

      <Card as="section" aria-labelledby="management-insights-heading">
        <CardHeader
          title={<span id="management-insights-heading">Management Insights</span>}
          subtitle="Computed from this period's variance results — not hand-written."
        />
        <div className="p-5">
          <ManagementInsights insights={insights} />
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card as="section" aria-labelledby="revenue-trend-heading">
          <CardHeader
            title={<span id="revenue-trend-heading">Revenue: Actual vs. Budget vs. Forecast</span>}
            subtitle="Trailing 12 months"
          />
          <div className="p-4">
            <RevenueTrendChart series={series} />
          </div>
        </Card>

        <Card as="section" aria-labelledby="margin-trend-heading">
          <CardHeader
            title={<span id="margin-trend-heading">Gross Margin % and Operating Margin % Trend</span>}
            subtitle="Trailing 12 months"
          />
          <div className="p-4">
            <MarginTrendChart series={series} />
          </div>
        </Card>

        <Card as="section" aria-labelledby="unit-economics-heading" className="lg:col-span-2">
          <CardHeader
            title={<span id="unit-economics-heading">Revenue per Unit and Cost per Unit</span>}
            subtitle="Trailing 12 months, whole-dollar scale"
          />
          <div className="p-4">
            <UnitEconomicsChart series={series} />
          </div>
        </Card>
      </div>
    </div>
  );
}
