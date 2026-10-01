"""
KPI module.

Defines the six executive KPIs shown on the dashboard (plus two supporting
metrics used only as chart series — revenue/cost per unit), computes each
from SQLite-sourced data, and layers on RAG (red/amber/green) status vs a
configurable target and a month-over-month trend indicator.

Deliberately narrow: this dashboard was previously a 14-metric wall that
read as noise rather than a decision-useful executive view. Every KPI kept
here earns its place on one of the 6 cards or one of the 3 dashboard
charts — nothing is computed "because the data exists."

Two metrics that would normally appear on a KPI dashboard are intentionally
absent, both to avoid showing a misleading number:
    - Revenue Growth YoY: this dataset covers one fiscal year. There is no
      genuine second year of monthly actuals to compare against, and a
      metric back-derived from a single assumed growth rate would be
      fabricated data presented as a real trend. Not computed anywhere.
    - "EBITDA": the model has no D&A/interest line items, so true EBITDA
      cannot be derived. What's shown is Operating Margin % (Operating
      Income / Revenue) under its real name — it is never labeled EBITDA.

Like variance.py, this module never touches Excel — it returns
DataFrames/dicts/lists consumed by excel_export.py.
"""

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Union

import pandas as pd

from close_pack import variance


@dataclass(frozen=True)
class KPIInputs:
    """Everything a KPI formula might need, loaded once per run."""

    pnl: pd.DataFrame    # long [month, line_item, actual, budget, forecast]
    units: pd.DataFrame  # [month, units_sold]


def load_kpi_inputs(db_path: Union[str, Path]) -> KPIInputs:
    """Load the P&L (with subtotals) and units tables needed to compute
    every KPI in KPI_REGISTRY."""
    pnl = variance.load_pnl(db_path)
    conn = sqlite3.connect(db_path)
    try:
        units = pd.read_sql("SELECT month, units_sold FROM units", conn)
    finally:
        conn.close()
    return KPIInputs(pnl=pnl, units=units)


def _wide(pnl: pd.DataFrame, scenario: str = "actual") -> pd.DataFrame:
    """Pivot the long P&L to a month-indexed table of one scenario's line items."""
    return pnl.pivot(index="month", columns="line_item", values=scenario)


# --------------------------------------------------------------------------
# KPI formulas — each returns a pd.Series indexed by month.
# --------------------------------------------------------------------------

def gross_margin_pct(inp: KPIInputs) -> pd.Series:
    """Gross Profit / Revenue."""
    w = _wide(inp.pnl)
    return (w["Gross Profit"] / w["Revenue"]).rename("gross_margin_pct")


def operating_margin_pct(inp: KPIInputs) -> pd.Series:
    """Operating Income / Revenue. This is Operating Margin, not EBITDA —
    the model has no D&A/interest lines to add back, so it is never
    labeled EBITDA anywhere in this project."""
    w = _wide(inp.pnl)
    return (w["Operating Income"] / w["Revenue"]).rename("operating_margin_pct")


def budget_attainment_pct(inp: KPIInputs) -> pd.Series:
    """Actual Revenue / Budget Revenue."""
    actual = _wide(inp.pnl, "actual")["Revenue"]
    budget = _wide(inp.pnl, "budget")["Revenue"]
    return (actual / budget).rename("budget_attainment_pct")


def forecast_accuracy_pct(inp: KPIInputs) -> pd.Series:
    """1 - |Actual Revenue - Forecast Revenue| / Actual Revenue, floored at
    0. Valid because the forecast used is always the vintage that was live
    BEFORE that month happened (data/generate_data.py revises the forecast
    quarterly using only elapsed-quarter actuals — never a look-ahead;
    see tests/test_validation.py for a check that this holds)."""
    actual = _wide(inp.pnl, "actual")["Revenue"]
    forecast = _wide(inp.pnl, "forecast")["Revenue"]
    accuracy = 1 - (actual - forecast).abs() / actual
    return accuracy.clip(lower=0).rename("forecast_accuracy_pct")


def revenue_per_unit(inp: KPIInputs) -> pd.Series:
    """Actual Revenue / units sold."""
    w = _wide(inp.pnl)
    units = inp.units.set_index("month")["units_sold"]
    return (w["Revenue"] / units).rename("revenue_per_unit")


def total_cost_per_unit(inp: KPIInputs) -> pd.Series:
    """(COGS + total opex) / units sold."""
    w = _wide(inp.pnl)
    total_cost = w["COGS"] + w[variance.OPEX_LINES].sum(axis=1)
    units = inp.units.set_index("month")["units_sold"]
    return (total_cost / units).rename("total_cost_per_unit")


# --------------------------------------------------------------------------
# Registry: name, formula function, default target, direction, display format.
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class KPISpec:
    key: str
    label: str
    func: Callable[[KPIInputs], pd.Series]
    target: float
    direction: str  # "higher_is_better" | "lower_is_better"
    fmt: str        # "pct" | "currency"


KPI_REGISTRY: list = [
    KPISpec("gross_margin_pct", "Gross Margin %", gross_margin_pct, 0.40, "higher_is_better", "pct"),
    KPISpec("operating_margin_pct", "Operating Margin %", operating_margin_pct, 0.12, "higher_is_better", "pct"),
    KPISpec("budget_attainment_pct", "Revenue Budget Attainment", budget_attainment_pct, 1.00, "higher_is_better", "pct"),
    KPISpec("forecast_accuracy_pct", "Forecast Accuracy %", forecast_accuracy_pct, 0.93, "higher_is_better", "pct"),
    KPISpec("revenue_per_unit", "Revenue per Unit", revenue_per_unit, 42.00, "higher_is_better", "currency"),
    KPISpec("total_cost_per_unit", "Total Cost per Unit", total_cost_per_unit, 34.00, "lower_is_better", "currency"),
]


def rag_status(value: float, target: float, direction: str, tolerance: float = 0.05) -> str:
    """Green/Amber/Red vs `target`. `tolerance` (default 5%) is how far past
    target on the wrong side still counts as Amber before it becomes Red.
    Directional: for a lower-is-better metric (an expense ratio, cost per
    unit), a value BELOW target is Green — a decrease is favorable there,
    not a decline."""
    if pd.isna(value):
        return "N/A"
    if direction == "higher_is_better":
        if value >= target:
            return "Green"
        return "Amber" if value >= target * (1 - tolerance) else "Red"
    else:  # lower_is_better
        if value <= target:
            return "Green"
        return "Amber" if value <= target * (1 + tolerance) else "Red"


def compute_kpi_table(inp: KPIInputs, targets: Optional[dict] = None, tolerance: float = 0.05) -> pd.DataFrame:
    """Long-form table — one row per (kpi, month) — with value, target, and
    RAG status, for every KPI in KPI_REGISTRY across the full history."""
    targets = targets or {}
    rows = []
    for spec in KPI_REGISTRY:
        target = targets.get(spec.key, spec.target)
        series = spec.func(inp)
        for month, value in series.items():
            rows.append({
                "month": month,
                "kpi_key": spec.key,
                "label": spec.label,
                "value": value,
                "fmt": spec.fmt,
                "target": target,
                "direction": spec.direction,
                "rag": rag_status(value, target, spec.direction, tolerance),
            })
    return pd.DataFrame(rows)


def trend(value: float, prior: Optional[float], direction: str) -> dict:
    """Month-over-month change for a KPI card: delta, percent change, and
    whether that change was favorable GIVEN the KPI's direction — e.g. a
    decrease is favorable for a lower-is-better metric like cost per unit."""
    if prior is None or prior == 0 or pd.isna(prior):
        return {"delta": None, "pct_change": None, "favorable": None}
    delta = value - prior
    if delta == 0:
        return {"delta": 0.0, "pct_change": 0.0, "favorable": None}
    pct_change = delta / abs(prior)
    favorable = (delta > 0) if direction == "higher_is_better" else (delta < 0)
    return {"delta": delta, "pct_change": pct_change, "favorable": favorable}


# --------------------------------------------------------------------------
# Executive dashboard: the 6 cards
# --------------------------------------------------------------------------

def _dollar_card(label: str, key: str, actual_series: pd.Series, budget_series: pd.Series,
                  month: str, prior_month: Optional[str]) -> dict:
    value = float(actual_series.loc[month])
    target = float(budget_series.loc[month])
    prior = float(actual_series.loc[prior_month]) if prior_month is not None else None
    return {
        "key": key, "label": label, "value": value, "target": target,
        "direction": "higher_is_better", "fmt": "currency",
        "rag": rag_status(value, target, "higher_is_better"),
        "prior": prior,
        # "budget": this card's target IS that month's actual budget line —
        # distinct from a "kpi_target" card, whose target is a configured
        # threshold, not a budget figure. Lets the dashboard say "vs.
        # Budget" only where that's literally true.
        "target_kind": "budget",
    }


def _registry_card(key: str, inp: KPIInputs, month: str, prior_month: Optional[str],
                    target_override: Optional[float] = None) -> dict:
    spec = next(s for s in KPI_REGISTRY if s.key == key)
    series = spec.func(inp)
    value = float(series.loc[month])
    target = spec.target if target_override is None else target_override
    prior = float(series.loc[prior_month]) if prior_month is not None and prior_month in series.index else None
    return {
        "key": key, "label": spec.label, "value": value, "target": target,
        "direction": spec.direction, "fmt": spec.fmt,
        "rag": rag_status(value, target, spec.direction),
        "prior": prior,
        "target_kind": "kpi_target",
    }


def compute_executive_kpis(inp: KPIInputs, month: str, targets: Optional[dict] = None) -> list:
    """The 6 executive-dashboard KPI cards for `month`: Revenue, Budget
    Attainment %, Gross Margin %, Operating Income, Operating Margin %,
    Forecast Accuracy %. Revenue and Operating Income are raw P&L dollar
    levels compared against that same month's budget; the rest come from
    KPI_REGISTRY. Each card carries the prior month's value for the
    dashboard's trend indicator (see `trend()`)."""
    targets = targets or {}
    w_actual = _wide(inp.pnl, "actual")
    w_budget = _wide(inp.pnl, "budget")
    months = list(w_actual.index)
    idx = months.index(month)
    prior_month = months[idx - 1] if idx > 0 else None

    return [
        _dollar_card("Revenue", "revenue", w_actual["Revenue"], w_budget["Revenue"], month, prior_month),
        _registry_card("budget_attainment_pct", inp, month, prior_month,
                        targets.get("budget_attainment_pct")),
        _registry_card("gross_margin_pct", inp, month, prior_month, targets.get("gross_margin_pct")),
        _dollar_card("Operating Income", "operating_income", w_actual["Operating Income"],
                     w_budget["Operating Income"], month, prior_month),
        _registry_card("operating_margin_pct", inp, month, prior_month, targets.get("operating_margin_pct")),
        _registry_card("forecast_accuracy_pct", inp, month, prior_month, targets.get("forecast_accuracy_pct")),
    ]


_RAG_SEVERITY = {"Red": 2, "Amber": 1, "Green": 0, "N/A": -1}


def _format_value(value: float, fmt: str) -> str:
    """Matches the dashboard cards' units exactly: currency in $K (same
    convention/rounding as variance.format_k(), reused here rather than
    duplicated) so the Risk & Action prose never shows '$775,350' right
    under a card that reads '$775K' for the same figure."""
    if fmt == "currency":
        return variance.format_k(value)
    if fmt == "pct":
        return f"{value:.1%}"
    return f"{value:,.2f}"


# Specific, analyst-style next steps per KPI — a recommended INVESTIGATIVE
# action (what to go look at next), not a fabricated business cause. The
# model has no product/channel/volume-level detail to assert a cause from,
# but recommending the standard next breakdown an FP&A analyst would run
# is legitimate even without that detail in hand.
_RISK_ACTIONS = {
    "revenue": "Review the shortfall by volume, product line, and channel to isolate the driver, "
               "and assess the impact on the current-quarter forecast.",
    "budget_attainment_pct": "Review the revenue shortfall by volume, product line, and channel to isolate "
               "the driver, and assess the impact on the current-quarter forecast.",
    "operating_income": "Trace the shortfall to its underlying revenue and cost drivers, and flag the "
               "impact for management reporting before the close is finalized.",
    "gross_margin_pct": "Review COGS by product line and supplier to confirm whether the pressure is "
               "transitory or structural, and flag any standard-cost revisions for next quarter's forecast.",
    "operating_margin_pct": "Review COGS and opex drivers behind the margin miss by line item, and confirm "
               "whether the current forecast's margin assumptions still hold.",
    "forecast_accuracy_pct": "Review the forecast model's input assumptions against the latest actual "
               "run-rate and recalibrate ahead of the next quarterly revision.",
    "revenue_per_unit": "Review realized pricing and discounting by channel against plan.",
    "total_cost_per_unit": "Review per-unit cost build-up by component to isolate whether the increase "
               "is COGS- or opex-driven.",
}
_DEFAULT_RISK_ACTION = "Review the driver behind this variance and assess the impact on the current forecast."


def management_insights(var_df: pd.DataFrame, exec_cards: list, month: str) -> dict:
    """Top favorable driver, top unfavorable driver (straight from the
    variance waterfall), and one risk/action line for whichever of the 6
    executive KPIs is furthest from target this month — phrased as a real
    FP&A analyst would: the specific gap, then a concrete next step, never
    a generic "monitor closely." Every clause is traceable to a computed
    number; the recommended action is a next investigative step, not a
    fabricated cause."""
    driver_narrative = variance.narrative(var_df, month, n=1)
    top_favorable = driver_narrative["favorable"][0] if driver_narrative["favorable"] else \
        "No favorable drivers this period."
    top_unfavorable = driver_narrative["unfavorable"][0] if driver_narrative["unfavorable"] else \
        "No unfavorable drivers this period."

    worst = max(exec_cards, key=lambda c: _RAG_SEVERITY.get(c["rag"], -1))
    if _RAG_SEVERITY.get(worst["rag"], -1) <= 0:
        risk_action = "All six executive KPIs are at or above target this period; continue monitoring against plan."
    else:
        target_phrase = "Budget" if worst.get("target_kind") == "budget" else "KPI Target"
        status_word = "unfavorable" if worst["rag"] == "Red" else "a watch item"
        action = _RISK_ACTIONS.get(worst["key"], _DEFAULT_RISK_ACTION)
        risk_action = (
            f"{worst['label']} is {status_word} at {_format_value(worst['value'], worst['fmt'])} "
            f"vs. {target_phrase} {_format_value(worst['target'], worst['fmt'])}. {action}"
        )

    return {"top_favorable": top_favorable, "top_unfavorable": top_unfavorable, "risk_action": risk_action}
