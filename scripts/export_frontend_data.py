"""
Exports the real, computed project data to JSON for the frontend
(frontend/src/data/*.json), and copies the real deliverables/screenshots
into frontend/public/ so the frontend is a self-contained, deployable app.

This script contains NO financial logic of its own beyond simple
presentation-layer re-shaping (picking fields, formatting for JSON, and —
for the Actual-vs-Forecast variance view — mirroring the exact same
sort/filter algorithm variance.material_top_drivers() already uses for
Actual-vs-Budget, parameterized for the forecast columns that
variance.compute_variance() already computes). It never recomputes a
number; everything traces back to close_pack.variance/kpi/controls.

Run after `make all` has seeded the database (or run `make all` first via
the `export` Makefile target, which sequences both):

    python scripts/export_frontend_data.py
"""

import json
import math
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from close_pack import controls, kpi, variance  # noqa: E402

DB_PATH = REPO_ROOT / "data" / "close_pack.db"
DELIVERABLES_DIR = REPO_ROOT / "deliverables"
DOCS_IMAGES_DIR = REPO_ROOT / "docs" / "images"

FRONTEND_DATA_DIR = REPO_ROOT / "frontend" / "src" / "data"
FRONTEND_PUBLIC_DELIVERABLES = REPO_ROOT / "frontend" / "public" / "deliverables"
FRONTEND_PUBLIC_IMAGES = REPO_ROOT / "frontend" / "public" / "images"

PNL_DISPLAY_ORDER = [
    "Revenue", "COGS", "Gross Profit",
    "Salaries", "Marketing", "Facilities", "Professional Services", "Other",
    "Operating Income",
]
SUBTOTAL_LINES = {"Gross Profit", "Operating Income"}


def _num(x):
    """None for NaN (JSON has no NaN) — the frontend renders this as 'N/M',
    same convention as the Excel workbooks."""
    if x is None:
        return None
    if isinstance(x, float) and math.isnan(x):
        return None
    return float(x)


def _material_top_drivers(var_df: pd.DataFrame, month: str, compare: str, n: int = 3):
    """Same algorithm as variance.material_top_drivers() (sorted by
    magnitude, filtered to rows that clear that comparison's materiality
    flag) — duplicated here only because the engine's version is hardcoded
    to the budget columns; this reads the forecast columns
    compute_variance() already produces, via variance.waterfall_components-
    style indexing, without changing variance.py."""
    month_df = var_df[var_df["month"] == month].set_index("line_item")
    components = [
        (line, float(month_df.loc[line, f"favorable_variance_vs_{compare}"]))
        for line in variance.BRIDGE_ORDER
    ]
    material = [(line, c) for line, c in components if bool(month_df.loc[line, f"flag_vs_{compare}"])]
    favorable = sorted((c for c in material if c[1] > 0), key=lambda c: c[1], reverse=True)[:n]
    unfavorable = sorted((c for c in material if c[1] < 0), key=lambda c: c[1])[:n]
    return favorable, unfavorable


def _driver_entries(drivers):
    return [
        {"line_item": line, "contribution": _num(c), "contribution_label": variance.format_k(c)}
        for line, c in drivers
    ]


def _pnl_rows(var_df: pd.DataFrame, month: str, compare: str):
    month_df = var_df[var_df["month"] == month].set_index("line_item")
    rows = []
    for line in PNL_DISPLAY_ORDER:
        r = month_df.loc[line]
        rows.append({
            "line_item": line,
            "is_subtotal": line in SUBTOTAL_LINES,
            "actual": _num(r["actual"]),
            "comparison": _num(r[compare]),
            "variance": _num(r[f"variance_vs_{compare}"]),
            "variance_pct": _num(r[f"variance_pct_vs_{compare}"]),
            "favorable": bool(r[f"favorable_variance_vs_{compare}"] >= 0) if pd.notna(r[f"favorable_variance_vs_{compare}"]) else None,
            "material": bool(r[f"flag_vs_{compare}"]),
        })
    return rows


def build_meta(current_period: str) -> dict:
    return {
        "product_name": "Close Acceleration Pack",
        "company_name": "Beacon Outdoor Goods",
        "company_name_full": "Beacon Outdoor Goods (fictional — synthetic data)",
        "current_period": current_period,
        "current_period_label": variance.month_label(current_period),
        "data_disclosure": "All company names, financial figures, and operational data in this "
                            "application are synthetic and fictional, generated for portfolio "
                            "demonstration purposes. This is not real company reporting.",
        "github_url": "https://github.com/chaluska4/close-acceleration-pack",
        # When this export was run — i.e. when the pipeline last produced
        # the numbers the frontend/workbooks currently show. Not a claim
        # about when the underlying synthetic data was authored.
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def build_kpis(kpi_inputs, current_period: str) -> dict:
    cards = kpi.compute_executive_kpis(kpi_inputs, current_period)
    card_payload = []
    for card in cards:
        t = kpi.trend(card["value"], card["prior"], card["direction"])
        card_payload.append({
            "key": card["key"],
            "label": card["label"],
            "value": _num(card["value"]),
            "target": _num(card["target"]),
            "target_kind": card["target_kind"],
            "direction": card["direction"],
            "fmt": card["fmt"],
            "rag": card["rag"],
            "prior": _num(card["prior"]),
            "trend": {
                "delta": _num(t["delta"]),
                "pct_change": _num(t["pct_change"]),
                "favorable": t["favorable"],
            },
        })

    # 12-month series backing the 3 dashboard charts — same source data,
    # just pivoted wide so the frontend can hand it straight to a chart lib.
    pnl = kpi_inputs.pnl
    months = sorted(pnl["month"].unique())
    w_actual = pnl.pivot(index="month", columns="line_item", values="actual")
    w_budget = pnl.pivot(index="month", columns="line_item", values="budget")
    w_forecast = pnl.pivot(index="month", columns="line_item", values="forecast")
    gross_margin = kpi.gross_margin_pct(kpi_inputs)
    operating_margin = kpi.operating_margin_pct(kpi_inputs)
    revenue_per_unit = kpi.revenue_per_unit(kpi_inputs)
    total_cost_per_unit = kpi.total_cost_per_unit(kpi_inputs)

    series = []
    for m in months:
        series.append({
            "month": m,
            "month_label": variance.month_label(m),
            "revenue_actual": _num(w_actual.loc[m, "Revenue"]),
            "revenue_budget": _num(w_budget.loc[m, "Revenue"]),
            "revenue_forecast": _num(w_forecast.loc[m, "Revenue"]),
            "gross_margin_pct": _num(gross_margin.loc[m]),
            "operating_margin_pct": _num(operating_margin.loc[m]),
            "revenue_per_unit": _num(revenue_per_unit.loc[m]),
            "total_cost_per_unit": _num(total_cost_per_unit.loc[m]),
        })

    return {"cards": card_payload, "series": series}


def build_management_insights(var_df, cards_raw, current_period: str) -> dict:
    return kpi.management_insights(var_df, cards_raw, current_period)


def build_variance(var_df: pd.DataFrame, current_period: str) -> dict:
    narrative = variance.narrative(var_df, current_period, n=3)
    recon = variance.waterfall_reconciliation(var_df, current_period)
    waterfall_components = variance.waterfall_components(var_df, current_period)

    comparisons = {}
    for compare, label in (("budget", "Budget"), ("forecast", "Forecast")):
        favorable, unfavorable = _material_top_drivers(var_df, current_period, compare, n=3)
        comparisons[compare] = {
            "label": label,
            "rows": _pnl_rows(var_df, current_period, compare),
            "top_favorable": _driver_entries(favorable),
            "top_unfavorable": _driver_entries(unfavorable),
        }

    return {
        "month": current_period,
        "month_label": variance.month_label(current_period),
        "threshold_pct": variance.DEFAULT_THRESHOLD_PCT,
        "threshold_abs": variance.DEFAULT_THRESHOLD_ABS,
        "convention_note": variance.VARIANCE_CONVENTION_NOTE,
        "narrative": {
            "headline": narrative["headline"],
            "management_summary": narrative["management_summary"],
        },
        "waterfall": {
            # Always vs. Budget — the bridge decomposes the budget
            # comparison only, same as the Excel Waterfall sheet; shown
            # regardless of which comparison is toggled in the table.
            "components": [
                {"line_item": line, "contribution": _num(c), "contribution_label": variance.format_k(c)}
                for line, c in waterfall_components
            ],
            "reconciliation": {
                "sum_components": _num(recon["sum_components"]),
                "oi_variance": _num(recon["oi_variance"]),
                "difference": _num(recon["difference"]),
            },
            "budget_oi": _num(narrative["budget_oi"]),
            "actual_oi": _num(narrative["actual_oi"]),
        },
        "comparisons": comparisons,
    }


def build_close(current_period: str) -> dict:
    calendar_df = controls.close_calendar()
    cal_summary = controls.close_calendar_summary()
    controls_df = controls.evaluate_controls(str(DB_PATH))
    ctrl_summary = controls.controls_summary(controls_df)

    calendar = calendar_df.to_dict(orient="records")
    controls_log = controls_df.to_dict(orient="records")

    return {
        "period_label": variance.month_label(current_period),
        "summary": cal_summary,
        "calendar": calendar,
        "controls_summary": ctrl_summary,
        "controls": controls_log,
    }


def write_json(name: str, payload: dict) -> None:
    FRONTEND_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = FRONTEND_DATA_DIR / name
    out.write_text(json.dumps(payload, indent=2, allow_nan=False))
    print(f"  frontend/src/data/{name}")


def copy_static_assets() -> None:
    FRONTEND_PUBLIC_DELIVERABLES.mkdir(parents=True, exist_ok=True)
    FRONTEND_PUBLIC_IMAGES.mkdir(parents=True, exist_ok=True)
    for f in DELIVERABLES_DIR.glob("*.xlsx"):
        shutil.copy2(f, FRONTEND_PUBLIC_DELIVERABLES / f.name)
        print(f"  frontend/public/deliverables/{f.name}")
    for name in ("kpi-dashboard.png", "variance-summary.png", "close-calendar.png"):
        src = DOCS_IMAGES_DIR / name
        if src.exists():
            shutil.copy2(src, FRONTEND_PUBLIC_IMAGES / name)
            print(f"  frontend/public/images/{name}")


def main():
    if not DB_PATH.exists():
        print(f"{DB_PATH} not found. Run `make all` first.", file=sys.stderr)
        sys.exit(1)
    if not DELIVERABLES_DIR.exists() or not any(DELIVERABLES_DIR.glob("*.xlsx")):
        print(f"{DELIVERABLES_DIR} has no .xlsx files. Run `make deliverables` first.", file=sys.stderr)
        sys.exit(1)

    var_df = variance.compute_variance(variance.load_pnl(DB_PATH))
    kpi_inputs = kpi.load_kpi_inputs(DB_PATH)
    current_period = max(var_df["month"])
    cards_raw = kpi.compute_executive_kpis(kpi_inputs, current_period)

    print("Writing frontend data:")
    write_json("meta.json", build_meta(current_period))
    write_json("kpis.json", build_kpis(kpi_inputs, current_period))
    write_json("management-insights.json", build_management_insights(var_df, cards_raw, current_period))
    write_json("variance.json", build_variance(var_df, current_period))
    write_json("close.json", build_close(current_period))

    print("Copying static assets:")
    copy_static_assets()


if __name__ == "__main__":
    main()
