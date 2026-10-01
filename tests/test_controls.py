"""
Targeted tests for the Close Checklist generator (close_pack/controls.py
and the close-workbook builders in close_pack/excel_export.py):
    1. A task already underway (Complete or In Progress) can never come
       out of close_calendar() with that status while a `depends_on`
       prerequisite is Exception/Blocked — it becomes Blocked — unless it
       carries an approved_workaround. A Not-Started task stays Not
       Started regardless (nothing to block yet). Tested both generically
       (toy task lists) and against the real CLOSE_CALENDAR scenario data.
    2. current_close_day() is computed from calendar state, never a fixed
       literal.
    3. ACC-03's 200-bps-vs-Budget-or-Forecast threshold evaluates
       correctly at both sides of the boundary, for the "exceeds Forecast
       but not Budget" OR case, and states which comparison actually
       triggered the exception vs. which was merely favorable.
    4. close_calendar_summary()['tasks_open'] equals every task not
       Complete (Exception/Blocked/In Progress/Not Started all count).
    5. The Close Calendar and Controls Log freeze panes are exactly
       "A11" and "A6" respectively.

Run with: python -m unittest discover -s tests -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "data"))

from close_pack import controls, excel_export, kpi, variance  # noqa: E402


def _toy_task(task_id, day, status, depends_on=(), approved_workaround=""):
    return {
        "task_id": task_id, "day": day, "task": f"Task {task_id}", "owner": "X", "reviewer": "Y",
        "dependency": "n/a", "depends_on": list(depends_on), "evidence_ref": "",
        "status": status, "exception_notes": "", "approved_workaround": approved_workaround,
    }


class TestDependencyResolution(unittest.TestCase):
    def test_complete_task_is_blocked_by_an_open_exception_dependency(self):
        tasks = [_toy_task("A", 1, "Exception"), _toy_task("B", 1, "Complete", depends_on=["A"])]
        by_id = {t["task_id"]: t for t in controls._resolve_dependency_statuses(tasks)}
        self.assertEqual(by_id["A"]["status"], "Exception", "the root-cause task keeps its own status")
        self.assertEqual(by_id["B"]["status"], "Blocked",
                          "B depends on an open Exception and was authored Complete — must become Blocked")
        self.assertIn("A", by_id["B"]["exception_notes"])

    def test_in_progress_task_is_also_blocked(self):
        """Blocked applies to In Progress, not just Complete — a task
        can't legitimately be 'in progress' on work that rests on an
        unresolved prerequisite either."""
        tasks = [_toy_task("A", 1, "Exception"), _toy_task("B", 1, "In Progress", depends_on=["A"])]
        by_id = {t["task_id"]: t for t in controls._resolve_dependency_statuses(tasks)}
        self.assertEqual(by_id["B"]["status"], "Blocked")

    def test_not_started_task_stays_not_started_even_if_dependency_is_blocked(self):
        """A task simply scheduled for later is not itself 'blocked' —
        it hasn't been attempted, so there's nothing to block."""
        tasks = [_toy_task("A", 1, "Exception"), _toy_task("B", 1, "Not Started", depends_on=["A"])]
        by_id = {t["task_id"]: t for t in controls._resolve_dependency_statuses(tasks)}
        self.assertEqual(by_id["B"]["status"], "Not Started")

    def test_downgrade_cascades_through_a_chain(self):
        tasks = [
            _toy_task("A", 1, "Exception"),
            _toy_task("B", 1, "Complete", depends_on=["A"]),
            _toy_task("C", 2, "Complete", depends_on=["B"]),
        ]
        by_id = {t["task_id"]: t for t in controls._resolve_dependency_statuses(tasks)}
        self.assertEqual(by_id["B"]["status"], "Blocked")
        self.assertEqual(by_id["C"]["status"], "Blocked",
                          "C transitively depends on A's open exception via B and must cascade too")

    def test_approved_workaround_prevents_the_downgrade(self):
        tasks = [_toy_task("A", 1, "Exception"),
                 _toy_task("B", 1, "Complete", depends_on=["A"],
                           approved_workaround="Controller-approved workaround — Memo CAP-001.")]
        by_id = {t["task_id"]: t for t in controls._resolve_dependency_statuses(tasks)}
        self.assertEqual(by_id["B"]["status"], "Complete",
                          "an approved_workaround must let the dependent task remain Complete")

    def test_no_contradiction_in_the_real_close_calendar(self):
        """General invariant over the actual scenario data: no task is
        Complete or In Progress while any of its dependencies is an open
        Exception/Blocked, unless it has an approved_workaround."""
        df = controls.close_calendar()
        by_id = df.set_index("task_id").to_dict("index")
        for task_id, task in by_id.items():
            if task["status"] not in ("Complete", "In Progress"):
                continue
            for dep_id in task["depends_on"]:
                self.assertFalse(
                    by_id[dep_id]["status"] in ("Exception", "Blocked") and not task["approved_workaround"],
                    f"{task_id} ({task['task']}) is {task['status']} but depends on {dep_id} "
                    f"({by_id[dep_id]['status']}), with no approved workaround",
                )

    def test_real_scenario_matches_the_specified_statuses(self):
        df = controls.close_calendar().set_index("task_id")
        self.assertEqual(df.loc["T2", "status"], "Exception", "Bank reconciliation remains Exception")
        self.assertEqual(df.loc["T3", "status"], "Blocked", "Post accruals becomes Blocked")
        self.assertEqual(df.loc["T5", "status"], "Blocked", "Run the trial balance becomes Blocked")
        self.assertEqual(df.loc["T7", "status"], "Blocked", "Run variance analysis becomes Blocked")


class TestCloseStatusDay(unittest.TestCase):
    def test_all_not_started_returns_zero(self):
        import pandas as pd
        df = pd.DataFrame([{"day": 1, "status": "Not Started"}, {"day": 2, "status": "Not Started"}])
        self.assertEqual(controls.current_close_day(df), 0)

    def test_returns_the_latest_day_with_any_activity(self):
        import pandas as pd
        df = pd.DataFrame([
            {"day": 1, "status": "Complete"},
            {"day": 2, "status": "In Progress"},
            {"day": 3, "status": "Not Started"},
        ])
        self.assertEqual(controls.current_close_day(df), 2)

    def test_real_calendar_day_is_dynamically_computed_not_hardcoded(self):
        day = controls.current_close_day()
        self.assertGreaterEqual(day, 1)
        self.assertLessEqual(day, 5)
        self.assertEqual(day, 4)


class TestACC03BpsThreshold(unittest.TestCase):
    def _build_db(self, tmp_path, actual_pct, budget_pct, forecast_pct, revenue=500_000.0):
        """Override only the LAST month's Revenue/COGS (all 3 scenarios)
        in an otherwise-realistic generated dataset, so load_pnl's
        Gross-Profit/Operating-Income subtotal math still has every line
        item it needs."""
        import generate_data
        data = generate_data.generate()
        for scenario, pct in (("actual", actual_pct), ("budget", budget_pct), ("forecast", forecast_pct)):
            data[scenario]["Revenue"][-1] = revenue
            data[scenario]["COGS"][-1] = revenue * pct
        db_path = tmp_path / "close_pack.db"
        generate_data._write_sqlite(data, db_path)
        return db_path

    def test_within_threshold_is_effective(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = self._build_db(Path(tmp), actual_pct=0.5699, budget_pct=0.55, forecast_pct=0.5699)
            status, detail = controls._eval_cogs_ratio_vs_plan_bps(str(db_path))
            self.assertEqual(status, "Effective", detail)

    def test_exceeds_budget_by_more_than_200bps_is_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = self._build_db(Path(tmp), actual_pct=0.5701, budget_pct=0.55, forecast_pct=0.5701)
            status, detail = controls._eval_cogs_ratio_vs_plan_bps(str(db_path))
            self.assertEqual(status, "Exception", detail)
            self.assertIn("Budget", detail)
            self.assertIn("triggered the exception", detail)

    def test_exceeds_forecast_but_not_budget_is_still_exception(self):
        """The rule is an OR: Budget OR Forecast — must flag even when
        only the forecast comparison breaches the threshold."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = self._build_db(Path(tmp), actual_pct=0.57, budget_pct=0.57, forecast_pct=0.5499)
            status, detail = controls._eval_cogs_ratio_vs_plan_bps(str(db_path))
            self.assertEqual(status, "Exception", detail)

    def test_real_dataset_december_states_which_comparison_triggered(self):
        """Regression check against the real synthetic data: December
        exceeds Budget by ~241 bps (the trigger) and is ~518 bps FAVORABLE
        vs. Forecast (explicitly not the trigger) — both facts must be
        stated, with the favorable one clearly not blamed."""
        status, detail = controls._eval_cogs_ratio_vs_plan_bps(str(REPO_ROOT / "data" / "close_pack.db"))
        self.assertEqual(status, "Exception")
        self.assertIn("2025-12", detail)
        self.assertIn("exceeded Budget by 241 bps", detail)
        self.assertIn("triggered the exception", detail)
        self.assertIn("518 bps below Forecast", detail)
        self.assertIn("favorable and not the trigger", detail)


class TestOpenTasksCountMatchesCalendar(unittest.TestCase):
    def test_open_tasks_equals_total_minus_complete(self):
        df = controls.close_calendar()
        expected = len(df) - int((df["status"] == "Complete").sum())
        summary = controls.close_calendar_summary()
        self.assertEqual(summary["tasks_open"], expected)

    def test_real_scenario_open_tasks_is_eight(self):
        self.assertEqual(controls.close_calendar_summary()["tasks_open"], 8)

    def test_complete_plus_open_equals_total(self):
        summary = controls.close_calendar_summary()
        self.assertEqual(summary["tasks_complete"] + summary["tasks_open"], summary["tasks_total"])


class TestCloseWorkbookFreezePanes(unittest.TestCase):
    """Builds a FRESH close_checklist.xlsx in an isolated temp dir and
    confirms the exact freeze-pane settings — not just inspecting the
    committed output/close_checklist.xlsx — so this fails if either value
    regresses by anyone's future edit."""

    @classmethod
    def setUpClass(cls):
        import generate_data
        import openpyxl

        cls.tmp_dir = tempfile.TemporaryDirectory()
        tmp_path = Path(cls.tmp_dir.name)
        db_path = tmp_path / "close_pack.db"
        data = generate_data.generate()
        generate_data._write_sqlite(data, db_path)

        calendar_df = controls.close_calendar()
        controls_df = controls.evaluate_controls(str(db_path))
        workbook_path = tmp_path / "close_checklist.xlsx"
        excel_export.build_close_workbook(calendar_df, controls_df, workbook_path)
        cls.wb = openpyxl.load_workbook(workbook_path)

    @classmethod
    def tearDownClass(cls):
        cls.tmp_dir.cleanup()

    def test_close_calendar_freeze_panes_is_a11(self):
        self.assertEqual(self.wb["Close Calendar"].freeze_panes, "A11")

    def test_controls_log_freeze_panes_is_a6(self):
        self.assertEqual(self.wb["Controls Log"].freeze_panes, "A6")


if __name__ == "__main__":
    unittest.main()
