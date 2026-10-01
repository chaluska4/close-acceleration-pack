"""
Variance engine.

Computes actual-vs-budget and actual-vs-forecast variance for every P&L
line, flags threshold breaches, builds the Operating Income waterfall
bridge, and generates the plain-English top-driver narrative.

This module never touches Excel or openpyxl — it reads SQLite (via
`load_pnl`) or takes a DataFrame directly, and returns clean
pandas DataFrames/dicts. All presentation lives in excel_export.py.
"""

import calendar
import sqlite3
from pathlib import Path
from typing import Union

import pandas as pd

# Lines where a HIGHER actual than plan is favorable (revenue-like).
# Every other line is a cost: a LOWER actual than plan is favorable.
REVENUE_LIKE_LINES = {"Revenue", "Gross Profit", "Operating Income"}
OPEX_LINES = ["Salaries", "Marketing", "Facilities", "Professional Services", "Other"]
BRIDGE_ORDER = ["Revenue", "COGS"] + OPEX_LINES  # order the waterfall walks the P&L
# BRIDGE_ORDER intentionally contains only leaf-level P&L lines. Gross Profit
# and Operating Income are calculated subtotals of these lines — including a
# subtotal as its own waterfall bar would double-count its components'
# impact on Operating Income.

DEFAULT_THRESHOLD_PCT = 0.05      # 5%
DEFAULT_THRESHOLD_ABS = 10_000.0  # $10k
IMMATERIAL_DENOMINATOR = 1_000.0  # below this, a % variance isn't meaningful

VARIANCE_CONVENTION_NOTE = (
    "Variance $ = Actual - Comparison (Budget or Forecast). For Revenue, "
    "Gross Profit, and Operating Income, positive is favorable. For COGS "
    "and opex lines, positive means the actual exceeded plan (unfavorable, "
    "an overspend) — 'Favorable Variance' columns flip that sign so a "
    "positive number always means 'helped Operating Income,' on every "
    "line, in every report in this workbook. Percent variance is shown as "
    "N/M (not meaningful) when the comparison base is zero or under "
    f"${IMMATERIAL_DENOMINATOR:,.0f}, or when a profit metric (Gross Profit, "
    "Operating Income) flips sign against its comparison — a % change is "
    "not a meaningful description of crossing from profit to loss or back."
)


def month_label(month: str) -> str:
    """'2025-12' -> 'December 2025' — the reporting-period label used
    everywhere the workbook shows the period to a reader, so no sheet
    hard-codes a month name."""
    year, m = month.split("-")
    return f"{calendar.month_name[int(m)]} {year}"


def load_pnl(db_path: Union[str, Path]) -> pd.DataFrame:
    """Load actuals/budgets/forecasts from SQLite into one long DataFrame with
    columns [month, line_item, actual, budget, forecast], then append
    Gross Profit and Operating Income subtotal rows computed from the raw
    line items (those subtotals are never stored in SQLite directly)."""
    conn = sqlite3.connect(db_path)
    try:
        actual = pd.read_sql("SELECT month, line_item, amount AS actual FROM actuals", conn)
        budget = pd.read_sql("SELECT month, line_item, amount AS budget FROM budgets", conn)
        forecast = pd.read_sql("SELECT month, line_item, amount AS forecast FROM forecasts", conn)
    finally:
        conn.close()

    pnl = actual.merge(budget, on=["month", "line_item"]).merge(forecast, on=["month", "line_item"])
    return add_subtotals(pnl)


def add_subtotals(pnl_df: pd.DataFrame) -> pd.DataFrame:
    """Append Gross Profit (Revenue - COGS) and Operating Income
    (Gross Profit - sum of opex lines) rows for every month in `pnl_df`."""
    subtotal_rows = []
    for month, group in pnl_df.groupby("month", sort=False):
        by_line = group.set_index("line_item")
        scenarios = ("actual", "budget", "forecast")

        gross_profit = {s: by_line.loc["Revenue", s] - by_line.loc["COGS", s] for s in scenarios}
        opex_total = {s: by_line.loc[OPEX_LINES, s].sum() for s in scenarios}
        operating_income = {s: gross_profit[s] - opex_total[s] for s in scenarios}

        subtotal_rows.append({"month": month, "line_item": "Gross Profit", **gross_profit})
        subtotal_rows.append({"month": month, "line_item": "Operating Income", **operating_income})

    return pd.concat([pnl_df, pd.DataFrame(subtotal_rows)], ignore_index=True)


def compute_variance(
    pnl_df: pd.DataFrame,
    threshold_pct: float = DEFAULT_THRESHOLD_PCT,
    threshold_abs: float = DEFAULT_THRESHOLD_ABS,
) -> pd.DataFrame:
    """Add variance $, variance %, a favorability-signed variance, and a
    threshold-breach flag for both actual-vs-budget and actual-vs-forecast.

    `favorable_variance_vs_*` flips the sign for cost lines so that a
    positive number always means "good for operating income" — this is
    what the waterfall and narrative consume directly.

    A row is flagged if it breaches EITHER the percent threshold or the
    dollar threshold (catches both a big swing on a small base and a
    moderate swing on a large base).

    When the comparison base is zero or below IMMATERIAL_DENOMINATOR, the
    percent variance is set to NaN (rendered as "N/M" downstream) rather
    than a misleadingly huge or undefined percentage — threshold flagging
    for that row then rests on the dollar threshold alone. The same NaN
    treatment applies when a profit metric (Gross Profit, Operating
    Income) flips sign between actual and comparison — e.g. a $5k budgeted
    profit vs. a $2k actual loss is a real, material swing, but "-140%"
    describes it misleadingly; the dollar variance still carries the story.
    """
    df = pnl_df.copy()
    is_profit_metric = df["line_item"].isin(REVENUE_LIKE_LINES)
    sign = is_profit_metric.map({True: 1.0, False: -1.0})

    for compare in ("budget", "forecast"):
        raw_variance = df["actual"] - df[compare]
        sign_flip = is_profit_metric & (df["actual"] * df[compare] < 0)
        usable_denominator = (df[compare].abs() >= IMMATERIAL_DENOMINATOR) & ~sign_flip
        denominator = df[compare].where(usable_denominator)
        df[f"variance_vs_{compare}"] = raw_variance
        df[f"favorable_variance_vs_{compare}"] = raw_variance * sign
        df[f"variance_pct_vs_{compare}"] = raw_variance / denominator
        df[f"flag_vs_{compare}"] = (
            df[f"variance_pct_vs_{compare}"].abs().fillna(0) >= threshold_pct
        ) | (raw_variance.abs() >= threshold_abs)

    return df


def waterfall_components(variance_df: pd.DataFrame, month: str) -> list[tuple[str, float]]:
    """Return the Operating Income bridge for `month` as an ordered list of
    (line_item, contribution) walking Revenue -> COGS -> each opex line.

    Each contribution is that line's `favorable_variance_vs_budget` — i.e.
    already signed so positive always helps Operating Income. By
    construction, sum(contributions) == Actual OI - Budget OI exactly,
    since Operating Income = Revenue - COGS - sum(opex).
    """
    month_df = variance_df[variance_df["month"] == month].set_index("line_item")
    return [(line, float(month_df.loc[line, "favorable_variance_vs_budget"])) for line in BRIDGE_ORDER]


def waterfall_reconciliation(variance_df: pd.DataFrame, month: str) -> dict:
    """Explicit reconciliation of the waterfall to the Operating Income
    variance for `month`: sum of the leaf-level driver contributions,
    the actual OI-variance, and the difference (must round to $0.00).
    Exists so the reconciliation can be *displayed*, not just unit-tested."""
    components = waterfall_components(variance_df, month)
    month_df = variance_df[variance_df["month"] == month].set_index("line_item")
    budget_oi = float(month_df.loc["Operating Income", "budget"])
    actual_oi = float(month_df.loc["Operating Income", "actual"])
    oi_variance = actual_oi - budget_oi
    sum_components = sum(c for _, c in components)
    return {
        "sum_components": round(sum_components, 2),
        "oi_variance": round(oi_variance, 2),
        "difference": round(sum_components - oi_variance, 2),
    }


def top_drivers(
    variance_df: pd.DataFrame, month: str, n: int = 3
) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
    """Return (top-n favorable, top-n unfavorable) waterfall components for
    `month`, ranked by magnitude of their contribution to Operating Income.
    Unfiltered by materiality — see `material_top_drivers` for the version
    executive-facing commentary should use."""
    components = waterfall_components(variance_df, month)
    favorable = sorted((c for c in components if c[1] > 0), key=lambda c: c[1], reverse=True)[:n]
    unfavorable = sorted((c for c in components if c[1] < 0), key=lambda c: c[1])[:n]
    return favorable, unfavorable


def material_top_drivers(
    variance_df: pd.DataFrame, month: str, n: int = 3
) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
    """Like `top_drivers`, but restricted to components that clear the
    same materiality threshold used for flagging (>=5% or >=$10k vs
    budget). Executive commentary should never let an immaterial variance
    (a few hundred dollars, a rounding-sized % swing) crowd out or dilute
    the real drivers — if fewer than `n` lines are material, fewer are
    returned rather than padding with noise."""
    month_df = variance_df[variance_df["month"] == month].set_index("line_item")
    components = waterfall_components(variance_df, month)
    material = [(line, c) for line, c in components if bool(month_df.loc[line, "flag_vs_budget"])]
    favorable = sorted((c for c in material if c[1] > 0), key=lambda c: c[1], reverse=True)[:n]
    unfavorable = sorted((c for c in material if c[1] < 0), key=lambda c: c[1])[:n]
    return favorable, unfavorable


def format_k(amount: float) -> str:
    """$83,268 -> '$83K'; -$58,521 -> '-$59K' — the $000s convention for
    executive-facing text, with the minus sign conventionally placed
    before the dollar sign (not '$-59K'). A driver can be material by
    PERCENT on a small dollar base (e.g. a $476 swing on a thin line
    item) — rounding that to '$0K' would read as a contradiction, so
    amounts under $1,000 fall back to whole dollars."""
    sign = "-" if amount < 0 else ""
    magnitude = abs(amount)
    if magnitude < 1_000:
        return f"{sign}${magnitude:,.0f}"
    return f"{sign}${magnitude / 1000:,.0f}K"


def _driver_clause(line_item: str, contribution: float) -> str:
    """'$83K lower revenue' / '$28K lower COGS' / '$4K higher Marketing
    spend' — quantified, direction-correct, plain English, $K scale."""
    amount = abs(contribution)
    if line_item in REVENUE_LIKE_LINES:
        direction_word = "higher" if contribution >= 0 else "lower"
        noun = line_item.lower()
    else:
        direction_word = "lower" if contribution >= 0 else "higher"
        noun = line_item if line_item == "COGS" else f"{line_item} spend"
    return f"{format_k(amount)} {direction_word} {noun}"


def _driver_list(drivers: list) -> str:
    clauses = [_driver_clause(line, c) for line, c in drivers]
    if not clauses:
        return ""
    if len(clauses) == 1:
        return clauses[0]
    return f"{', '.join(clauses[:-1])} and {clauses[-1]}"


def _management_summary(
    oi_variance_budget: float, oi_variance_forecast: float, favorable: list, unfavorable: list
) -> str:
    """Two management-style sentences: 'Operating Income was $XK
    (un)favorable to budget but $YK (un)favorable to the latest forecast.
    The budget variance was driven by A and B, partially offset by C.'
    The second sentence explicitly labels the drivers as BUDGET drivers —
    the waterfall and driver bullets only ever decompose the budget
    comparison, never the forecast comparison, so the text must not imply
    otherwise. Only ever references MATERIAL drivers actually computed
    from the data — no business cause is stated that the numbers don't
    support, and no immaterial line is cited just to fill out the sentence."""
    budget_word = "favorable to" if oi_variance_budget >= 0 else "unfavorable to"
    forecast_word = "favorable to" if oi_variance_forecast >= 0 else "unfavorable to"
    primary, offset = (unfavorable, favorable) if oi_variance_budget < 0 else (favorable, unfavorable)

    headline = (
        f"Operating Income was {format_k(abs(oi_variance_budget))} {budget_word} budget "
        f"but {format_k(abs(oi_variance_forecast))} {forecast_word} the latest forecast."
    )
    if not primary:
        return headline

    driver_sentence = f"The budget variance was driven by {_driver_list(primary[:2])}"
    if offset:
        driver_sentence += f", partially offset by {_driver_list(offset[:1])}"
    driver_sentence += "."

    return f"{headline} {driver_sentence}"


def narrative(variance_df: pd.DataFrame, month: str, n: int = 3) -> dict:
    """Auto-generate the executive summary for `month`: a headline figure,
    a single management-style summary sentence stating both the budget AND
    forecast comparisons, and material favorable/unfavorable driver
    sentences (up to n each — fewer if fewer clear the materiality
    threshold). All dollar figures are $K; all wording avoids mechanical
    phrasing like 'added $X to Operating Income.'"""
    month_df = variance_df[variance_df["month"] == month].set_index("line_item")
    favorable, unfavorable = material_top_drivers(variance_df, month, n)

    budget_oi = float(month_df.loc["Operating Income", "budget"])
    forecast_oi = float(month_df.loc["Operating Income", "forecast"])
    actual_oi = float(month_df.loc["Operating Income", "actual"])
    oi_variance = actual_oi - budget_oi
    oi_variance_forecast = actual_oi - forecast_oi
    direction = "ahead of" if oi_variance >= 0 else "behind"

    headline = (
        f"Operating Income for {month_label(month)} was {format_k(actual_oi)}, "
        f"{format_k(abs(oi_variance))} {direction} the {format_k(budget_oi)} budget."
    )
    management_summary = _management_summary(oi_variance, oi_variance_forecast, favorable, unfavorable)

    def _sentence(line_item: str, contribution: float) -> str:
        pct = month_df.loc[line_item, "variance_pct_vs_budget"]
        pct_str = f"{pct:+.1%}" if pd.notna(pct) else "N/M"
        favorable_word = "favorable" if contribution > 0 else "unfavorable"
        return f"{line_item}: {format_k(abs(contribution))} {favorable_word} to budget ({pct_str})."

    return {
        "month": month,
        "headline": headline,
        "management_summary": management_summary,
        "favorable": [_sentence(line, c) for line, c in favorable],
        "unfavorable": [_sentence(line, c) for line, c in unfavorable],
        "budget_oi": budget_oi,
        "forecast_oi": forecast_oi,
        "actual_oi": actual_oi,
        "oi_variance": oi_variance,
        "oi_variance_forecast": oi_variance_forecast,
    }
