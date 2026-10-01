# Review Log

Self-review appended per phase, checked against the applicable §6
acceptance criteria as of that phase.

---

## 2026-09-30 — Phase 1: Data + schema

**What passed:**
- `python data/generate_data.py` runs clean, seeds `data/close_pack.db`
  with `actuals`, `budgets`, `forecasts` (84 rows each = 12 months x 7 line
  items), `units` (12 rows), `prior_year_revenue` (12 rows).
- `_validate()` assertions confirm actuals != budgets != forecasts for
  Revenue, all amounts non-negative, units positive.
- Manual inspection: Revenue actual consistently below the optimistic
  budget; COGS actual vs budget shows a clean spike in 2025-06 (+$87k) and
  2025-07 (+$127k) with other months tracking closely — the "something for
  the variance narrative to find" requirement is satisfied by construction.

**What failed / gaps:** None at this phase. `prior_year_revenue` is an
addition beyond the literal §2 file tree — see ASSUMPTIONS.md.

**Applicable §6 boxes:** N/A yet (data layer isn't an acceptance criterion
on its own; feeds Phases 2-3 checks below).

---

## 2026-09-30 — Phase 2: Variance engine

**What passed:**
- `close_pack/variance.py`: `load_pnl`, `add_subtotals`, `compute_variance`,
  `waterfall_components`, `top_drivers`, `narrative` all implemented per
  the one-direction-of-data-flow rule (SQLite/DataFrame in, DataFrame/dict
  out — no openpyxl import in this file).
- `tests/test_variance.py`: 8/8 pass via `python -m unittest discover -s
  tests -v`. Covers: Operating Income hand-calc, waterfall components sum
  to total OI variance (both a hand-built toy P&L and a full regression
  over all 12 real-data months), threshold boundary inclusivity and the
  percent/dollar OR logic, and that the narrative's top-3 favorable/
  unfavorable picks are the true largest contributors (not insertion
  order).
- Regression test confirms the planted COGS spike flags in both 2025-06
  and 2025-07 against the default ±5%/$10k threshold.

**What failed / gaps:** None.

**§6 boxes now satisfiable:**
- [x] Variance math verified by tests; waterfall sums to total
      operating-income variance
- [x] Threshold flagging demonstrably catches the planted mid-year cost
      spike

---

## 2026-09-30 — Phase 3: KPI module

**What passed:**
- `close_pack/kpi.py`: 14 KPIs in `KPI_REGISTRY` (>= the 12+ required),
  each a named function with its formula in the docstring. `compute_kpi_table`
  returns long-form month x KPI values with target and RAG status.
- Manual check against `data/close_pack.db`: December 2025 shows a
  realistic, non-degenerate RAG mix (Green/Amber/Red all represented across
  the full year — 85 Green, 53 Red, 28 Amber, 2 N/A from the first month's
  undefined MoM growth), not an all-green or all-red wall.
- `forecast_accuracy_pct` and `revenue_growth_yoy` both compute without
  error using the new `prior_year_revenue` table.

**What failed / gaps:** No dedicated `tests/test_kpi.py` — the build spec's
architecture only names `tests/test_variance.py` explicitly under §2/§4, so
KPI correctness was verified by manual inspection against known inputs
(documented above) rather than an automated suite. Flagged as a known
limitation if it resurfaces; not currently blocking any §6 box (no KPI
testing criterion exists in §6).

**§6 boxes now satisfiable:**
- [x] 12+ KPIs computed with trends and RAG; forecast-accuracy KPI exists

---

## 2026-09-30 — Phase 4: Controls module

**What passed:**
- `close_pack/controls.py`: `close_calendar()` returns a 10-task Day 1-5
  schedule (task, owner role, dependency). `evaluate_controls()` returns
  12 controls spanning all 3 required categories (4 Completeness, 4
  Accuracy, 4 Authorization), each with control ID, description, owner,
  frequency, and evidence reference.
- 8 of the 12 controls are auto-evaluated against the real dataset
  (completeness row counts, waterfall reconciliation, unit-price and
  COGS-ratio reasonableness, forecast re-basing) rather than hardcoded to
  "Pass" — the other 4 are policy/segregation-of-duties controls with no
  data trail in this model, explicitly labeled as manual attestations.
- Verified ACC-03 (COGS ratio reasonableness) genuinely evaluates to
  **Fail** for 2025-06 and 2025-07 — the control framework actually catches
  the planted mid-year cost spike rather than rubber-stamping every check
  as Pass. This is the strongest evidence in the repo that the controls are
  real, not decorative.

**What failed / gaps:** None. ACC-03's "Fail" status is intentional and
documented, not a bug — see ASSUMPTIONS.md.

**§6 boxes now satisfiable:**
- [x] Controls log has 10+ controls across 3 categories with owners and
      evidence refs

---

## 2026-09-30 — Phase 5: Excel export

**What passed:**
- `close_pack/excel_export.py` contains every openpyxl import in the repo;
  `variance.py`/`kpi.py`/`controls.py` remain formatting-free.
- `python -m close_pack` runs clean end to end and writes all 3 workbooks:
  `variance_analysis.xlsx` (Summary, Variance Detail, Waterfall — 3 sheets),
  `kpi_dashboard.xlsx` (Dashboard — 1 sheet, 15 embedded images: 1 overview
  trend chart + 14 KPI sparklines), `close_checklist.xlsx` (Close Calendar,
  Controls Log — 2 sheets).
- Validated "opens cleanly with no warnings" the available way on this
  machine (no Excel/LibreOffice installed): zip integrity check passed for
  all 3 files, and `openpyxl.load_workbook()` raised zero warnings with
  `warnings.filterwarnings("error")` active.
- Visually inspected the extracted waterfall chart, revenue trend chart,
  and a KPI sparkline (saved as PNGs) — all render correctly, match the
  underlying numbers exactly (December's waterfall bars reconcile to the
  Executive Summary narrative sentence-for-sentence), and follow the
  dataviz skill's palette/mark rules (fixed categorical order, single axis,
  legend for 3+ series, thin lines, recessive grid).
- Conditional formatting on Variance Detail is a live openpyxl
  `FormulaRule` bound to the pre-computed flag column (not a duplicated
  threshold formula) — single source of truth stays in `variance.py`.
- All 3 sheets/workbooks use landscape orientation, fit-to-one-page-wide,
  freeze panes on the header row, and NamedStyles for currency/percent.

**What failed / gaps:** Could not verify rendering in actual Excel/
LibreOffice (neither installed in this environment) — verification relied
on zip/openpyxl structural checks plus visual inspection of the extracted
chart images. Documented as a known limitation; the structural checks are
strong secondary evidence (a genuinely corrupt .xlsx fails zip integrity
or throws on load).

**§6 boxes now satisfiable:**
- [x] All 3 workbooks generate, open without warnings, print-ready
      (verified via zip integrity + openpyxl load; not verified in Excel
      itself — see gap above)

---

## 2026-09-30 — Phase 6: Showcase docs

**What passed:**
- `README.md`: 2-sentence problem statement, condensed skills matrix above
  the fold, module tour for all 3 modules with embedded screenshots
  (`docs/waterfall.png`, `docs/revenue_trend.png`, `docs/kpi_rag_summary.png`,
  `docs/controls_summary.png`), "Run it in 60 seconds," a Design Decisions
  section justifying SQLite / openpyxl / module boundaries / synthetic
  data, a Roadmap (Power BI port, ERP connector stub, controls scheduling),
  and a Known Limitations section.
- `SKILLS.md`: full table mapping every §3 skill to exact file(s)/function(s).
- `docs/generate_screenshots.py`: regenerates all 4 README images from the
  live pipeline output (reuses the same render functions that build the
  embedded workbook charts, plus two doc-only summary charts).
- `Makefile`: `all` (data + pipeline), `data`, `pipeline`, `screenshots`,
  `test`, `clean` targets — verified `make clean && make all && make
  screenshots && make test` runs end to end with no errors.
- `requirements.txt` (pandas, openpyxl, matplotlib), `.gitignore` (db,
  output/, `__pycache__/`, `.venv/`) both in place.

**What failed / gaps:** None.

**§6 boxes now satisfiable:**
- [x] `make all` runs clean on a fresh clone (simulated via `make clean &&
      make all`) with only pip-installable deps
- [x] README has skills matrix above the fold, screenshots, 60-second run
      instructions, design decisions, roadmap
- [x] SKILLS.md maps every skill in §3 to file/function evidence
- [x] No real company data anywhere; fictional company clearly labeled as
      synthetic (stated in every module docstring and in the README)

## 2026-09-30 — Final review against all of §6

Ran a genuine fresh-clone simulation: rsync'd the repo (respecting
`.gitignore`) into a scratch directory outside the project, built a brand
new venv there, `pip install -r requirements.txt`, then `make all` and
`make test` — zero pre-existing state (no `.venv`, no `data/close_pack.db`,
no `output/`) carried over. Full checklist:

| # | Criterion | Result |
|---|---|---|
| 1 | `make all` runs clean on a fresh clone with only pip-installable deps | **PASS** — verified in an isolated scratch dir + fresh venv, not just in-place |
| 2 | All 3 workbooks generate, open without warnings, print-ready | **PASS** — zip integrity + `openpyxl.load_workbook()` under `warnings-as-errors`, all clean; landscape + fit-to-width + `fitToPage=True` confirmed on all 6 sheets across the 3 workbooks. *Not verified inside Excel/LibreOffice itself (neither installed here) — see Known Limitations.* |
| 3 | Variance math verified by tests; waterfall sums to total OI variance | **PASS** — 8/8 unit tests; reconciliation reconfirmed for all 12 months in this final pass |
| 4 | Threshold flagging demonstrably catches the planted mid-year cost spike | **PASS** — 2025-06 and 2025-07 COGS both flag `True` |
| 5 | 12+ KPIs computed with trends and RAG; forecast-accuracy KPI exists | **PASS** — 14 KPIs; `forecast_accuracy_pct` present |
| 6 | Controls log has 10+ controls across 3 categories with owners and evidence refs | **PASS** — 12 controls, all 3 categories, `owner`/`evidence_ref` columns populated |
| 7 | README has skills matrix above the fold, screenshots, 60-second run, design decisions, roadmap | **PASS** |
| 8 | SKILLS.md maps every skill in §3 to file/function evidence | **PASS** — all 10 skills mapped |
| 9 | No real company data anywhere; fictional company clearly labeled | **PASS** — "Beacon Outdoor Goods (fictional — synthetic data)" appears in every workbook subtitle and the README |

**Stop condition met**: every §6 box is checked and every phase explanation
is written (above). Known limitations carried into the README rather than
hidden: no Excel/LibreOffice-native render verification in this
environment, `EBITDA Margin %` is a documented proxy, and `kpi.py`/
`controls.py` have no dedicated automated test files (verified by manual
inspection instead, since §2/§4 only name `tests/test_variance.py`
explicitly).

---

## 2026-09-30 — Post-build enhancement pass (external review)

A targeted revision driven by an external review of the output (not a
rebuild): simplify the KPI dashboard, tighten variance-sheet credibility
(units, N/M handling, explicit waterfall reconciliation, management-style
narrative), make the close checklist operational (reviewer/evidence/
status/exception fields), and add cross-cutting financial-safeguard tests.
Architecture, data flow, and workbook filenames unchanged throughout.

**What changed, by file:**
- `data/generate_data.py` — removed `prior_year_revenue` table and
  `_generate_prior_year_revenue()` (fabricated-data risk for an
  unsupportable YoY metric).
- `close_pack/variance.py` — added `IMMATERIAL_DENOMINATOR`/N-M handling,
  `VARIANCE_CONVENTION_NOTE`, `waterfall_reconciliation()`, and a
  management-style `management_summary` narrative sentence.
- `close_pack/kpi.py` — trimmed `KPI_REGISTRY` from 14 to 6 KPIs, renamed
  `ebitda_margin_pct` → `operating_margin_pct`, added
  `compute_executive_kpis()`, `trend()`, `management_insights()`. Removed
  `revenue_growth_yoy`/`revenue_growth_mom`/`cogs_ratio`/`opex_ratio`/
  `units_growth_mom`/`cogs_per_unit`/`salaries_pct_of_revenue`/
  `marketing_pct_of_revenue` (no longer referenced anywhere).
- `close_pack/controls.py` — close calendar gained reviewer/evidence/
  status/exception-notes fields and a realistic in-progress snapshot;
  controls log gained process area/risk/reviewer/exception-remediation
  fields and Effective/Exception status vocabulary; added
  `close_calendar_summary()`/`controls_summary()`.
- `close_pack/excel_export.py` — full KPI dashboard redesign (6 cards +
  insights + 3 charts + compact table, all sparkline images removed);
  Variance Detail gained group headers, N/M cells, a convention note;
  Waterfall sheet gained an explicit reconciliation block; Close/Controls
  sheets gained new columns, status coloring, a summary box, and
  content-driven (not fixed-guess) row heights.
- `close_pack/__main__.py` — updated to the new `build_kpi_workbook(
  kpi_inputs, month, out_path)` signature.
- `docs/generate_screenshots.py` — updated for renamed functions/status
  values; added `margin_trend.png`.
- `tests/test_validation.py` (new) — 13 tests: OI reconciliation,
  favorable/unfavorable sign logic, waterfall reconciles to $0.00 (exact,
  not just within tolerance) for every month, no calculated subtotal used
  as a waterfall driver, no YoY anywhere (registry, module, DB schema),
  forecast has no look-ahead bias (independently reconstructed and
  compared to the generator's actual output), end-to-end workbook
  generation in an isolated temp directory.
- `README.md`, `SKILLS.md`, `ASSUMPTIONS.md` — updated for the above
  (KPI counts, renamed functions, Effective/Exception vocabulary, new
  "Financial Safeguards" section).

**QA performed:**
- `make clean && make all && make screenshots && make test` — clean,
  21/21 tests pass (8 original + 13 new).
- Genuine fresh-clone simulation (isolated temp dir, fresh venv, `pip
  install -r requirements.txt`, `make all`, `make test`) — clean, 21/21.
- Visually extracted and inspected all 3 new/changed dashboard charts
  (Revenue trend, Margin trend, Unit-economics trend) plus the waterfall.
  Found and fixed a real issue: the Margin trend chart's legend (frameon=
  False) rendered illegibly on top of the Gross Margin line, which sits
  near the top of that chart's y-range. Fixed by giving all 3 trend-chart
  legends a white background (`frameon=True, facecolor="white"`).
- Programmatically inspected KPI card/table cell values, merged ranges,
  and formats against hand-checked expected numbers — all correct.
- Found and fixed a second real issue during QA (not flagged by the
  review): Close Calendar and Controls Log row heights were fixed
  constants (32pt/40pt) that would have visually clipped the longest
  wrapped text (187 characters in one Controls Log remediation cell).
  Replaced with `_wrapped_row_height()`, computed from actual content
  length and column width.
- Found and fixed a design smell introduced mid-edit: an early draft of
  the Close Calendar summary box duplicated `close_calendar_summary()`/
  `controls_summary()` logic inside `excel_export.py` instead of
  importing `controls.py` and reusing it. Caught in self-review before
  this was considered done; fixed to import and reuse.

**What failed / gaps:** None outstanding. All acceptance items from the
review brief are satisfied; see the "Financial safeguards" section of
README.md for the user-facing summary.

---

## 2026-09-30 — KPI Dashboard V2 layout fix (release-blocking)

Fixed two release-blocking defects: charts overlapping each other, and the
Executive Dashboard behaving like a fixed-size canvas instead of a normal
scrollable worksheet. Root-caused both (see ASSUMPTIONS.md) rather than
patching symptoms: unsized image embeds + a flat row-advance guess caused
the overlap; a `freeze_panes` set at the KPI table's own row (deep in the
sheet) caused the scroll problem. Rebuilt `build_kpi_workbook()` as a
deliberate vertical layout — title, 6 cards, insights, then a 2x2
chart/table grid at the exact requested anchors (B17/N17/B33/N33) — with
every chart given an explicit, sheet-geometry-derived pixel size.

**QA performed:**
- `make clean && make all && make test` — clean, 29/29 tests pass (21
  prior + 8 new `test_dashboard_layout.py` checks).
- Extracted all 3 dashboard chart images from the saved `.xlsx` and
  visually inspected them at their actual embedded size — correctly
  proportioned (no stretch/squish distortion), legends legible, no
  overlap.
- **Self-caught measurement error during this fix**: my first attempt to
  verify chart sizes read `img.width`/`img.height` on a reloaded
  `openpyxl.Workbook` and got numbers matching the PNG's native pixel
  size (e.g. 1484x785), which looked like the explicit-sizing fix hadn't
  taken effect. Traced this to openpyxl's reader (`reader/drawings.py`)
  reconstructing a fresh `Image` object from the raw embedded PNG bytes
  on load — `.width`/`.height` on that reloaded object always reflect
  the PNG's native size, never the display size that was actually set at
  write time. The real, correct display size lives in
  `img.anchor.ext.cx`/`.cy` (EMU) and confirmed exactly matching the
  intended pixel boxes once read correctly (767x409, 813x409, 767x409).
  Documented so this isn't re-discovered the hard way next time.
- Could not open the file in Excel or LibreOffice directly (neither
  installed in this environment) — verified via: (a) the automated
  overlap/anchor/freeze/scrollbar checks in `test_dashboard_layout.py`,
  (b) extracted-image visual inspection, (c) direct cell-value inspection
  of the card/table regions. The file was also opened via macOS `open`
  for the user's own visual confirmation in their installed spreadsheet
  app.
- Confirmed `variance_analysis.xlsx` and `close_checklist.xlsx` are
  unaffected (zip integrity + load clean) — only `build_kpi_workbook()`
  and its three trend-chart renderers (which gained an optional,
  backward-compatible `figsize` parameter) were touched.

**What failed / gaps:** None outstanding.

---

## 2026-09-30 — KPI Dashboard V3→V4 content/polish pass

14 targeted content/polish fixes on top of the V3 layout fix: Jan-Dec
month labels, $K currency suffixes, "Revenue Budget Attainment" rename,
"vs. KPI Target" vs "vs. Budget" wording split, F/W/U finance notation
replacing literal Red/Amber/Green text (color unchanged), percentage-point
trend variance for ratio KPIs, analyst-specific Risk & Action text,
larger/more-scannable insights text, December end-of-line chart labels,
header/card/chart left-edge alignment, and the KPI detail table moved to
its own tab. No calculation/formula changes — `gross_margin_pct()`,
`operating_margin_pct()`, `budget_attainment_pct()`, etc. are untouched;
only the KPI's display `label` and the presentation layer changed.

**QA performed:**
- `make clean && make all && make screenshots && make test` — clean,
  29/29 tests pass, including all 8 `test_dashboard_layout.py` checks
  (anchors/overlap/freeze/scroll still hold after the content changes).
- Visually extracted and inspected all 3 dashboard chart images: Jan-Dec
  labels render correctly; the Revenue chart's December end-labels
  ($859K/$813K/$775K) are clearly separated with no overlap or clipping;
  the Margin chart's negative Operating Margin values (down to -19% in
  July) remain fully visible, not clipped.
- Programmatically inspected card/table cell values: "Revenue Budget
  Attainment" label confirmed; "vs. Budget" appears only on the two
  dollar cards, "vs. KPI Target" on all four ratio cards; RAG column
  shows F/W/U (not Green/Red); trend column shows "+0.8 pts F" style for
  ratio KPIs and "+8.3% F" style for dollar KPIs; Risk & Action text
  reads as a specific, data-tied recommendation, not "monitor closely."
- Produced `output/kpi_dashboardV4.xlsx` as the specific requested
  deliverable (see ASSUMPTIONS.md for why the canonical
  `output/kpi_dashboard.xlsx` filename was kept for the regular pipeline).
- Confirmed `variance_analysis.xlsx` and `close_checklist.xlsx` remain
  untouched (zip integrity + load clean).

**What failed / gaps:** None outstanding.

---

## 2026-09-30 — Variance Analysis V2→V3 content/credibility pass

Audited `variance_analysis.xlsx` against the new brief before changing
anything. Found the conditional formatting had a real bug (every material
variance colored red regardless of favorability), three months (Feb/Jun/
Jul) with misleading Operating Income percentages from an actual/budget
sign flip, and a hard-coded "2025-12" literal in `__main__.py`. Fixed all
three, plus the requested presentation redesign: 3 KPI cards on Summary,
$K formatting throughout executive content, Yes/— Material? column,
natural (non-robotic) driver commentary filtered to material items only,
renamed Detail headers with exact 3-part number formats, header+ID-column
freeze on Detail, and a compact (880x420px) explicitly-sized Waterfall
chart with a management-facing title and a one-line reconciliation control.

**What changed:**
- `close_pack/variance.py` — sign-flip N/M handling in `compute_variance()`;
  new `material_top_drivers()`; new public `format_k()` (was private,
  fixed a latent negative-sign bug: `-$59K` not `$-59K`); new public
  `month_label()`; rewrote `narrative()`'s bullet/summary text for natural
  phrasing and materiality filtering.
- `close_pack/excel_export.py` — Summary sheet rebuilt (4-line header
  block, 3 KPI cards via new `_write_metric_card()`, trimmed notes);
  Variance Detail rebuilt (renamed headers, exact `$#,##0;($#,##0);-` /
  `0.0%;(0.0%);-` formats, Python-computed favorable/unfavorable/neutral
  fills replacing the buggy blanket-red rule, header+ID-column freeze,
  widened columns); Waterfall rebuilt (month-name chart title without
  "leaf-level" jargon, $K data labels, no gridlines, explicit 880x420px
  size, one-line "Bridge Reconciliation: $0 (Reconciled: Yes)" control).
  Deleted the now-dead `_embed_png()` helper and unused `FormulaRule`
  import.
- `close_pack/__main__.py` — reporting period now computed as
  `max(var_df["month"])` instead of a hard-coded `"2025-12"` literal.
- `docs/generate_screenshots.py` — updated for `render_waterfall_png`'s
  new `month_label` parameter.
- `tests/test_validation.py` — 7 new tests: sign-flip N/M (toy case +
  regression check against the real Feb/Jun/Jul data), materiality-filtered
  commentary (toy case proving immaterial lines never appear in driver
  bullets), `format_k()` (whole-dollar floor, correct negative-sign
  placement).

**QA performed:**
- `make clean && make all && make screenshots && make test` — clean,
  36/36 tests pass (29 prior + 7 new).
- Genuine fresh-clone simulation (isolated temp dir, fresh venv) — clean,
  36/36.
- **Waterfall reconciliation confirmed**: `Bridge Reconciliation: $0
  (Reconciled: Yes)` renders on the sheet for every month; existing
  exact-to-the-penny reconciliation test (`test_reconciles_after_
  rounding_for_every_month`) still passes for all 12 months.
- **Actual/Budget/Forecast source values confirmed unchanged**: spot-
  checked 4 values (Dec Revenue actual/budget, Jun/Dec COGS actual)
  against the same figures recorded earlier in this project's history —
  byte-identical, as expected from an untouched, seeded generator.
- Visually extracted and inspected the Waterfall chart image at its
  actual embedded size (880x420px) — no gridlines, $K labels (including
  the sub-$1K fallback for Facilities/Other, fixed during this pass after
  first spotting a "+$0K" label), management-facing title exactly
  matching the requested format, no overlapping bars/labels.
- Programmatically inspected Summary sheet (4-line header, 3 KPI cards
  with correct $K/parens formatting and favorable/unfavorable accent
  color), Variance Detail (renamed headers, correct green/red/neutral
  fills on a known favorable row and a known unfavorable row, N/M on the
  known Feb sign-flip row, `freeze_panes == "C4"`), and Waterfall
  (reconciliation text, $K bridge detail table) — all matched expected
  values exactly.
- Confirmed `kpi_dashboard.xlsx` and `close_checklist.xlsx` unaffected
  (zip integrity + load clean; only `variance.py`, the variance-workbook
  functions in `excel_export.py`, and `__main__.py`'s period computation
  were touched).

**What failed / gaps:** None outstanding.

---

## 2026-10-01 — Waterfall label overlap, forecast comparison, units, reconciliation

Five targeted fixes on `variance_analysis.xlsx`: waterfall x-axis label
overlap (Facilities/Professional Services), forecast comparison missing
from the Summary sheet, redundant "$000s"+"$109K" unit labeling, a
reconciliation control that wasn't auditable enough, and a Variance Detail
note that didn't explain why a negative $ can be green.

**What changed:**
- `close_pack/variance.py` — `narrative()` now computes `forecast_oi`/
  `oi_variance_forecast`; `_management_summary()` states both comparisons
  in one sentence ("...unfavorable to budget but $YK favorable to the
  latest forecast, driven by...").
- `close_pack/excel_export.py` — `render_waterfall_png()` widened default
  figsize and abbreviates "Professional Services" to a 2-line
  "Professional\nSvcs." label; `_build_waterfall_sheet()` chart widened
  to 1000x420px, subtitle changed to "USD (rounded to nearest $K)", added
  a 3-line "Reconciliation Detail" block (Sum/Variance/Difference,
  Difference at full precision) alongside the existing one-line
  indicator; `_build_variance_summary_sheet()` gained a 4th "Variance to
  Forecast" KPI card and the same subtitle wording change;
  `_build_variance_detail_sheet()`'s note rewritten to explicitly state
  that color reflects economic impact, not the raw $ sign.

**QA performed:**
- `make clean && make all && make screenshots && make test` — clean,
  36/36 tests pass (no new tests needed; existing coverage for
  reconciliation, favorability, materiality, and N/M already applied to
  the changed code paths).
- Genuine fresh-clone simulation — clean, 36/36.
- **Explicit 12-month x 3-scenario OI reconciliation check** (Revenue −
  COGS − opex = Operating Income, for actual/budget/forecast, every
  month) run directly against the regenerated database — all 36 checks
  pass.
- **Visually extracted and inspected the widened waterfall chart**: all 9
  bars/labels (Budget OI, Revenue, COGS, Salaries, Marketing, Facilities,
  "Professional Svcs.", Other, Actual OI) are clearly separated with no
  overlap or clipping at the chart's actual embedded size — this was the
  release-blocking issue and is now confirmed resolved by direct
  inspection, not just by the pixel-sizing math.
- Programmatically confirmed: 4th card value/accent (Variance to Forecast
  = +$15K, green/favorable), both subtitles read "USD (rounded to nearest
  $K)", reconciliation Difference cell is `$#,##0.00` format showing `0`,
  `freeze_panes` on Variance Detail still `"C4"` (preserved, unchanged).
- Confirmed `kpi_dashboard.xlsx` and `close_checklist.xlsx` unaffected.

**What failed / gaps:** None outstanding.

---

## 2026-10-01 — Phase 19: KPI Dashboard card label plain-language polish

**Request:** Replace abbreviated KPI-card trend text (e.g. "U  +8.3% F")
with plain, management-facing labels stating both status and trend (e.g.
"Status: Under Target | MoM: +8.3%"), generated dynamically, preserving
favorable/unfavorable color logic, fitting cleanly at 100% zoom. No other
workbook, calculation, chart data, or dashboard layout change.

**What changed:**
- `close_pack/excel_export.py`: added `_card_status_label(value, target)`
  (positional Above/Under/On Target, direction-agnostic — see
  ASSUMPTIONS.md for why) and `_card_mom_text(card)` (the MoM numeric text
  only, no F/U letter), both built from `kpi_mod.trend()`/card fields —
  nothing hardcoded. `_write_kpi_card()`'s trend_row now writes
  `"Status: {position}\nMoM: {mom text}"`, wrap_text=True, row height 28pt.
  Font color still comes from `RAG_FILL_FONT`/`font_hex` (unchanged
  mechanism) — color-coded favorability is fully preserved.
- `_trend_display_text()` (the old abbreviated formatter) and `RAG_LABEL`
  are untouched and still used by the compact "KPI Detail" tab's
  Trend(MoM)/RAG columns — confirmed byte-identical after regen (see
  verification below).

**What passed:**
- Fresh regen via `make clean && make all` — clean run, 3 workbooks
  written, no errors.
- Full suite: `python -m unittest discover -s tests -v` — 60/60 pass,
  including all 7 `test_dashboard_layout.py` chart/freeze/scroll checks
  (layout genuinely untouched).
- Programmatic inspection of all 6 cards' row-9 trend text, font, and fill
  on the regenerated `output/kpi_dashboard.xlsx`:
  - Revenue: "Status: Under Target\nMoM: +8.3%" — red (FF9C0006 font /
    FFD03B3B strip), matches prior RAG=Red/U.
  - Revenue Budget Attainment: "Status: Under Target\nMoM: -2.0 pts" — red.
  - Gross Margin %: "Status: Above Target\nMoM: +0.8 pts" — green
    (FF006100 / FF0CA30C), matches prior RAG=Green/F.
  - Operating Income: "Status: Under Target\nMoM: +33.7%" — red.
  - Operating Margin %: "Status: Above Target\nMoM: +2.7 pts" — green.
  - Forecast Accuracy %: "Status: Above Target\nMoM: -2.3 pts" — green.
  - All 6: font size 9, bold, `wrap_text=True`, `vertical=center`,
    `horizontal=center`; merged 3-column range (B:D, F:H, J:L, N:P, R:T,
    V:X) each at column width 9 (204px); row 9 height 28pt. Longest line
    is 21 characters ("Status: Under Target" / "Status: Above Target"),
    comfortably under the ~204px card width at 9pt bold Calibri — no
    clipping risk on either line.
  - KPI Detail tab's Trend(MoM)/RAG columns confirmed unchanged: still
    "+8.3% F" / "U" style for all 6 rows.

**What failed / gaps:** None. All 6 cards verified individually; no
regressions in any other sheet or workbook.

---

## 2026-10-01 — Phase 20: Management Insights clipping fix + KPI Detail RAG plain text

**Request:** (1) Fix clipped Management Insights labels ("Top"/"Top"/"Ris")
so "Top Favorable Driver:", "Top Unfavorable Driver:", and "Risk & Action:"
render in full. (2) Replace coded F/U in the KPI Detail tab's RAG column
with "Above Target"/"Under Target", keeping existing green/red conditional
formatting and status logic. No calculation, source data, chart, or
dashboard-layout change.

**What changed:**
- `_write_management_insights()`: label now merged A:D (was column A alone,
  width 3) and narrative start shifted from B to E. Root cause: column A is
  only ~26px wide, and Excel truncates (rather than overflows) text when
  the adjacent cell is non-empty — which the narrative cell always was.
- `_write_kpi_table()`'s RAG cell: text now `_card_status_label(card
  ["value"], card["target"])` instead of the old `RAG_LABEL.get(rag, rag)`
  F/U/W lookup. Fill/font color still from `RAG_FILL_FONT`/`rag` —
  unchanged. Column F widened 8->16 in `_build_kpi_detail_sheet` to fit the
  longer text.
- Removed `RAG_LABEL` (dead code after this change) — confirmed via
  repo-wide grep no other reference existed.

**What passed:**
- Fresh regen via `make clean && make all` — clean, no errors.
- Full suite: `python -m unittest discover -s tests -v` — 60/60 pass.
- Programmatic inspection of `output/kpi_dashboard.xlsx`:
  - Dashboard rows 12-14: label text is the full `"Top Favorable Driver:"`
    / `"Top Unfavorable Driver:"` / `"Risk & Action:"` (not truncated),
    each in its own `A{row}:D{row}` merge; narrative text intact in a
    separate `E{row}:Y{row}` merge — label and narrative no longer share a
    cell, so neither can clip or overlap the other.
  - KPI Detail RAG column (F5:F10): "Under Target" (red, FFFFC7CE fill /
    FF9C0006 font) for Revenue, Revenue Budget Attainment, Operating
    Income; "Above Target" (green, FFC6EFCE / FF006100) for Gross Margin %,
    Operating Margin %, Forecast Accuracy % — matches the prior round's
    F/U pattern exactly (same 6 KPIs, same favorability), confirming the
    text changed but the underlying status logic didn't. Column F width
    confirmed 16.
  - KPI Detail Trend (MoM) column confirmed unchanged: still "+8.3% F" /
    "-2.0 pts U" style for all 6 rows — scope held to only the RAG column.

**What failed / gaps:** None outstanding.
