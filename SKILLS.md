# Skills → Evidence Map

Every skill below is demonstrated in the code itself — not just claimed.
File paths and function names are exact; open them to verify.

| Skill | Where it shows up |
|---|---|
| **Variance analysis** | `close_pack/variance.py` — `compute_variance()`, `waterfall_components()`, `top_drivers()`, `narrative()`. Tested in `tests/test_variance.py`. Rendered in `close_pack/excel_export.py` — `render_waterfall_png()`, `_build_variance_detail_sheet()`, `_build_variance_summary_sheet()`. |
| **Month-end close** | `close_pack/controls.py` — `CLOSE_CALENDAR` (Day 1-5 task list, owner, reviewer/approver, dependency, evidence, status, exception notes), `close_calendar()`, `close_calendar_summary()`. Rendered in `close_pack/excel_export.py` — `_build_close_calendar_sheet()`. |
| **Budgeting & forecasting** | `data/generate_data.py` — `_generate_budget_revenue()` (pre-year plan), `_generate_forecast()` (quarterly re-basing off *elapsed-quarter* actuals only — no look-ahead, verified in `tests/test_validation.py`). `close_pack/variance.py` — `compute_variance()` compares actual against *both* budget and forecast. `close_pack/kpi.py` — `budget_attainment_pct()`, `forecast_accuracy_pct()`. |
| **KPI dashboarding** | `close_pack/kpi.py` — `KPI_REGISTRY` (6 executive KPIs), `compute_executive_kpis()`, `trend()`, `rag_status()`, `management_insights()`. Rendered in `close_pack/excel_export.py` — `build_kpi_workbook()`, `_write_kpi_card()`, `render_margin_trend_png()`, `render_unit_economics_png()`. |
| **Process automation** | `Makefile` (`make all`) and `close_pack/__main__.py` — `main()`. One command takes a seeded SQLite ledger to three formatted workbooks; see README "Run it in 60 seconds." |
| **Internal controls** | `close_pack/controls.py` — `CONTROLS_LOG` (12 controls across Completeness/Accuracy/Authorization, each with a process area, risk statement, owner, reviewer, and evidence retained), `evaluate_controls()`, `controls_summary()`. Rendered in `close_pack/excel_export.py` — `_build_controls_log_sheet()`. Informed by completeness/accuracy/authorization/evidence-retention/exception-management principles — not a claim of SOX compliance or audit-readiness. |
| **Python (pandas)** | `close_pack/variance.py`, `close_pack/kpi.py`, `close_pack/controls.py` — every calculation is a pandas DataFrame/Series transform, zero manual loops over raw rows for the math itself. |
| **Excel (advanced)** | `close_pack/excel_export.py` — live conditional formatting (`FormulaRule` in `_build_variance_detail_sheet()`), registered `NamedStyle`s (`_register_named_styles()`), embedded matplotlib charts via `openpyxl.drawing.image` (`render_waterfall_png()`, `render_revenue_trend_png()`, `render_margin_trend_png()`, `render_unit_economics_png()`), display-scaled `$000s` number formats (`CURRENCY_000_FMT`), print setup + freeze panes (`_print_setup()`). |
| **SQLite** | `data/generate_data.py` — `_write_sqlite()` builds the `actuals`/`budgets`/`forecasts`/`units` schema; data dictionary is in the module docstring. |
| **Data validation** | `data/generate_data.py` — `_validate()` (shape, sign, distinctness checks before any row is written). `close_pack/controls.py` — `COMP-01`..`COMP-04` (completeness controls evaluated live against the generated data). `tests/test_validation.py` — OI reconciliation, sign logic, waterfall reconciliation, no-subtotal-as-driver, no-YoY-without-history, no-look-ahead-forecast, end-to-end workbook generation. |

## A note on the controls framework

Eight of the twelve controls in `CONTROLS_LOG` are evaluated live against
the actual dataset — they can genuinely come back "Exception." `ACC-03`
(COGS ratio reasonableness) does, every run, against 2025-06 and 2025-07:
it catches the planted mid-year supply-chain cost spike and carries a
specific remediation note. That's deliberate — a controls framework that
always shows green isn't evidence of anything. This log demonstrates
internal-controls awareness applied to a hypothetical company; it is not
a claim of SOX compliance, audit-readiness, or enterprise-grade coverage.
