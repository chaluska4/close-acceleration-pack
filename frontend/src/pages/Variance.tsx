import { useState } from "react";
import { Card, CardHeader } from "../components/ui/Card";
import { ComparisonToggle } from "../components/variance/ComparisonToggle";
import { DriversList } from "../components/variance/DriversList";
import { PnlVarianceTable } from "../components/variance/PnlVarianceTable";
import { ReconciliationFooter } from "../components/variance/ReconciliationFooter";
import { WaterfallChart } from "../components/variance/WaterfallChart";
import { getVariance } from "../lib/adapter";
import { formatCurrency } from "../lib/format";
import type { Comparison } from "../lib/types";

export function Variance() {
  const variance = getVariance();
  const [comparison, setComparison] = useState<Comparison>("budget");
  const active = variance.comparisons[comparison];

  return (
    <div className="flex flex-col gap-6">
      <Card as="section" aria-labelledby="variance-summary-heading">
        <CardHeader
          title={<span id="variance-summary-heading">Management Summary</span>}
          subtitle={variance.month_label}
        />
        <div className="space-y-2 p-5 text-sm leading-relaxed text-[var(--color-ink)]">
          <p className="font-medium text-[var(--color-navy)]">{variance.narrative.headline}</p>
          <p className="text-[var(--color-ink-secondary)]">{variance.narrative.management_summary}</p>
        </div>
      </Card>

      <Card as="section" aria-labelledby="pnl-variance-heading">
        <CardHeader
          title={<span id="pnl-variance-heading">P&amp;L Variance</span>}
          subtitle={`Actual vs. ${active.label}, ${variance.month_label}`}
          action={<ComparisonToggle value={comparison} onChange={setComparison} />}
        />
        <div className="p-5">
          <PnlVarianceTable comparison={active} />
          <p className="mt-3 text-xs text-[var(--color-ink-muted)]">
            <strong className="font-semibold text-[var(--color-ink-secondary)]">Materiality threshold:</strong>{" "}
            a line is flagged "Material" when it breaches either{" "}
            <strong className="text-[var(--color-ink-secondary)]">
              ±{(variance.threshold_pct * 100).toFixed(0)}%
            </strong>{" "}
            or <strong className="text-[var(--color-ink-secondary)]">±{formatCurrency(variance.threshold_abs)}</strong>{" "}
            — catching both a large swing on a small base and a moderate swing on a large one. "N/M" (not
            meaningful) replaces a percent that would otherwise mislead, e.g. a profit line flipping sign.
          </p>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card as="section" aria-labelledby="favorable-drivers-heading">
          <CardHeader
            title={<span id="favorable-drivers-heading">Top Favorable Driver{active.top_favorable.length === 1 ? "" : "s"}</span>}
            subtitle={`vs. ${active.label}`}
          />
          <div className="p-5">
            <DriversList title="Favorable" drivers={active.top_favorable} tone="favorable" />
          </div>
        </Card>
        <Card as="section" aria-labelledby="unfavorable-drivers-heading">
          <CardHeader
            title={<span id="unfavorable-drivers-heading">Top Unfavorable Driver{active.top_unfavorable.length === 1 ? "" : "s"}</span>}
            subtitle={`vs. ${active.label}`}
          />
          <div className="p-5">
            <DriversList title="Unfavorable" drivers={active.top_unfavorable} tone="unfavorable" />
          </div>
        </Card>
      </div>

      <Card as="section" aria-labelledby="waterfall-heading">
        <CardHeader
          title={<span id="waterfall-heading">Operating Income Bridge</span>}
          subtitle="Budget OI → leaf-level P&L drivers → Actual OI (always vs. Budget — the bridge decomposes the budget comparison)"
        />
        <div className="p-5">
          <WaterfallChart waterfall={variance.waterfall} />
          <div className="mt-4">
            <ReconciliationFooter reconciliation={variance.waterfall.reconciliation} />
          </div>
        </div>
      </Card>
    </div>
  );
}
