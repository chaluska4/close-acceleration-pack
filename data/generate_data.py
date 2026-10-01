"""
Synthetic data generator for the Close Acceleration Pack.

Seeds close_pack.db (SQLite) with 12 months of realistic financial data for
"Beacon Outdoor Goods" — a fictional consumer goods company. All figures are
synthetic and generated deterministically (seeded RNG) so every downstream
module, test, and screenshot is reproducible.

--------------------------------------------------------------------------
DATA DICTIONARY
--------------------------------------------------------------------------
Table: actuals / budgets / forecasts
    month       TEXT    'YYYY-MM', fiscal month (2025-01 .. 2025-12)
    line_item   TEXT    One of LINE_ITEMS (P&L input lines; see below)
    amount      REAL    Dollar amount for that month/line_item

    P&L structure: Gross Profit and Operating Income are SUBTOTALS derived
    by variance.py from the raw line items below — they are intentionally
    NOT stored as rows, so there is exactly one source of truth per number.
    Raw line items stored:
        Revenue, COGS,
        Salaries, Marketing, Facilities, Professional Services, Other
    (the last five are opex lines; Gross Profit = Revenue - COGS;
     Operating Income = Gross Profit - sum(opex lines))

Table: units
    month        TEXT   'YYYY-MM'
    units_sold   INTEGER  Units shipped that month (actuals only; drives
                           the per-unit operating KPIs in kpi.py)

NOTE ON YEAR-OVER-YEAR: this dataset covers exactly one fiscal year
(2025-01..2025-12). There is no second year of real monthly actuals, so
no YoY growth KPI is computed anywhere in this project — a prior-year
baseline synthesized from a single growth-rate assumption would be
fabricated data dressed up as a metric, not genuine history. kpi.py only
reports month-over-month trends and within-year comparisons.

--------------------------------------------------------------------------
NARRATIVE BUILT INTO THE DATA (so downstream modules have something to find)
--------------------------------------------------------------------------
- Revenue has real seasonality (holiday peak in Nov/Dec, winter trough in
  Jan/Feb) and a modest growth trend.
- Budget was set before the year started and is slightly OPTIMISTIC: it
  assumed stronger holiday lift and a richer margin than actually occurred.
- COGS actuals carry a planted mid-year cost spike (Jun-Jul) from a
  supply-chain disruption that was not in the budget — this is the
  variance engine's headline unfavorable driver.
- Professional Services and Marketing actuals run UNDER budget most months
  (deferred consulting spend, leaner campaigns) — these are the headline
  favorable drivers, so the top-3 favorable/unfavorable narrative has real
  signal in both directions, not just a wall of red.
- Forecast is revised quarterly: the Q1 vintage equals the original budget;
  at the start of each subsequent quarter the forecast for the remaining
  months is re-based on the actual run-rate observed so far, so forecast
  accuracy should generally improve as the year progresses.
"""

import sqlite3
from pathlib import Path

import numpy as np

DB_PATH = Path(__file__).parent / "close_pack.db"
FISCAL_YEAR = 2025
MONTHS = [f"{FISCAL_YEAR}-{m:02d}" for m in range(1, 13)]

REVENUE_LINE = "Revenue"
COGS_LINE = "COGS"
OPEX_LINES = ["Salaries", "Marketing", "Facilities", "Professional Services", "Other"]
LINE_ITEMS = [REVENUE_LINE, COGS_LINE] + OPEX_LINES

# Realistic consumer-goods seasonality: winter trough, steady ramp,
# holiday peak in Nov/Dec. Index values average ~1.0 across the year.
ACTUAL_SEASONALITY = {
    1: 0.82, 2: 0.80, 3: 0.88, 4: 0.93, 5: 0.97, 6: 1.00,
    7: 0.96, 8: 0.99, 9: 1.04, 10: 1.10, 11: 1.28, 12: 1.38,
}
# Budget was built with a rosier holiday assumption and a smoother ramp —
# this is the "optimism" baked into the plan.
BUDGET_SEASONALITY = {
    1: 0.86, 2: 0.85, 3: 0.90, 4: 0.95, 5: 0.99, 6: 1.02,
    7: 1.00, 8: 1.03, 9: 1.07, 10: 1.14, 11: 1.35, 12: 1.48,
}

RNG_SEED = 42
BASE_MONTHLY_REVENUE = 520_000.0
ACTUAL_MONTHLY_GROWTH = 0.006   # realized growth, compounding
BUDGET_MONTHLY_GROWTH = 0.010   # planned (optimistic) growth
UNIT_PRICE = 42.50


def _seasonal_index(table: dict, month_num: int) -> float:
    return table[month_num]


def _generate_revenue_and_units(rng: np.random.Generator):
    """Realized monthly revenue + units sold, with seasonality/trend/noise."""
    revenue, units = [], []
    for i, month in enumerate(MONTHS):
        m = int(month.split("-")[1])
        trend = (1 + ACTUAL_MONTHLY_GROWTH) ** i
        noise = rng.normal(loc=1.0, scale=0.015)
        rev = BASE_MONTHLY_REVENUE * _seasonal_index(ACTUAL_SEASONALITY, m) * trend * noise
        revenue.append(round(rev, 2))
        units.append(int(round(rev / UNIT_PRICE)))
    return revenue, units


def _generate_budget_revenue():
    """Budget revenue: smooth, seasonal, optimistic — no noise (set once, pre-year)."""
    budget = []
    for i, month in enumerate(MONTHS):
        m = int(month.split("-")[1])
        trend = (1 + BUDGET_MONTHLY_GROWTH) ** i
        rev = BASE_MONTHLY_REVENUE * _seasonal_index(BUDGET_SEASONALITY, m) * trend
        budget.append(round(rev, 2))
    return budget


def _generate_cogs(actual_revenue, rng: np.random.Generator):
    """Actual COGS ~58% of revenue, plus a planted Jun/Jul supply-chain spike."""
    actual, budget = [], []
    for i, month in enumerate(MONTHS):
        m = int(month.split("-")[1])
        actual_ratio = 0.58 + rng.normal(0, 0.006)
        cogs = actual_revenue[i] * actual_ratio
        if m in (6, 7):
            cogs += 95_000 if m == 6 else 130_000  # supply-chain disruption
        actual.append(round(cogs, 2))
        # Budget assumed a leaner, steady 55.5% COGS ratio — no spike anticipated.
        budget.append(round(_generate_budget_revenue()[i] * 0.555, 2))
    return actual, budget


def _generate_opex(actual_revenue, rng: np.random.Generator):
    """Opex actuals/budget per line. Marketing & Professional Services run
    under budget (favorable); Salaries runs slightly over after a mid-year
    merit increase (unfavorable); Facilities/Other are roughly neutral."""
    actual = {line: [] for line in OPEX_LINES}
    budget = {line: [] for line in OPEX_LINES}
    for i, month in enumerate(MONTHS):
        m = int(month.split("-")[1])
        rev = actual_revenue[i]

        salaries_budget = 92_000 + i * 300
        salaries_actual = salaries_budget * (1.03 if m >= 7 else 1.00) + rng.normal(0, 800)

        marketing_budget = rev * 0.085
        marketing_actual = marketing_budget * (rng.normal(0.88, 0.05) if m not in (10, 11, 12)
                                                else rng.normal(1.05, 0.04))

        facilities_budget = 28_000 + (i // 3) * 500
        facilities_actual = facilities_budget + rng.normal(0, 600)

        prof_services_budget = 15_000 + (400 * (m in (3, 9)))  # quarterly-ish bumps
        prof_services_actual = prof_services_budget * rng.normal(0.80, 0.08)

        other_budget = 9_000
        other_actual = other_budget * rng.normal(0.97, 0.06)

        actual["Salaries"].append(round(salaries_actual, 2))
        budget["Salaries"].append(round(salaries_budget, 2))
        actual["Marketing"].append(round(marketing_actual, 2))
        budget["Marketing"].append(round(marketing_budget, 2))
        actual["Facilities"].append(round(facilities_actual, 2))
        budget["Facilities"].append(round(facilities_budget, 2))
        actual["Professional Services"].append(round(prof_services_actual, 2))
        budget["Professional Services"].append(round(prof_services_budget, 2))
        actual["Other"].append(round(other_actual, 2))
        budget["Other"].append(round(other_budget, 2))
    return actual, budget


def _generate_forecast(actual_by_line: dict, budget_by_line: dict) -> dict:
    """Quarterly-revised forecast. Q1 vintage == budget. At the start of each
    subsequent quarter, the forecast for the remaining months of the year is
    re-based on the actual run-rate observed in the elapsed quarters,
    clipped to +/-15% of budget to keep it plausible."""
    forecast = {line: list(budget_by_line[line]) for line in LINE_ITEMS}
    quarter_starts = [0, 3, 6, 9]  # month indices (0-based) where a new vintage begins
    for q_idx, start in enumerate(quarter_starts[1:], start=1):
        elapsed = slice(0, start)  # months known (actuals) as of this revision
        for line in LINE_ITEMS:
            actual_sum = sum(actual_by_line[line][elapsed])
            budget_sum = sum(budget_by_line[line][elapsed])
            run_rate_factor = actual_sum / budget_sum if budget_sum else 1.0
            run_rate_factor = min(max(run_rate_factor, 0.85), 1.15)
            for m_idx in range(start, 12):
                forecast[line][m_idx] = round(budget_by_line[line][m_idx] * run_rate_factor, 2)
    return forecast


def generate() -> dict:
    """Build the full synthetic dataset. Returns dict of line -> {actual, budget, forecast}
    plus units_sold, all keyed by the 12 MONTHS."""
    rng = np.random.default_rng(RNG_SEED)

    actual_revenue, units_sold = _generate_revenue_and_units(rng)
    budget_revenue = _generate_budget_revenue()
    actual_cogs, budget_cogs = _generate_cogs(actual_revenue, rng)
    actual_opex, budget_opex = _generate_opex(actual_revenue, rng)

    actual_by_line = {REVENUE_LINE: actual_revenue, COGS_LINE: actual_cogs, **actual_opex}
    budget_by_line = {REVENUE_LINE: budget_revenue, COGS_LINE: budget_cogs, **budget_opex}
    forecast_by_line = _generate_forecast(actual_by_line, budget_by_line)

    return {
        "actual": actual_by_line,
        "budget": budget_by_line,
        "forecast": forecast_by_line,
        "units_sold": units_sold,
    }


def _validate(data: dict) -> None:
    """Input validation: shape, sign, and distinctness checks before writing to SQLite."""
    for table_name in ("actual", "budget", "forecast"):
        table = data[table_name]
        assert set(table.keys()) == set(LINE_ITEMS), f"{table_name} missing line items"
        for line, series in table.items():
            assert len(series) == 12, f"{table_name}/{line} must have 12 months, got {len(series)}"
            assert all(v >= 0 for v in series), f"{table_name}/{line} has a negative amount"

    assert len(data["units_sold"]) == 12, "units_sold must have 12 months"
    assert all(u > 0 for u in data["units_sold"]), "units_sold must be positive"

    # Budgets, actuals, and forecasts must genuinely differ (not just copies of each other).
    rev_actual = data["actual"][REVENUE_LINE]
    rev_budget = data["budget"][REVENUE_LINE]
    rev_forecast = data["forecast"][REVENUE_LINE]
    assert rev_actual != rev_budget, "actual revenue must differ from budget"
    assert rev_budget != rev_forecast, "forecast must differ from budget after quarterly revisions"
    assert rev_actual != rev_forecast, "actual revenue must differ from forecast"


def _write_sqlite(data: dict, db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    for table in ("actuals", "budgets", "forecasts"):
        cur.execute(f"""
            CREATE TABLE {table} (
                month TEXT NOT NULL,
                line_item TEXT NOT NULL,
                amount REAL NOT NULL,
                PRIMARY KEY (month, line_item)
            )
        """)
    cur.execute("""
        CREATE TABLE units (
            month TEXT NOT NULL PRIMARY KEY,
            units_sold INTEGER NOT NULL
        )
    """)

    table_map = {"actuals": "actual", "budgets": "budget", "forecasts": "forecast"}
    for sql_table, data_key in table_map.items():
        rows = [
            (month, line, data[data_key][line][i])
            for line in LINE_ITEMS
            for i, month in enumerate(MONTHS)
        ]
        cur.executemany(f"INSERT INTO {sql_table} (month, line_item, amount) VALUES (?, ?, ?)", rows)

    unit_rows = [(month, data["units_sold"][i]) for i, month in enumerate(MONTHS)]
    cur.executemany("INSERT INTO units (month, units_sold) VALUES (?, ?)", unit_rows)

    conn.commit()

    # Verify row counts land exactly where the schema promises: 12 months x 7 line
    # items per P&L table, 12 rows in units.
    for table in ("actuals", "budgets", "forecasts"):
        count = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        assert count == 12 * len(LINE_ITEMS), f"{table} has {count} rows, expected {12 * len(LINE_ITEMS)}"
    units_count = cur.execute("SELECT COUNT(*) FROM units").fetchone()[0]
    assert units_count == 12, f"units has {units_count} rows, expected 12"

    conn.close()


def main():
    data = generate()
    _validate(data)
    _write_sqlite(data, DB_PATH)
    print(f"Seeded {DB_PATH} with {len(MONTHS)} months x {len(LINE_ITEMS)} line items "
          f"across actuals/budgets/forecasts, plus units_sold.")


if __name__ == "__main__":
    main()
