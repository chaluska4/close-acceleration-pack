"""
Pipeline entrypoint: `python -m close_pack` (or `make all`).

Reads the seeded SQLite ledger, runs variance/KPI/controls, and writes
three formatted workbooks to output/. Run `python data/generate_data.py`
first (or use the Makefile, which sequences both steps).
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / "data" / "close_pack.db"
OUTPUT_DIR = REPO_ROOT / "output"


def main() -> None:
    if not DB_PATH.exists():
        print(f"{DB_PATH} not found. Run `python data/generate_data.py` first (or `make all`).",
              file=sys.stderr)
        sys.exit(1)

    from close_pack import controls, excel_export, kpi, variance

    OUTPUT_DIR.mkdir(exist_ok=True)

    var_df = variance.compute_variance(variance.load_pnl(DB_PATH))
    kpi_inputs = kpi.load_kpi_inputs(DB_PATH)
    calendar_df = controls.close_calendar()
    controls_df = controls.evaluate_controls(str(DB_PATH))

    # The close period shown on the Summary/Waterfall/Dashboard sheets is
    # always the most recent month actually present in the data — never a
    # hard-coded literal, so this stays correct if the dataset ever changes.
    current_period = max(var_df["month"])

    excel_export.build_variance_workbook(var_df, current_period, OUTPUT_DIR / "variance_analysis.xlsx")
    excel_export.build_kpi_workbook(kpi_inputs, current_period, OUTPUT_DIR / "kpi_dashboard.xlsx")
    excel_export.build_close_workbook(calendar_df, controls_df, OUTPUT_DIR / "close_checklist.xlsx")

    print(f"Wrote 3 workbooks to {OUTPUT_DIR}/:")
    print("  - variance_analysis.xlsx")
    print("  - kpi_dashboard.xlsx")
    print("  - close_checklist.xlsx")


if __name__ == "__main__":
    main()
