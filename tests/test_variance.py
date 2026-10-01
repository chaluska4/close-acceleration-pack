"""
Unit tests for the variance engine (close_pack/variance.py).

Run with: python -m unittest discover -s tests -v
(No pytest dependency — keeps requirements.txt to pandas/openpyxl/matplotlib.)

Covers the three behaviors §4/§6 of the build spec call out explicitly:
    1. Waterfall components sum exactly to the total Operating Income variance.
    2. Threshold flagging is correct at the boundary (>= is inclusive) and
       respects the OR between the percent and dollar thresholds.
    3. The narrative's top-3 favorable/unfavorable picks are the true
       largest drivers, not just the first rows encountered.
It also regression-tests against the real synthetic dataset: the planted
mid-year COGS spike must actually trip the default threshold.
"""

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "data"))

import pandas as pd  # noqa: E402

from close_pack import variance  # noqa: E402


def _toy_pnl(month: str = "2099-01") -> pd.DataFrame:
    """A fully hand-computed 7-line P&L for one month, so waterfall and
    narrative assertions don't depend on the (randomized) synthetic data."""
    rows = [
        {"line_item": "Revenue", "actual": 100_000, "budget": 90_000, "forecast": 95_000},
        {"line_item": "COGS", "actual": 40_000, "budget": 45_000, "forecast": 42_000},
        {"line_item": "Salaries", "actual": 20_000, "budget": 20_000, "forecast": 20_000},
        {"line_item": "Marketing", "actual": 12_000, "budget": 8_000, "forecast": 9_000},
        {"line_item": "Facilities", "actual": 5_000, "budget": 5_000, "forecast": 5_000},
        {"line_item": "Professional Services", "actual": 3_000, "budget": 4_000, "forecast": 3_500},
        {"line_item": "Other", "actual": 1_000, "budget": 1_000, "forecast": 1_000},
    ]
    for row in rows:
        row["month"] = month
    return variance.add_subtotals(pd.DataFrame(rows))


class TestAddSubtotals(unittest.TestCase):
    def test_operating_income_matches_hand_calc(self):
        pnl = _toy_pnl()
        oi = pnl.set_index("line_item").loc["Operating Income"]
        # actual: 100,000 - 40,000 - (20,000+12,000+5,000+3,000+1,000) = 19,000
        # budget:  90,000 - 45,000 - (20,000+ 8,000+5,000+4,000+1,000) =  7,000
        self.assertAlmostEqual(oi["actual"], 19_000)
        self.assertAlmostEqual(oi["budget"], 7_000)


class TestWaterfall(unittest.TestCase):
    def test_components_sum_to_total_oi_variance(self):
        pnl = _toy_pnl()
        var_df = variance.compute_variance(pnl)
        components = variance.waterfall_components(var_df, "2099-01")

        month_df = var_df.set_index("line_item")
        expected_total = month_df.loc["Operating Income", "actual"] - month_df.loc["Operating Income", "budget"]
        actual_total = sum(contribution for _, contribution in components)

        self.assertAlmostEqual(actual_total, expected_total, places=2)
        self.assertAlmostEqual(expected_total, 12_000)  # hand-calculated above

    def test_waterfall_covers_every_bridge_line_once(self):
        pnl = _toy_pnl()
        var_df = variance.compute_variance(pnl)
        components = variance.waterfall_components(var_df, "2099-01")
        labels = [label for label, _ in components]
        self.assertEqual(labels, variance.BRIDGE_ORDER)

    def test_real_dataset_waterfall_sums_for_every_month(self):
        """Regression check against the actual synthetic generator output,
        not just the hand-built toy case."""
        import generate_data

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "close_pack.db"
            data = generate_data.generate()
            generate_data._write_sqlite(data, db_path)

            var_df = variance.compute_variance(variance.load_pnl(db_path))
            for month in generate_data.MONTHS:
                components = variance.waterfall_components(var_df, month)
                month_df = var_df[var_df["month"] == month].set_index("line_item")
                expected = month_df.loc["Operating Income", "actual"] - month_df.loc["Operating Income", "budget"]
                actual = sum(c for _, c in components)
                self.assertAlmostEqual(actual, expected, places=2, msg=f"waterfall mismatch in {month}")


class TestThresholdFlagging(unittest.TestCase):
    def test_boundary_behavior(self):
        rows = [
            # Exactly 5% variance -> percent threshold boundary, must flag (inclusive).
            {"month": "2099-02", "line_item": "Revenue", "actual": 105_000, "budget": 100_000, "forecast": 100_000},
            # Exactly $10k variance but only 3.33% -> dollar threshold boundary, must flag via OR.
            {"month": "2099-02", "line_item": "COGS", "actual": 310_000, "budget": 300_000, "forecast": 300_000},
            # $1,000 / 2% -> below both thresholds, must NOT flag.
            {"month": "2099-02", "line_item": "Salaries", "actual": 51_000, "budget": 50_000, "forecast": 50_000},
        ]
        df = pd.DataFrame(rows)
        var_df = variance.compute_variance(df, threshold_pct=0.05, threshold_abs=10_000.0)
        flags = var_df.set_index("line_item")["flag_vs_budget"]

        self.assertTrue(flags["Revenue"], "5% boundary should flag (>= is inclusive)")
        self.assertTrue(flags["COGS"], "$10k boundary should flag even though % is below threshold")
        self.assertFalse(flags["Salaries"], "below both thresholds should not flag")

    def test_real_dataset_flags_the_planted_cogs_spike(self):
        import generate_data

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "close_pack.db"
            data = generate_data.generate()
            generate_data._write_sqlite(data, db_path)

            var_df = variance.compute_variance(variance.load_pnl(db_path))
            cogs = var_df[(var_df["line_item"] == "COGS")].set_index("month")
            self.assertTrue(cogs.loc["2025-06", "flag_vs_budget"], "June COGS spike must trip the threshold")
            self.assertTrue(cogs.loc["2025-07", "flag_vs_budget"], "July COGS spike must trip the threshold")


class TestNarrative(unittest.TestCase):
    def test_top_drivers_picks_true_largest(self):
        pnl = _toy_pnl()
        var_df = variance.compute_variance(pnl)
        favorable, unfavorable = variance.top_drivers(var_df, "2099-01", n=3)

        # Hand-calculated contributions: Revenue +10,000, COGS +5,000,
        # Professional Services +1,000 (favorable); Marketing -4,000 (only unfavorable).
        self.assertEqual([label for label, _ in favorable], ["Revenue", "COGS", "Professional Services"])
        self.assertAlmostEqual(favorable[0][1], 10_000)
        self.assertEqual([label for label, _ in unfavorable], ["Marketing"])
        self.assertAlmostEqual(unfavorable[0][1], -4_000)

    def test_narrative_sentences_reference_top_drivers(self):
        pnl = _toy_pnl()
        var_df = variance.compute_variance(pnl)
        summary = variance.narrative(var_df, "2099-01", n=3)

        self.assertIn("Revenue", summary["favorable"][0])
        self.assertTrue(any("Marketing" in s for s in summary["unfavorable"]))
        self.assertAlmostEqual(summary["oi_variance"], 12_000)


if __name__ == "__main__":
    unittest.main()
