"""Tests for distribution-audit helpers. They do not read satellite crops."""

from __future__ import annotations

import importlib.util
import math
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "tools" / "distribution_audit.py"
SPEC = importlib.util.spec_from_file_location("distribution_audit", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class StatisticTests(unittest.TestCase):
    def test_percentile_interpolates_inclusive_rank(self):
        self.assertEqual(audit.percentile([1, 2, 3, 4], 50), 2.5)
        self.assertEqual(audit.percentile([1, 2, 3, 4], 0), 1)
        self.assertEqual(audit.percentile([1, 2, 3, 4], 100), 4)
        self.assertIsNone(audit.percentile([], 50))

    def test_population_std_uses_divisor_n(self):
        summary = audit.summarize([1, 2, 3])
        self.assertEqual(summary["mean"], 2)
        self.assertAlmostEqual(summary["population_std"], math.sqrt(2 / 3))

    def test_db_histogram_counts_positive_power_only(self):
        bins = audit.db_histogram([0.01, 0.1, math.nan, -1], width=10)
        self.assertEqual(sum(item["count"] for item in bins), 2)

    def test_mask_frequencies_keep_zero_and_fill(self):
        counts = audit.mask_frequencies([0, 1, 1, 255])
        self.assertEqual(counts, {"0": 1, "1": 2, "255": 1})

    def test_profile_step_skips_empty_rows(self):
        values = [[1.0, 3.0], [math.nan, math.nan], [10.0, 10.0]]
        valid = [[True, True], [False, False], [True, True]]
        means = audit.axis_means(values, valid)
        steps = audit.adjacent_steps(means, as_db=True)
        self.assertEqual(steps["step_count"], 0)
        self.assertIsNone(means[1])

    def test_linear_mean_step_and_db_mean_step_stay_separate(self):
        values = [[1.0, 1.0], [1.0, 10000.0]]
        mask = [[1, 1], [1, 1]]
        result = audit.layer_audit(values, mask, "power")
        linear_step = result["row_mean_profile_summary"]["largest_absolute_step"]["delta"]
        db_step = result["row_db_mean_profile_summary"]["largest_absolute_step"]["delta"]
        self.assertGreater(abs(linear_step), abs(db_step))
        self.assertAlmostEqual(result["row_db_mean_profile"][0], 0.0)

    def test_high_tail_bbox_does_not_name_a_cause(self):
        rows = [[1.0, 1.0], [20.0, 20.0]]
        report = audit.high_tail_bbox(rows, 10)
        self.assertEqual(report["count"], 2)
        self.assertNotIn("debris", report)
        self.assertNotIn("rfi", report)

    def test_audit_source_does_not_classify(self):
        text = MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("import water_candidate", text)
        self.assertNotIn("screen(", text)
        self.assertNotIn("screen_detailed", text)


if __name__ == "__main__":
    unittest.main()
