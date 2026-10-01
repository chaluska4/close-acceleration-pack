"""
Generates the README screenshots in docs/ from the live pipeline output.

Reuses the same matplotlib render functions that build the embedded
workbook charts (excel_export.py), plus two summary charts (executive KPI
status mix, controls effective/exception by category) that exist only as
documentation, not as workbook content. Run after `make all` has seeded
the database:

    python docs/generate_screenshots.py
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from close_pack import controls, excel_export, kpi, variance

DB_PATH = REPO_ROOT / "data" / "close_pack.db"
DOCS_DIR = Path(__file__).parent
CURRENT_PERIOD = "2025-12"


def save(png_bytes, name):
    (DOCS_DIR / name).write_bytes(png_bytes.getvalue())
    print(f"  docs/{name}")


def render_kpi_rag_summary(cards):
    """Horizontal status bars: how many of the 6 executive KPI cards are
    Green/Amber/Red this month — the dashboard's headline-at-a-glance."""
    excel_export._mpl_style()
    order = ["Green", "Amber", "Red"]
    counts = {r: 0 for r in order}
    for card in cards:
        if card["rag"] in counts:
            counts[card["rag"]] += 1
    values = [counts[r] for r in order]
    colors = [excel_export._mpl(excel_export.RAG_COLOR[r]) for r in order]

    fig, ax = plt.subplots(figsize=(6, 3.0))
    bars = ax.barh(order, values, color=colors, height=0.55)
    for bar, v in zip(bars, values):
        ax.text(bar.get_width() + 0.15, bar.get_y() + bar.get_height() / 2, str(v),
                va="center", fontsize=10, color=excel_export._mpl(excel_export.INK_PRIMARY))
    ax.set_xlim(0, max(values) + 2)
    ax.invert_yaxis()
    ax.set_title(f"Executive KPI Status Mix — {CURRENT_PERIOD} (of 6 KPIs)", fontsize=12, fontweight="bold",
                 color=excel_export._mpl(excel_export.NAVY), loc="left")
    ax.spines["left"].set_visible(False)
    ax.tick_params(left=False)
    fig.tight_layout()
    return excel_export._fig_to_png(fig)


def render_controls_summary(controls_df):
    """Stacked Effective/Exception counts per category — proves the
    controls framework actually evaluates, rather than rubber-stamping
    everything."""
    excel_export._mpl_style()
    grouped = controls_df.groupby(["category", "status"]).size().unstack(fill_value=0)
    categories = ["Completeness", "Accuracy", "Authorization"]
    effective = [grouped.loc[c, "Effective"] if c in grouped.index and "Effective" in grouped.columns else 0
                 for c in categories]
    exception = [grouped.loc[c, "Exception"] if c in grouped.index and "Exception" in grouped.columns else 0
                 for c in categories]

    fig, ax = plt.subplots(figsize=(6, 3.2))
    x = range(len(categories))
    ax.bar(x, effective, color=excel_export._mpl(excel_export.STATUS_GOOD), label="Effective", width=0.5)
    ax.bar(x, exception, bottom=effective, color=excel_export._mpl(excel_export.STATUS_CRITICAL),
           label="Exception", width=0.5)
    ax.set_xticks(list(x))
    ax.set_xticklabels(categories, fontsize=9)
    ax.set_ylabel("Controls")
    ax.set_title("Controls Log — Effective / Exception by Category", fontsize=12, fontweight="bold",
                 color=excel_export._mpl(excel_export.NAVY), loc="left")
    ax.legend(frameon=False, loc="upper right", fontsize=8)
    fig.tight_layout()
    return excel_export._fig_to_png(fig)


def main():
    if not DB_PATH.exists():
        print(f"{DB_PATH} not found — run `python data/generate_data.py` first.", file=sys.stderr)
        sys.exit(1)

    var_df = variance.compute_variance(variance.load_pnl(DB_PATH))
    kpi_inputs = kpi.load_kpi_inputs(DB_PATH)
    cards = kpi.compute_executive_kpis(kpi_inputs, CURRENT_PERIOD)
    controls_df = controls.evaluate_controls(str(DB_PATH))

    print("Writing screenshots:")

    components = variance.waterfall_components(var_df, CURRENT_PERIOD)
    month_df = var_df[var_df["month"] == CURRENT_PERIOD].set_index("line_item")
    waterfall_png = excel_export.render_waterfall_png(
        components, float(month_df.loc["Operating Income", "budget"]),
        float(month_df.loc["Operating Income", "actual"]), variance.month_label(CURRENT_PERIOD),
    )
    save(waterfall_png, "waterfall.png")

    pnl = kpi_inputs.pnl
    w_actual = pnl.pivot(index="month", columns="line_item", values="actual")
    w_budget = pnl.pivot(index="month", columns="line_item", values="budget")
    w_forecast = pnl.pivot(index="month", columns="line_item", values="forecast")
    months = list(w_actual.index)

    trend_png = excel_export.render_revenue_trend_png(
        months, w_actual["Revenue"].tolist(), w_budget["Revenue"].tolist(), w_forecast["Revenue"].tolist(),
    )
    save(trend_png, "revenue_trend.png")

    margin_png = excel_export.render_margin_trend_png(
        months, kpi.gross_margin_pct(kpi_inputs).tolist(), kpi.operating_margin_pct(kpi_inputs).tolist(),
    )
    save(margin_png, "margin_trend.png")

    save(render_kpi_rag_summary(cards), "kpi_rag_summary.png")
    save(render_controls_summary(controls_df), "controls_summary.png")


if __name__ == "__main__":
    main()
