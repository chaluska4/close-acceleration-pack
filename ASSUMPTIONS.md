# Assumptions & Judgment Calls

Logged as they're made, per the build spec's "never silently" rule. Each
entry: the call, and why.

## Phase 1 — Data + schema

- **Fictional company**: "Beacon Outdoor Goods," a consumer goods company,
  fiscal year 2025 (`2025-01`..`2025-12`). Clearly synthetic, invented for
  this project — no real company data anywhere.
- **Gross Profit / Operating Income are not stored as SQLite rows.** The
  architecture spec lists them as P&L lines, but storing them alongside raw
  inputs would create two sources of truth for the same number (a stored
  subtotal that could drift from its components). They're computed by
  `variance.add_subtotals()` from the raw line items every time the data is
  loaded. Documented in the `generate_data.py` data dictionary.
- **Added a `prior_year_revenue` table** (month_num 1-12, amount) not in the
  original §2 architecture diagram. The spec requires a Revenue Growth YoY
  KPI, which is mathematically impossible with only one fiscal year of P&L
  detail. Rather than fabricate a second full year of budget/forecast data
  (out of scope) or skip the KPI (violates §6), I added a minimal one-column
  table holding FY2024 revenue by calendar month, back-derived from FY2025
  actuals at an assumed 9% YoY growth rate plus independent noise. This is a
  deviation from the literal §2 file tree (it's an extra table, not an extra
  file) — flagged here per the spec's own rule.
- **Mid-year cost spike lives in COGS (Jun/Jul)**, sized at +$95k / +$130k,
  framed as a supply-chain disruption. Chosen over spreading the spike
  across multiple lines so the variance narrative has one clear, defensible
  headline driver rather than several small ones.
- **Budget "optimism"** is modeled as a richer holiday seasonality
  assumption + faster planned growth rate for Revenue, and a leaner assumed
  COGS ratio (55.5% vs. a realized ~58%) — not a flat percentage haircut on
  actuals. Budget is generated independently of actuals (no
  actuals-informed fudge factor), which is how real annual budgets are
  built and is what makes the variance story defensible on inspection.
- **Forecast vintages are quarterly**, re-based on the actual run-rate of
  elapsed quarters and clipped to +/-15% of budget. Q1 forecast == original
  budget (no actuals exist yet to revise from).

## Phase 2 — Variance engine

- **Threshold flag logic is OR, not AND**: a line flags if it breaches
  EITHER the percent threshold or the dollar threshold. This catches both a
  big percentage swing on a small base and a moderate percentage swing on a
  large base (e.g., a $10k COGS miss that's only 3% of a large COGS base
  still matters operationally).
- **Boundary is inclusive** (`>=`), so a variance landing exactly at 5% or
  exactly at $10,000 flags. Tested explicitly in `test_variance.py`.
- **Waterfall bridge walks Revenue -> COGS -> the five opex lines in that
  order** (not sorted by size), matching how a controller reads a P&L
  top-to-bottom. Favorable-vs-unfavorable coloring on the chart is a
  presentation concern and lives in `excel_export.py`.

## Phase 3 — KPI module

- **EBITDA margin % is a proxy** (= Operating Income / Revenue). The model
  has no D&A or interest line items, so true EBITDA can't be derived; the
  KPI is labeled "EBITDA Margin % (proxy)" everywhere it's displayed so it's
  never mistaken for a GAAP figure.
- **Budget Attainment %** is defined as Revenue actual/budget, the standard
  FP&A usage (sales-plan attainment), not Operating Income attainment.
- **Forecast Accuracy %** is computed on Revenue only (`1 - |actual -
  forecast| / actual`, floored at 0), the line every quarterly forecast
  revision in the data generator is actually targeting.
- **RAG tolerance defaults to a 5% band**: within 5% of target on the wrong
  side is Amber; beyond that is Red. Configurable per-call via
  `rag_status(..., tolerance=...)`.
- **14 KPIs implemented** (spec requires 12+): 8 financial, 6 operating.
  Chose real, distinct operating KPIs (revenue/COGS/total-cost per unit,
  units growth, salaries % and marketing % of revenue) over padding with
  near-duplicates.

## Phase 4 — Controls module

- **8 of 12 controls are auto-evaluated against the real dataset**; the
  other 4 (all Authorization-category) are policy/segregation-of-duties
  controls — "budget signed off by Finance Director," "JEs over $25k
  require second approver," etc. — with no transaction-level data to check
  against in this model. Those are explicitly labeled as manual
  attestations with a synthetic evidence reference, never silently marked
  Pass as if data-verified.
- **ACC-03 (COGS ratio reasonableness) is designed to FAIL** for 2025-06
  and 2025-07 against the real generated data, because the planted
  supply-chain cost spike genuinely falls outside the 50-62% reasonableness
  band. This is intentional: a controls framework where every check always
  passes isn't credible evidence of internal-controls skill — a framework
  that catches a real, planted anomaly is.
- **Control categories map 1:1 onto annuity-operations document validation**
  (completeness = all required data/pages present; accuracy = data ties out
  to source; authorization = proper sign-off/access) as instructed in §1.

## Phase 5 — Excel export

- **"Sparklines" are rendered as small matplotlib line-chart PNGs**, not
  native Excel sparklines. openpyxl has no public API for Excel's native
  Sparkline object (it's not implemented in the library), so the spec's
  "sparklines or small charts" either/or is satisfied via the "small
  charts" branch — each one colored by that KPI's latest RAG status so it
  visually echoes the RAG column beside it.
- **Waterfall/trend charts are matplotlib PNGs embedded via
  `openpyxl.drawing.image`**, per the explicit Phase 5 instruction — not
  native openpyxl chart objects. This is also why README screenshots are
  possible: the same render functions produce the chart images used both
  in the workbook and in `docs/`.
- **Chart colors follow the dataviz skill's reference palette**
  (`references/palette.md`): fixed-order categorical hues for Actual/
  Budget/Forecast (never reused for a 4th series), the reserved status
  palette for favorable/unfavorable and RAG, single axis everywhere, and a
  legend whenever 2+ series share a chart. Spreadsheet CELL shading uses
  Excel's own conventional light-fill/dark-font red-amber-green instead of
  the chart status hexes — different medium, different (but standard)
  idiom.
- **Conditional formatting references the pre-computed flag column**
  (`FormulaRule` on `flag_vs_budget`) rather than re-implementing the
  ±5%/$10k threshold as a native Excel formula, keeping the threshold
  logic in exactly one place (`variance.py`).
- **"Opens cleanly with no warnings" verified structurally**, not visually
  in Excel/LibreOffice (neither is installed in this environment): zip
  integrity check + `openpyxl.load_workbook()` under
  `warnings.filterwarnings("error")` on all 3 output files, both clean.
  Documented as a known limitation in REVIEW.md.
- **Current close period shown in Summary/Waterfall is the latest month
  (2025-12)**, matching how a real close reports one period at a time; the
  Variance Detail sheet still carries the full 12-month table.

## Phase 6 — Showcase docs

- **`docs/generate_screenshots.py` is a standalone script**, not part of
  the `close_pack` package, since screenshot generation is a documentation
  concern, not part of the deliverable pipeline (`close_pack/__main__.py`
  writes workbooks; it never writes to `docs/`). It reuses
  `excel_export`'s render functions rather than duplicating chart code.
- **Two screenshots (`kpi_rag_summary.png`, `controls_summary.png`) exist
  only in `docs/`**, not as workbook content — they're summary views built
  specifically to give Modules B and C their own README visual, since
  their actual workbook content (a 14-row KPI table, a 12-row controls
  table) doesn't screenshot as compellingly as a chart does.

## Post-build enhancement pass (targeted review-driven revision)

A second pass, driven by an external review, tightened credibility and
simplified the KPI dashboard without changing the pipeline's architecture,
data flow, or output filenames.

- **Removed `revenue_growth_yoy` and the `prior_year_revenue` table
  entirely** rather than gating it behind a history check. The dataset
  has exactly one fiscal year of real monthly actuals; the prior-year
  baseline was back-derived from a single assumed growth rate, which is
  fabricated data dressed up as a trend. Deleting it (instead of leaving
  dead code behind a flag) keeps the codebase honest about what it can
  and can't compute. Enforced by `tests/test_validation.py`.
- **`ebitda_margin_pct` renamed to `operating_margin_pct`** — same
  formula (`Operating Income / Revenue`), but never called EBITDA
  anywhere, including in variable/function names. The model still has no
  D&A/interest data, so the number itself didn't change, only its name —
  the prior "(proxy)" caveat approach still let the term "EBITDA" appear
  in the workbook, which a reviewer could reasonably read as
  overstating the metric.
- **KPI dashboard trimmed from 14 KPIs (with 14 embedded sparkline images)
  to exactly 6 executive cards** (Revenue, Budget Attainment %, Gross
  Margin %, Operating Income, Operating Margin %, Forecast Accuracy %)
  plus 3 trend charts. `revenue_per_unit` and `total_cost_per_unit` are
  still computed (they're what Chart 3 plots) but are intentionally not
  among the 6 cards — chosen to be chart-only rather than card+chart to
  avoid re-inflating the card count. `cogs_ratio`, `opex_ratio`,
  `revenue_growth_mom`, `units_growth_mom`, `cogs_per_unit`,
  `salaries_pct_of_revenue`, and `marketing_pct_of_revenue` were removed
  from the codebase (not just hidden) since nothing downstream still used
  them — dead code is itself a code-quality smell a reviewer would flag.
- **Per-KPI sparkline images were removed, not shrunk.** The style
  guidance explicitly said "no tiny chart elements," and a 14-row table of
  embedded images was the specific thing being fixed. The compact table's
  "Trend" column is now a text arrow + MoM % (`▲ +8.3% MoM`), colored by
  whether that change was favorable given the KPI's direction — legible at
  table-row scale without needing a rendered image at all.
- **Budget Attainment % target changed from 0.95 to 1.00 (100%).**
  "Attainment" conventionally means hitting 100% of budget; the RAG
  tolerance band (Amber down to 95%, Red below) already does the work of
  not punishing a small miss, so the target itself should read as the
  actual budget, not a pre-discounted one.
- **`$000s` display on the dashboard uses Excel's trailing-comma number
  format trick** (`'$#,##0,'`), not a value division in Python. The
  stored cell value is the real, full-precision dollar amount — only the
  *display* is scaled. This means a formula referencing that cell
  elsewhere in the workbook would still get the correct number, and it
  does not lose precision the way pre-dividing the value would.
- **Variance % is "N/M" (not meaningful) when the comparison base is
  zero or under $1,000** (`IMMATERIAL_DENOMINATOR`), applied uniformly via
  `variance.compute_variance()` rather than patched in at display time —
  keeps one source of truth for what counts as a meaningful percentage.
  No line item in the current dataset actually triggers this (all bases
  are well above $1,000), but the safeguard exists for robustness and is
  exercised by a dedicated boundary test.
- **Controls status vocabulary changed from Pass/Fail to
  Effective/Exception.** Standard internal-audit/SOX-adjacent language,
  and pairs naturally with the new `exception_remediation` column — "Fail"
  has no natural continuation, "Exception" does ("Exception, remediation:
  ...").
- **Close calendar shows a realistic in-progress snapshot** (4 Complete, 1
  Exception, 2 In Progress, 3 Not Started), not a blank template with
  every status defaulted to "Not Started." A demo that shows the tool
  mid-use, including one task that's flagged an exception and escalated,
  is stronger evidence of realistic close operations than an all-pending
  list — the Exception's dollar figure and escalation note are synthetic
  but internally consistent with the rest of the demo data.
- **Row heights on the Close Calendar and Controls Log sheets are computed
  from actual text length** (`_wrapped_row_height()`), not a fixed guess.
  The longest Controls Log remediation text is 187 characters — a fixed
  40pt row height would have visually clipped it. This was caught during
  this pass's own QA pass, not by the external review.
- **`excel_export.py` now imports `controls.py` directly** (in addition to
  `kpi.py`/`variance.py`) to reuse `close_calendar_summary()`/
  `controls_summary()` for the new top-of-sheet summary box, rather than
  duplicating that aggregation logic inside the presentation layer. This
  is consistent with the existing one-directional data flow rule (calc
  modules never import `excel_export`; `excel_export` may import any calc
  module) — an earlier draft of this change mistakenly duplicated the
  summary functions instead of importing them, which was caught and fixed
  before this was considered done.

## KPI dashboard layout fix (release-blocking overlap/scroll bug)

- **Root cause of chart overlap**: charts were embedded via `ws.add_image()`
  with no explicit size, so each one rendered at its PNG's native pixel
  size (~1800x500px at 200 DPI) while the code advanced to the next
  chart's row by a flat guess (`row += 16`) — nowhere near enough for an
  image that tall, so charts overlapped.
- **Root cause of the "frozen wide canvas" feel**: `_write_kpi_table()`
  was setting `ws.freeze_panes` at its own header row (deep in the sheet,
  ~row 64 under the old layout), freezing almost the entire dashboard in
  view. Fixed by moving to a single, modest `"A5"` freeze set once at the
  top level of `build_kpi_workbook()` — `_write_kpi_table()` no longer
  touches `freeze_panes` at all.
- **Chart sizing is now pixel-exact, computed from the sheet's own actual
  column widths/row heights** (`_range_pixel_box()`), not a hardcoded
  guess — so it stays correct even if column widths change later. Each
  chart is also rendered with a matplotlib `figsize` whose ASPECT RATIO
  matches its target box (`_figsize_for_box()`) before being resized to
  the exact box, so the resize is a clean downscale, never a distorting
  stretch/squish.
- **Verifying an embedded image's resulting size requires reading
  `img.anchor.ext` (EMU), not `img.width`/`img.height` after a reload.**
  openpyxl's reader reconstructs `Image` objects from the raw embedded PNG
  bytes on load, so `.width`/`.height` always report the PNG's native
  pixel size post-reload regardless of what display size was set at write
  time — only the anchor's `ext.cx`/`ext.cy` reflects the actual size
  Excel will render. This tripped up my own first verification pass
  during this fix (documented in REVIEW.md) before I traced it to
  openpyxl's `reader/drawings.py` reconstructing a fresh `Image` from
  scratch rather than preserving the original object's overridden size.
- **KPI cards widened from 2 to 3 columns each** (`CARD_WIDTH`) so the
  6-card row spans roughly the same total width as the chart grid below
  (columns B:Y) — visual consistency was not explicitly requested but is
  implied by "deliberate vertical layout" and "polished."

## KPI Dashboard V4 content/polish pass

- **`output/kpi_dashboard.xlsx` stays the canonical pipeline filename.**
  The V4 brief asked for the file as `kpi_dashboardV4.xlsx`; rather than
  rename the pipeline's established output (which every prior round
  explicitly said not to do), all the V4 improvements were made to the
  actual `build_kpi_workbook()` function — so the canonical dashboard
  permanently carries them — and `output/kpi_dashboardV4.xlsx` is produced
  as an additional one-off snapshot of that same function for this
  specific delivery. It is not part of `make all`/the Makefile.
- **RAG status has two vocabularies now, by design**: `kpi.rag_status()`
  still returns "Green"/"Amber"/"Red" (used for cell/accent COLOR via
  `RAG_COLOR`/`RAG_FILL_FONT` — unchanged, since color is the actual
  visual-aid mechanism), while a presentation-only `RAG_LABEL` map in
  `excel_export.py` turns that into F/W/U TEXT for cards and the table.
  The Risk & Action prose sentence uses full English adjectives
  ("unfavorable", "a watch item") instead of single-letter codes — a
  single letter mid-sentence doesn't read like analyst prose, which is
  what that specific text needs to sound like.
- **Trend notation branches on `card["fmt"]`**: percentage-POINT delta
  ("+2.1 pts F") for ratio/margin KPIs, relative percent change ("+8.3%
  F") for dollar KPIs — a relative "% change of a percentage" (e.g. 40%
  to 42% read as "+5%") is the specific confusing pattern being replaced;
  a point delta is unambiguous for a ratio.
- **"vs. Budget" vs. "vs. KPI Target" is driven by a new `target_kind`
  field** set when each card is built (`"budget"` for the two raw P&L
  dollar cards, whose target IS that month's actual budget line;
  `"kpi_target"` for every KPI_REGISTRY-sourced ratio card, whose target
  is a configured threshold). Applied to all four ratio cards for
  consistency, not just Operating Margin — leaving 3 of 4 still saying
  the ambiguous "vs. target" while only fixing one would have been
  inconsistent.
- **Risk/Action next-step text is a recommended INVESTIGATIVE step, not a
  fabricated cause.** The model has no product/channel/volume-level
  detail, so it can't actually attribute a revenue miss to a channel —
  but recommending "review by volume/product/channel" as the standard
  next diagnostic an FP&A analyst would run is legitimate without that
  detail in hand; it's a process recommendation, not a business claim the
  data doesn't support.
- **KPI Detail table moved to its own sheet tab** rather than trying to
  make it fit more cleanly in the Dashboard's 4th grid quadrant — a real
  6-row/6-column cell-data table sharing the same tight 22pt row heights
  as an image grid looked cramped. The Dashboard sheet leaves a one-line
  pointer at N33 instead of deleting the table.
- **December-only end-of-line chart labels** (Revenue trend only, per the
  request) use `ax.annotate` with an offset in points, and `xlim` is
  widened to leave room — otherwise the last label would clip at the
  chart's right edge, and the chart's explicit box-fit sizing would crop
  it rather than shrink to accommodate it.

## Variance Analysis V2→V3 content/credibility pass

- **Conditional formatting was a real bug, not just a style choice.** The
  old rule colored EVERY materially-flagged row red, including favorable
  ones (e.g. COGS coming in significantly under budget — a good thing —
  showed red purely because it cleared the threshold). Replaced with
  Python-computed fills (green if material+favorable, red if
  material+unfavorable, untouched if immaterial), since favorability
  depends on line-item classification (revenue-like vs. cost) that isn't
  naturally expressible as a live Excel formula without adding backend
  columns the brief explicitly asked to avoid. The materiality *threshold*
  itself remains entirely in `variance.py` (single source of truth) — only
  the color-selection mechanism moved from a formula rule to a direct fill.
- **Sign-flip N/M is a new, real correctness fix, not just polish.** Three
  months in the actual dataset (Feb/Jun/Jul 2025) have Operating Income on
  the opposite side of zero from budget OI, which produced misleading
  percentages (-122.8%, -191.5%, -281.7%) before this fix. Confirmed by
  querying the real data before implementing, not assumed.
- **`format_k()` is now public** (was `_format_k`) so `excel_export.py` can
  reuse the same $K-with-$1K-floor-and-conventional-negative-sign logic
  for the waterfall chart's data labels, instead of duplicating slightly
  different rounding logic in two places. Fixing the negative-sign
  placement (`-$59K` instead of `$-59K`) was caught by writing the
  targeted test for it, not by inspection — the bug was latent (invisible
  for December, since Dec's actual OI is positive) and would only have
  surfaced if the reporting period were ever Feb/Jun/Jul.
- **The old 3-line Reconciliation block (Sum / Variance / Difference) was
  replaced with one prominent line** ("Bridge Reconciliation: $0
  (Reconciled: Yes)") rather than kept alongside a new one — the brief
  asked for a "visible but unobtrusive" control, and three technical rows
  reads as the opposite of unobtrusive. The Bridge Detail table below it
  still carries the full per-line numbers for anyone who wants to verify
  by hand.
- **`build_variance_workbook()`'s `threshold_pct`/`threshold_abs`
  parameters were removed** (not just left unused) — they only ever fed
  the now-removed "Threshold: ±5%..." title text; `var_df` already
  reflects whatever threshold was used to compute it, so the parameters
  were dead weight once that display line was cut.
- **`_embed_png()` (the original unsized-embed helper) and the unused
  `FormulaRule` import were deleted**, not left in place — `_embed_png`
  was the exact pattern that caused the KPI dashboard's original chart
  overlap bug in an earlier round; leaving it available invites reuse of
  a known-bad pattern.
- **The Waterfall chart's explicit 880x420px size** is a fixed constant
  (not computed from a multi-chart grid like the KPI dashboard's, since
  this sheet only ever has one chart — no overlap risk to design around,
  so the simpler fixed-size approach is appropriate here, not
  under-engineering).

## Variance Analysis — label overlap, forecast comparison, units, reconciliation

- **Waterfall chart widened to 1000x420px** (from 880x420) and
  "Professional Services" relabeled "Professional\nSvcs." (two lines) —
  the combination needed to fully clear the overlap, confirmed visually;
  widening alone or abbreviating alone was not tested as sufficient in
  isolation, both were applied together per the brief's own "and/or"
  framing.
- **The management summary now states both comparisons in one sentence**
  ("...unfavorable to budget but $YK favorable to the latest forecast,
  driven by..."), but the **driver breakdown stays tied to the budget
  comparison** — the waterfall and driver bullets only ever decompose the
  budget variance; restating two independent driver breakdowns (budget
  AND forecast) in one sentence would be far harder to read and wasn't
  what the requested sentence style implied.
- **Summary subtitle changed from "USD $000s" to "USD (rounded to nearest
  $K)"** on both Summary and Waterfall sheets — removes the redundancy
  with per-value "$109K" labels while keeping the per-value $K suffix
  exactly as it was (the brief was explicit that only the subtitle wording
  was redundant, not the value formatting itself). Variance Detail's "full
  USD" note is unchanged — it was never part of the redundancy complaint.
- **The 3-line reconciliation block supplements, not replaces, the
  one-line "Bridge Reconciliation: $0 (Reconciled: Yes)" indicator** — the
  brief said "replace or supplement," and keeping both serves two
  different readers: the one-line version for an at-a-glance scan, the
  3-line "Reconciliation Detail" block (Sum / Variance / Difference) for
  someone who wants to verify the arithmetic by hand. The Difference row
  uses full 2-decimal precision (`$0.00`) while Sum/Variance use the
  sheet's $K convention — the whole point of that row is proving
  exactness, which $K rounding would visually obscure.
- **Variance Detail's note was rewritten, not its headers** — the brief
  allowed "note and/or headers"; adding header-level clarification
  (e.g. renaming "$ Var vs Budget") risked exceeding "no unnecessary
  columns or clutter," while the note is free-form prose that could
  directly spell out the Green/Red-vs-raw-sign distinction without adding
  any new visual elements.

## KPI Dashboard V4 — duplicate request, verified not rebuilt

- A later request asked for the same 15 KPI-dashboard changes already
  implemented in the "KPI Dashboard V4 content/polish pass" earlier in
  this project's history (Jan-Dec labels, $K values, renamed KPI, F/U
  notation, pts variance, analyst risk/action text, December end-labels,
  alignment, KPI Detail tab, etc.). Audited the current code line-by-line
  against all 15 items before touching anything — all were already
  present — and regenerated rather than rebuilding, per "do not rebuild
  from scratch."
- **Found one real, previously-missed inconsistency during this
  verification pass**: `kpi._format_value()` formatted currency as full
  dollars (`$775,350`), so the Risk & Action prose sentence showed a
  different unit than the card directly above it (`$775K`). Fixed by
  having `_format_value()` call `variance.format_k()` instead of
  formatting independently — one $K convention, not two slightly
  different ones.

## Variance Analysis — two final text/formatting polish edits

- **Management summary split into two sentences** so the driver clause is
  explicitly labeled "The budget variance was driven by..." rather than a
  single run-on sentence where it was ambiguous whether the drivers
  applied to the budget or forecast comparison (both are now stated as
  separate headline figures first).
- **Variance Detail's `A1` note replaced verbatim** with the shorter
  requested text, with row height computed via the existing
  `_wrapped_row_height()` helper (254 chars / 154 character-width-units
  of the 11 merged columns = exactly 2 lines) rather than hand-picking a
  row height — same approach already used for Close Calendar/Controls Log
  rows, applied here for consistency rather than introducing a second
  "guess the height" pattern.
- Both changes are text-only; no calculation, materiality, N/M, or
  waterfall-reconciliation logic was touched. Verified directly (not just
  via existing tests): source Actual/Budget/Forecast values unchanged,
  waterfall reconciles exactly for all 12 months, Jun/Jul COGS still
  flagged material, Feb/Jun/Jul Operating Income % still N/M.

## Variance Analysis — company-name and freeze-pane regression hardening

- **Audited before touching anything**: `Summary!A1` already displayed
  "Beacon Outdoor Goods" and `Variance Detail.freeze_panes` was already
  exactly `"C4"` in the current output — neither was visibly broken. The
  real issue was implementation fragility, not a visible defect: A1 was a
  SEPARATE hardcoded string literal (not derived from the module's single
  `COMPANY_NAME` constant used everywhere else), and `freeze_panes` was
  set via a computed `ws.cell(row=header_row+1, column=3)` reference
  positioned before later layout calls, rather than as an explicit
  literal after all sheet setup.
- **Added `COMPANY_SHORT_NAME = COMPANY_NAME.split(" (")[0]`**, derived
  once, used at `Summary!A1`. A future company config changes
  `COMPANY_NAME` in one place; every title (long form elsewhere, short
  form here) updates automatically — no second literal to remember to edit.
- **`freeze_panes = "C4"` moved to the last line of
  `_build_variance_detail_sheet()`**, after `auto_filter`, column widths,
  and print setup — genuinely "after all sheet setup is complete," not
  just before the function returns. Guarded with
  `assert header_row == 3` immediately above it: `header_row` is
  structurally fixed (note row 1 + group-header row 2 + this header row
  3 — never dependent on month count or data), so the assert is a
  tripwire against someone restructuring the sheet's top rows later
  without updating the freeze target, not a check expected to ever fire.
- **Regression tests build a FRESH workbook in an isolated temp dir**
  (not just inspecting the committed `output/variance_analysis.xlsx`) so
  they fail if the bug is reintroduced by anyone's future edit, not only
  if the checked-in output file happens to go stale.

## Close Checklist — dependency-consistent calendar, Open Tasks, ACC-03 bps

- **Added `task_id`/`depends_on` to every CLOSE_CALENDAR entry** alongside
  the existing free-text `dependency` description. The free text stays
  (it's what a reader actually sees in the "Dependency" column); the
  structured IDs are what `_resolve_dependency_statuses()` actually
  checks — free text can't be validated programmatically, so the
  dependency rule needed a parallel structured representation, not a
  parser for the prose.
- **Chose "cascade to Exception" over "approved workaround"** for the
  real scenario data (the brief offered both as valid). Accruals were
  authored as genuinely posted (not half-done), so "In Progress" would
  misrepresent the work; but the posting still rests on an unreconciled
  bank account, which is a real audit concern — "Exception" (work done,
  outcome not yet confirmable) is the more financially honest status than
  silently approving a workaround around an unreconciled account.
  `approved_workaround` is still a real, supported field in the data
  model and resolution logic for scenarios where that IS the right call.
- **The cascade is a single forward pass, not a fixed-point loop** —
  correct specifically because every task's `depends_on` only ever points
  to an earlier-authored task (the calendar is authored in schedule
  order). If a future scenario ever needed forward or circular
  references, this would need revisiting; documented here so it isn't
  rediscovered as a mystery bug.
- **`current_close_day()` defines "as of" as the latest day with ANY
  task activity** (anything not "Not Started"), not the latest day with
  a COMPLETE task — a day where work is merely in progress still counts
  as "where the close currently is." Given the real scenario, this
  resolves to Day 4 (T7 is In Progress) even though no Day 4 task is
  finished yet.
- **ACC-03 evaluates the CURRENT reporting month** (`max(pnl["month"])`),
  not a fixed month and not all 12 months like several of the other
  controls — a monthly threshold control is naturally scoped to the
  period being closed, consistent with how `__main__.py` already derives
  "current period" the same way.
- **The computed bps detail is folded into ACC-03's Evidence Retained
  cell specifically** (`_EVIDENCE_INCLUDES_DETAIL`), not added as a new
  column across all 12 controls — the brief scoped this to ACC-03, and a
  new column would touch every row's layout. The existing dynamic
  `_wrapped_row_height()` mechanism (built in an earlier round) already
  handles the much longer resulting text (row height auto-scales to
  148pt for this one row) — this is exactly the kind of case that
  mechanism exists for.
- **Found and fixed a second real gap during this pass, not explicitly
  asked for**: the `detail` field computed by every evaluator was never
  actually rendered anywhere in the workbook for ANY control — a reviewer
  had no way to see the quantitative evidence behind any evaluated
  control's Pass/Exception call, not just ACC-03's. Fixed narrowly for
  ACC-03 (what was asked); the same latent gap exists for the other 7
  evaluated controls and is not fixed here, since that's a broader change
  than this round's scope.

## Close Checklist — Blocked status, Open Tasks redefinition, freeze panes

- **"Open Tasks" redefinition is an explicit override of the prior
  round's deliberate design, not a bug fix** — the previous round
  intentionally excluded Exception from "Open" to keep a narrow
  risk-signal metric; this round's brief explicitly redefines "Open" as
  "everything not Complete" (total − complete = 8), which is a different,
  equally valid convention. Implemented exactly as specified rather than
  arguing for the earlier definition.
- **"Blocked" is a new, distinct status from "Exception"**: Exception =
  the task's OWN work has an unresolved issue (the root cause, e.g. Bank
  Reconciliation). Blocked = the task's own work is fine but it rests on
  an unresolved prerequisite (the knock-on effect). Both share the same
  red fill (text label carries the distinction, not a second color — kept
  the restrained palette unchanged).
- **Extended the cascade to Day 3's "Prepare balance sheet account
  reconciliations" (T6), not just the 3 tasks explicitly named in the
  brief.** T6 depends on the same Trial Balance task (T5) as "Run
  variance analysis" (T7), was also authored "In Progress," and sits
  under the exact same rule the brief asked for generally ("Use Blocked
  for a task that cannot be completed because an unresolved required
  dependency is in Exception or Blocked"). Applying the rule to T7 but
  not T6 would have reintroduced the same kind of inconsistency this
  whole effort exists to eliminate. Flagging this explicitly since the
  brief's own enumeration didn't name T6 — happy to revert it to "In
  Progress" if that was intentional, but leaving it inconsistent with T7
  seemed like the wrong default.
- **The Blocked rule only fires for tasks authored Complete or In
  Progress** — a "Not Started" task stays Not Started even if its
  dependency is Blocked (per the brief's explicit instruction), since
  "blocked" presumes an attempt was made; a task that hasn't started yet
  has nothing to be blocked by definition.
- **Both freeze-pane values ("A11" Close Calendar, "A6" Controls Log)
  already computed correctly** before this round — the fix was hardening
  them to explicit literals with defensive asserts (mirroring the
  Variance Detail "C4" pattern from an earlier round), moved to the last
  line of each sheet-build function, rather than a functional bug fix.
- **ACC-03's two bps clauses are built from one shared `_bps_clause()`
  helper**, not two near-duplicate f-strings — handles the general case
  (either, both, or neither comparison could trigger) rather than being
  hardcoded to "Budget triggers, Forecast doesn't," which only happens to
  be true for the current December data.

- **KPI Dashboard card status label is a POSITIONAL description
  ("Above Target" / "Under Target" / "On Target"), not a favorability
  judgment.** `_card_status_label()` compares `value` vs. `target` directly
  and ignores `direction` entirely — for a lower-is-better KPI (e.g. Total
  Cost per Unit), "Above Target" is unfavorable, while for a higher-is-better
  KPI it's favorable. The card's existing RAG-driven fill/font color (sourced
  from `RAG_FILL_FONT`/`font_hex`, unchanged) is what tells the reader
  whether that position is good or bad — the text states a plain fact, the
  color states the judgment. "On Target" triggers within a 0.5%-relative
  tolerance band of the target (chosen so near-exact matches don't show a
  meaningless "Above Target" over a rounding-level difference); this
  tolerance is independent of (and not reused from) `rag_status()`'s own
  5% RAG tolerance band, since the two serve different purposes (position
  wording vs. stoplight severity) and conflating them could make a card
  read "On Target" while still showing Amber/Red, or vice versa.
- **KPI Dashboard card trend text uses an explicit `\n`** between "Status:
  ..." and "MoM: ..." (not Excel's automatic word-wrap) so the two-line
  break always lands at that exact point — never mid-word — regardless of
  card width, satisfying "no clipping or awkward wrapping" by construction
  rather than by tuning font size against a pixel estimate. Row 9's height
  was bumped from the default to 28pt to fit two lines of 9pt bold text;
  this is a per-row height tweak inside the pre-existing 5-row card
  structure, not a change to overall dashboard layout (grid positions,
  chart anchors, and sheet dimensions are all untouched).
- **Scope: only the big dashboard cards' trend_row text changed** (the
  request said "KPI-card labels" specifically). The compact "KPI Detail"
  tab's "Trend (MoM)"/"RAG" columns — which already have column headers for
  context, unlike the bare card line — still use the original abbreviated
  `_trend_display_text()` (e.g. "+8.3% F" / "U"), untouched, per "do not
  make unrelated changes."
- **Management Insights labels were clipping to "Top"/"Top"/"Ris"** because
  the label was written into column A alone (width 3, ~26px — the sheet's
  "slim left margin" column) while the narrative cell immediately to its
  right (column B) is non-empty on those rows; Excel only lets text overflow
  into an EMPTY neighbor, so the label was hard-truncated at the column
  boundary. Fixed by merging the label across A:D (~230px, comfortably over
  the ~168px "Top Unfavorable Driver:" needs at 11pt bold) and starting the
  narrative one column later, at E instead of B. This changes only these 3
  rows' internal column split, not the sheet's actual column widths, chart
  grid, or any anchor position — "dashboard layout" in the grid/chart sense
  is unchanged.
- **KPI Detail RAG column text now reuses `_card_status_label(value,
  target)`** (the same positional helper the Dashboard cards use) instead
  of a RAG->letter lookup. This was a deliberate choice, not the simplest
  possible one: a naive RAG->text map (e.g. "Green"->"Above Target") would
  be semantically backwards for a lower-is-better KPI, where Green means
  value <= target (i.e., "Under"/"On Target", not "Above"). Computing the
  position directly from value vs. target is correct for every KPI
  regardless of direction, and keeps this column consistent with the
  Dashboard cards' own wording. Fill/font color (green/red) is still driven
  by the existing `rag`/`RAG_FILL_FONT` — "underlying status logic" and
  conditional-formatting intent are both unchanged, only the cell's text
  changed. Column F (RAG) was widened 8->16 to fit "Above Target"/"Under
  Target" without clipping. `RAG_LABEL` (the now-fully-unused F/W/U lookup)
  was removed — confirmed via repo-wide grep that nothing else referenced
  it.

## Tooling

- **`unittest` (stdlib) instead of `pytest`** for `tests/test_variance.py`,
  to keep `requirements.txt` at exactly the three libraries the spec names
  (pandas, openpyxl, matplotlib) with zero test-framework dependency.
- **Project-local `.venv`** created for dependency isolation; gitignored,
  not part of the deliverable.
