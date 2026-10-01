import { Card, CardHeader } from "../components/ui/Card";
import { DeliverableCard } from "../components/outputs/DeliverableCard";
import { HowItWorks } from "../components/outputs/HowItWorks";
import { getMeta } from "../lib/adapter";

const DELIVERABLES = [
  {
    title: "KPI Dashboard",
    description: "Six executive KPI cards, three trend charts, and management insights for the reporting period.",
    imageSrc: "images/kpi-dashboard.png",
    imageAlt: "KPI Dashboard workbook — executive KPI cards and management insights",
    downloadHref: "deliverables/kpi_dashboard.xlsx",
  },
  {
    title: "Variance Analysis",
    description: "Actual vs. Budget vs. Forecast P&L variance, favorable/unfavorable drivers, and the OI waterfall bridge.",
    imageSrc: "images/variance-summary.png",
    imageAlt: "Variance Analysis workbook — favorable and unfavorable drivers",
    downloadHref: "deliverables/variance_analysis.xlsx",
  },
  {
    title: "Close Checklist",
    description: "Day 1–5 close calendar with dependency-cascade status, plus the full 12-control testing log.",
    imageSrc: "images/close-calendar.png",
    imageAlt: "Close Calendar workbook — Day 1-5 tasks with dependency-cascade status",
    downloadHref: "deliverables/close_checklist.xlsx",
  },
];

export function Outputs() {
  const meta = getMeta();

  return (
    <div className="flex flex-col gap-6">
      <Card as="section" aria-labelledby="outputs-heading">
        <CardHeader
          title={<span id="outputs-heading">Excel Deliverables</span>}
          subtitle="The real, generated workbooks behind this app — same data, same numbers, formatted for circulation."
        />
        <div className="grid grid-cols-1 gap-5 p-5 sm:grid-cols-2 lg:grid-cols-3">
          {DELIVERABLES.map((deliverable) => (
            <DeliverableCard key={deliverable.title} {...deliverable} />
          ))}
        </div>
      </Card>

      <Card as="section" aria-labelledby="how-it-works-heading">
        <CardHeader
          title={<span id="how-it-works-heading">How It Works</span>}
          subtitle="One automated pipeline produces everything you see here — the dashboard and the Excel workbooks."
          action={
            <a
              href={meta.github_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex shrink-0 items-center justify-center rounded-md border border-[var(--color-border)] px-3.5 py-2 text-xs font-medium text-[var(--color-ink-secondary)] transition-colors hover:border-[var(--color-navy)] hover:text-[var(--color-navy)]"
            >
              View technical implementation on GitHub
              <span aria-hidden="true"> ↗</span>
              <span className="sr-only"> (opens in a new tab)</span>
            </a>
          }
        />
        <HowItWorks generatedAt={meta.generated_at} />
      </Card>
    </div>
  );
}
