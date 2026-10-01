"""
Close calendar + controls log.

The controls log is informed by document-validation practice from annuity
operations — completeness, accuracy, and authorization checks — adapted
here to a month-end close, plus evidence retention and exception
management for each control. This is a demonstration of internal-controls
awareness applied to a hypothetical company; it does not claim SOX
compliance, audit-readiness, or enterprise-grade coverage.

Where a control can be evaluated against the generated dataset, it is
(`evaluate_controls` runs real checks that can genuinely come back
"Exception"). Where it's a policy or segregation-of-duties control with no
data trail in this model (e.g. "budget was signed off by the Finance
Director"), it's marked as a manual attestation with a synthetic evidence
reference — clearly labeled, not claimed as data-verified.

Like variance.py and kpi.py, this module never touches Excel.
"""

from dataclasses import dataclass
from typing import Callable, Optional

import pandas as pd

from close_pack import variance

# --------------------------------------------------------------------------
# Close calendar
# --------------------------------------------------------------------------
# Statuses reflect a realistic snapshot partway through a close (not a blank
# template): Day 1-2 tasks are mostly done, Day 3 is wrapping up, Day 4-5
# are still ahead. `status` below is the AUTHORED/claimed status; it is run
# through `_resolve_dependency_statuses()` before being returned by
# `close_calendar()` — a task can never come out of that function showing
# Complete while a `depends_on` prerequisite is still an open Exception,
# regardless of what status was authored here. `dependency` is the
# human-readable description shown in the workbook; `depends_on` is the
# same relationship as structured task_ids, which is what the dependency
# rule actually checks (free text can't be validated programmatically).

CLOSE_CALENDAR = [
    {"task_id": "T1", "day": 1, "task": "Cut off subledgers (AP/AR/Inventory) and lock the period",
     "owner": "AP/AR Clerk", "reviewer": "Staff Accountant",
     "dependency": "None — first task of the close", "depends_on": [],
     "evidence_ref": "Subledger cutoff report — SUBLEDGER-2025-12",
     "status": "Complete", "exception_notes": "", "approved_workaround": ""},
    {"task_id": "T2", "day": 1, "task": "Reconcile all bank accounts to the GL",
     "owner": "Staff Accountant", "reviewer": "Controller",
     "dependency": "Subledger cutoff", "depends_on": ["T1"],
     "evidence_ref": "Bank reconciliation workpaper — BANKREC-2025-12",
     "status": "Exception",
     "exception_notes": "Unreconciled variance of $1,240 pending research; escalated to Controller for resolution by Day 2.",
     "approved_workaround": ""},
    {"task_id": "T3", "day": 2, "task": "Post accruals and reclassifying journal entries",
     "owner": "Senior Accountant", "reviewer": "Controller",
     "dependency": "Bank reconciliations", "depends_on": ["T2"],
     "evidence_ref": "JE batch — ACCR-2025-12",
     # Authored as Complete (entries were posted) — but T2 is still an open
     # Exception, so _resolve_dependency_statuses() downgrades this below.
     "status": "Complete", "exception_notes": "", "approved_workaround": ""},
    {"task_id": "T4", "day": 2, "task": "Calculate and post the payroll accrual",
     "owner": "Payroll/HR", "reviewer": "Controller",
     "dependency": "None — runs in parallel with accruals", "depends_on": [],
     "evidence_ref": "Payroll accrual calculation — PR-2025-12",
     "status": "Complete", "exception_notes": "", "approved_workaround": ""},
    {"task_id": "T5", "day": 3, "task": "Run the trial balance and review for out-of-pattern balances",
     "owner": "Controller", "reviewer": "FP&A Manager",
     "dependency": "Accruals and payroll posted", "depends_on": ["T3", "T4"],
     "evidence_ref": "Trial balance export — TB-2025-12",
     "status": "Complete", "exception_notes": "", "approved_workaround": ""},
    {"task_id": "T6", "day": 3, "task": "Prepare balance sheet account reconciliations",
     "owner": "Staff Accountant", "reviewer": "Controller",
     "dependency": "Trial balance run", "depends_on": ["T5"],
     "evidence_ref": "Balance sheet reconciliation binder — BSREC-2025-12",
     "status": "In Progress", "exception_notes": "", "approved_workaround": ""},
    {"task_id": "T7", "day": 4, "task": "Run variance analysis: actual vs. budget vs. forecast",
     "owner": "FP&A Analyst", "reviewer": "FP&A Manager",
     "dependency": "Trial balance finalized", "depends_on": ["T5"],
     "evidence_ref": "Variance Analysis Workbook — variance_analysis.xlsx",
     "status": "In Progress", "exception_notes": "", "approved_workaround": ""},
    {"task_id": "T8", "day": 4, "task": "Execute controls testing and collect evidence for the controls log",
     "owner": "Internal Controls", "reviewer": "Controller",
     "dependency": "Subledgers and GL closed", "depends_on": ["T1", "T5"],
     "evidence_ref": "Controls Log — close_checklist.xlsx (Controls Log tab)",
     "status": "Not Started", "exception_notes": "", "approved_workaround": ""},
    {"task_id": "T9", "day": 5, "task": "Finalize financial statements and management reporting package",
     "owner": "Controller", "reviewer": "FP&A Manager",
     "dependency": "Variance analysis and controls testing complete", "depends_on": ["T7", "T8"],
     "evidence_ref": "Management Reporting Package — MRP-2025-12",
     "status": "Not Started", "exception_notes": "", "approved_workaround": ""},
    {"task_id": "T10", "day": 5, "task": "Distribute close package to leadership",
     "owner": "FP&A Manager", "reviewer": "Controller",
     "dependency": "Financials finalized", "depends_on": ["T9"],
     "evidence_ref": "Distribution confirmation — close package email log",
     "status": "Not Started", "exception_notes": "", "approved_workaround": ""},
]


#: A task whose OWN work has an unresolved issue is "Exception" — the
#: root cause. A task that is itself fine but rests on an unresolved
#: prerequisite is "Blocked" — the knock-on effect. Keeping these
#: distinct lets a reader immediately tell "this is where the problem is"
#: (Exception) apart from "this is waiting on that problem" (Blocked).
_UNRESOLVED_STATUSES = ("Exception", "Blocked")


def _resolve_dependency_statuses(tasks: list) -> list:
    """Enforce, programmatically, that a task already underway (Complete
    or In Progress) can never be returned with that status while a
    `depends_on` prerequisite is still Exception/Blocked — it becomes
    Blocked instead — unless this task carries a non-empty
    `approved_workaround` (a Controller-approved, documented rationale for
    proceeding anyway). A task that hasn't been started yet stays Not
    Started regardless of its dependencies' state: being blocked is only
    meaningful for a task someone has actually attempted.

    Tasks are authored in dependency order (every `depends_on` points to
    an earlier entry), so a single forward pass naturally cascades: if a
    task gets downgraded here, anything depending on IT is checked against
    its new (downgraded) status, not its originally authored one.

    This is the general mechanism the brief asked for — it isn't specific
    to bank-rec/accruals; it fires for any future scenario with the same
    shape, which is why it's a function over the whole list rather than a
    one-off edit to a single task's status string."""
    by_id = {}
    resolved = []
    for task in tasks:
        task = dict(task)
        if task["status"] in ("Complete", "In Progress"):
            blockers = [
                by_id[dep_id] for dep_id in task.get("depends_on", [])
                if by_id[dep_id]["status"] in _UNRESOLVED_STATUSES
            ]
            if blockers and not task.get("approved_workaround"):
                blocker = blockers[0]
                task["status"] = "Blocked"
                task["exception_notes"] = (
                    f"Blocked: dependent on unresolved prerequisite "
                    f"\"{blocker['task']}\" ({blocker['task_id']}, currently {blocker['status']}); "
                    f"cannot proceed or confirm completion until that is resolved."
                )
        by_id[task["task_id"]] = task
        resolved.append(task)
    return resolved


def close_calendar() -> pd.DataFrame:
    """Return the Day 1-5 close calendar as a DataFrame, in schedule order,
    after dependency-status resolution (see `_resolve_dependency_statuses`)."""
    return pd.DataFrame(_resolve_dependency_statuses(CLOSE_CALENDAR))


def current_close_day(calendar_df: Optional[pd.DataFrame] = None) -> int:
    """The close's 'as of' day: the latest day with any task activity
    (status other than 'Not Started'). Computed from the calendar's own
    state — never hard-coded — so 'Close status as of: Day X' always
    reflects the actual scenario, whatever day it currently represents."""
    df = calendar_df if calendar_df is not None else close_calendar()
    active = df[df["status"] != "Not Started"]
    if active.empty:
        return 0
    return int(active["day"].max())


def close_calendar_summary() -> dict:
    """Tasks complete / total; Open Tasks = every task not yet Complete
    (In Progress, Blocked, Exception, and Not Started alike — anything
    still outstanding); Exception/Blocked counts kept separately too, for
    anyone who wants the at-risk subset specifically rather than the full
    outstanding count."""
    df = close_calendar()
    total = len(df)
    complete = int((df["status"] == "Complete").sum())
    exception = int((df["status"] == "Exception").sum())
    blocked = int((df["status"] == "Blocked").sum())
    open_tasks = total - complete
    return {
        "tasks_complete": complete,
        "tasks_total": total,
        "tasks_open": open_tasks,
        "exception_tasks": exception,
        "blocked_tasks": blocked,
        "current_close_day": current_close_day(df),
    }


# --------------------------------------------------------------------------
# Controls log
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class ControlSpec:
    control_id: str
    category: str       # "Completeness" | "Accuracy" | "Authorization"
    process_area: str
    risk: str
    control_activity: str
    owner: str
    reviewer: str
    frequency: str
    evidence_ref: str
    evaluator: Optional[Callable[[str], tuple]] = None
    # evaluator(db_path) -> (status: "Effective"|"Exception", detail: str)
    # None => manual attestation, always "Effective"


def _eval_actuals_complete(db_path: str):
    pnl = variance.load_pnl(db_path)
    raw = pnl[~pnl["line_item"].isin(["Gross Profit", "Operating Income"])]
    actual_count = raw["month"].nunique() * raw["line_item"].nunique()
    ok = actual_count == 12 * 7
    return ("Effective" if ok else "Exception", f"{actual_count} of 84 expected (month x line_item) cells present.")


def _eval_scenario_complete(scenario: str):
    def _check(db_path: str):
        pnl = variance.load_pnl(db_path)
        raw = pnl[~pnl["line_item"].isin(["Gross Profit", "Operating Income"])]
        non_null = raw[scenario].notna().sum()
        ok = non_null == 84
        return ("Effective" if ok else "Exception", f"{non_null} of 84 expected {scenario} values populated.")
    return _check


def _eval_units_complete(db_path: str):
    import sqlite3
    conn = sqlite3.connect(db_path)
    try:
        count = conn.execute("SELECT COUNT(*) FROM units").fetchone()[0]
    finally:
        conn.close()
    ok = count == 12
    return ("Effective" if ok else "Exception", f"{count} of 12 expected monthly units_sold records present.")


def _eval_waterfall_reconciles(db_path: str):
    var_df = variance.compute_variance(variance.load_pnl(db_path))
    months = sorted(var_df["month"].unique())
    bad_months = []
    for month in months:
        recon = variance.waterfall_reconciliation(var_df, month)
        if abs(recon["difference"]) > 0.01:
            bad_months.append(month)
    ok = not bad_months
    detail = "Waterfall reconciles to OI variance for all 12 months (difference = $0.00)." if ok \
        else f"Reconciliation break in: {', '.join(bad_months)}."
    return ("Effective" if ok else "Exception", detail)


def _eval_unit_price_reasonable(db_path: str, low=38.0, high=47.0):
    import sqlite3
    pnl = variance.load_pnl(db_path)
    conn = sqlite3.connect(db_path)
    try:
        units = pd.read_sql("SELECT month, units_sold FROM units", conn)
    finally:
        conn.close()
    revenue = pnl[pnl["line_item"] == "Revenue"][["month", "actual"]]
    merged = revenue.merge(units, on="month")
    merged["implied_price"] = merged["actual"] / merged["units_sold"]
    out_of_range = merged[(merged["implied_price"] < low) | (merged["implied_price"] > high)]
    ok = out_of_range.empty
    detail = f"Implied unit price within ${low:.0f}-${high:.0f} for all 12 months." if ok \
        else f"Out of range in: {', '.join(out_of_range['month'])}."
    return ("Effective" if ok else "Exception", detail)


COGS_RATIO_THRESHOLD_BPS = 200.0  # Exception if actual COGS% of Revenue exceeds Budget or Forecast by more than this


def _bps_clause(comparison_label: str, bps: float, threshold_bps: float, triggered: bool) -> str:
    """One causally-explicit sentence for a single Budget-or-Forecast
    comparison — states the number, AND whether it was the reason for the
    exception, the way an auditor reading the evidence would want it
    separated rather than two deltas listed side by side with no verdict
    attached to either."""
    direction = "above" if bps >= 0 else "below"
    if triggered:
        return (
            f"Actual COGS exceeded {comparison_label} by {abs(bps):.0f} bps ({bps:+.0f} bps), "
            f"which triggered the exception (threshold: +{threshold_bps:.0f} bps)"
        )
    if bps < 0:
        return f"Actual was {abs(bps):.0f} bps below {comparison_label} ({bps:+.0f} bps), which is favorable and not the trigger"
    return f"Actual was {bps:.0f} bps above {comparison_label} ({bps:+.0f} bps), within the +{threshold_bps:.0f} bps threshold"


def _eval_cogs_ratio_vs_plan_bps(db_path: str, threshold_bps: float = COGS_RATIO_THRESHOLD_BPS):
    """Exception if Actual COGS as a % of Revenue exceeds EITHER Budget's
    or the latest Forecast's COGS % of Revenue by more than `threshold_bps`
    basis points, for the current reporting month (the most recent month
    in the dataset — never hard-coded to a specific period, so this control
    evaluates correctly for any future reporting month). The evidence text
    states each comparison's bps gap AND whether it was the one that
    actually triggered the exception — a favorable gap on one comparison
    must not be left ambiguous just because the other comparison failed."""
    pnl = variance.load_pnl(db_path)
    month = max(pnl["month"])
    month_df = pnl[pnl["month"] == month].set_index("line_item")

    def _cogs_pct(scenario: str) -> float:
        return month_df.loc["COGS", scenario] / month_df.loc["Revenue", scenario]

    actual_pct = _cogs_pct("actual")
    budget_pct = _cogs_pct("budget")
    forecast_pct = _cogs_pct("forecast")
    vs_budget_bps = (actual_pct - budget_pct) * 10_000
    vs_forecast_bps = (actual_pct - forecast_pct) * 10_000

    budget_triggered = vs_budget_bps > threshold_bps
    forecast_triggered = vs_forecast_bps > threshold_bps
    exceeds = budget_triggered or forecast_triggered

    detail = (
        f"{month}: Actual COGS was {actual_pct:.2%} of Revenue (Budget {budget_pct:.2%}, "
        f"Forecast {forecast_pct:.2%}). "
        f"{_bps_clause('Budget', vs_budget_bps, threshold_bps, budget_triggered)}. "
        f"{_bps_clause('Forecast', vs_forecast_bps, threshold_bps, forecast_triggered)}."
    )
    return ("Exception" if exceeds else "Effective", detail)


def _eval_forecast_revised(db_path: str):
    pnl = variance.load_pnl(db_path)
    post_q1 = pnl[pnl["month"] > "2025-03"]
    stale = post_q1[
        (post_q1["forecast"] == post_q1["budget"])
        & (~post_q1["line_item"].isin(["Gross Profit", "Operating Income"]))
    ]
    ok = stale.empty
    detail = "All post-Q1 forecasts were re-based off actual run-rate (no stale budget copy-forward)." if ok \
        else f"{len(stale)} line/month cells still equal the original budget after Q1."
    return ("Effective" if ok else "Exception", detail)


CONTROLS_LOG = [
    ControlSpec(
        "COMP-01", "Completeness", "Financial Close - P&L Reporting",
        "Incomplete P&L data could cause reported results to misstate actual financial performance.",
        "All P&L line items are present for all 12 months in actuals",
        "Staff Accountant", "Controller", "Monthly",
        "GL export row count — close_pack.db/actuals", _eval_actuals_complete,
    ),
    ControlSpec(
        "COMP-02", "Completeness", "Budgeting",
        "An incomplete budget load would produce false or missing variance results for any affected line.",
        "All P&L line items are present for all 12 months in budgets",
        "FP&A Analyst", "FP&A Manager", "Annual (set once, checked monthly)",
        "Budget load file — close_pack.db/budgets", _eval_scenario_complete("budget"),
    ),
    ControlSpec(
        "COMP-03", "Completeness", "Forecasting",
        "An incomplete forecast load would misstate forecast-accuracy reporting.",
        "All P&L line items are present for all 12 months in forecasts",
        "FP&A Analyst", "FP&A Manager", "Quarterly",
        "Forecast revision file — close_pack.db/forecasts", _eval_scenario_complete("forecast"),
    ),
    ControlSpec(
        "COMP-04", "Completeness", "Operations Reporting",
        "A missing units-sold record would break per-unit KPI reporting for that month.",
        "A units-sold record exists for every closed month",
        "Operations Analyst", "FP&A Analyst", "Monthly",
        "Shipment log — close_pack.db/units", _eval_units_complete,
    ),
    ControlSpec(
        "ACC-01", "Accuracy", "Variance Reporting",
        "A broken waterfall reconciliation would let a mis-stated variance narrative reach management undetected.",
        "Operating Income waterfall reconciles exactly to the total OI variance",
        "FP&A Analyst", "FP&A Manager", "Monthly",
        "variance.py waterfall_reconciliation() output", _eval_waterfall_reconciles,
    ),
    ControlSpec(
        "ACC-02", "Accuracy", "Revenue Assurance",
        "A mismatch between booked revenue and shipment volume could indicate a pricing or booking error.",
        "Implied unit price (Revenue / units sold) falls within expected range",
        "Controller", "FP&A Manager", "Monthly",
        "Revenue vs. shipment-log cross-check", _eval_unit_price_reasonable,
    ),
    ControlSpec(
        "ACC-03", "Accuracy", "Cost of Goods Sold",
        "An unexplained COGS ratio swing could indicate a supplier cost issue or margin erosion going unnoticed until year-end.",
        f"Exception if COGS as a % of Revenue exceeds Budget or the latest Forecast by more than "
        f"{COGS_RATIO_THRESHOLD_BPS:.0f} bps",
        "Controller", "FP&A Manager", "Monthly",
        "COGS trend analysis workpaper (Actual/Budget/Forecast COGS-%-of-Revenue, bps variance)",
        _eval_cogs_ratio_vs_plan_bps,
    ),
    ControlSpec(
        "ACC-04", "Accuracy", "Forecasting",
        "A forecast copy-forwarded from budget rather than re-based on actuals would overstate forecast accuracy and mislead planning.",
        "Forecast values are re-based (not copy-forwarded) after each quarterly revision",
        "FP&A Manager", "Controller", "Quarterly",
        "Forecast vintage comparison — forecasts vs. budgets table", _eval_forecast_revised,
    ),
    ControlSpec(
        "AUTH-01", "Authorization", "Budget Governance",
        "An unapproved budget could be used as the basis for variance reporting without management's agreement to the plan.",
        "Annual budget is signed off by the Finance Director before fiscal-year start",
        "Finance Director", "CFO", "Annual",
        "Approval record: CAP-2025-BUD-001 (FY25 budget package)",
    ),
    ControlSpec(
        "AUTH-02", "Authorization", "Journal Entry Authorization",
        "An unreviewed large journal entry could post an error or an unauthorized adjustment to the GL.",
        "Journal entries and reclasses over $25,000 require a second approver",
        "Controller", "CFO", "Per transaction",
        "JE approval workflow log (second-approver field populated)",
    ),
    ControlSpec(
        "AUTH-03", "Authorization", "Forecast Governance",
        "An unapproved forecast revision could reach leadership without FP&A management review.",
        "Quarterly forecast revisions are approved by the FP&A Manager before publication",
        "FP&A Manager", "CFO", "Quarterly",
        "Forecast sign-off record: CAP-2025-FCST-Q#",
    ),
    ControlSpec(
        "AUTH-04", "Authorization", "System Access / Segregation of Duties",
        "Unrestricted access to the close-the-books function could allow an unauthorized user to alter a closed period.",
        "Close-the-books system function is restricted to the Controller and Assistant Controller",
        "IT Security", "Controller", "Quarterly access review",
        "System access review: close-lock role membership",
    ),
]

_REMEDIATION_OVERRIDES = {
    "ACC-03": "Research root cause with Supply Chain/Procurement; document business justification for the "
              "period and evaluate whether standard cost assumptions need revision for the next forecast cycle.",
}


# Controls where the live computed result (not just pass/fail) needs to
# be visible to a reviewer directly on the Controls Log sheet — the
# Evidence Retained column is where it's folded in, since this workbook
# has no separate "evaluation result" column and adding one would touch
# every control's row, not just this one.
_EVIDENCE_INCLUDES_DETAIL = {"ACC-03"}


def evaluate_controls(db_path: str) -> pd.DataFrame:
    """Run every control in CONTROLS_LOG against the dataset at `db_path`
    (evaluator controls, which can genuinely come back "Exception") or
    record its manual attestation (evaluator=None), returning one row per
    control with category/process area/risk/activity/owner/reviewer/
    frequency/evidence/status/remediation."""
    rows = []
    for spec in CONTROLS_LOG:
        if spec.evaluator is not None:
            status, detail = spec.evaluator(db_path)
        else:
            status, detail = "Effective", "Manual attestation — no automated data trail in this model."

        if status == "Exception":
            remediation = _REMEDIATION_OVERRIDES.get(spec.control_id, f"Investigate and remediate: {detail}")
        else:
            remediation = "None required — control operating as designed."

        evidence_ref = spec.evidence_ref
        if spec.control_id in _EVIDENCE_INCLUDES_DETAIL:
            evidence_ref = f"{spec.evidence_ref}. Result: {detail}"

        rows.append({
            "control_id": spec.control_id,
            "category": spec.category,
            "process_area": spec.process_area,
            "risk": spec.risk,
            "control_activity": spec.control_activity,
            "owner": spec.owner,
            "reviewer": spec.reviewer,
            "frequency": spec.frequency,
            "evidence_ref": evidence_ref,
            "status": status,
            "detail": detail,
            "exception_remediation": remediation,
        })
    return pd.DataFrame(rows)


def controls_summary(controls_df: pd.DataFrame) -> dict:
    """Controls effective / with exceptions, for the top-of-sheet summary."""
    total = len(controls_df)
    effective = int((controls_df["status"] == "Effective").sum())
    exception = int((controls_df["status"] == "Exception").sum())
    return {"controls_total": total, "controls_effective": effective, "controls_exception": exception}
