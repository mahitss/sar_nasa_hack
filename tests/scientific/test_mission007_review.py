"""Tests for Mission 007 review rules. They do not read the Kuwari rasters."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "tools" / "mission007_review.py"
SPEC = importlib.util.spec_from_file_location("mission007_review", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
review = importlib.util.module_from_spec(SPEC)
sys.modules["mission007_review"] = review
SPEC.loader.exec_module(review)


def grid(rows, cols, value):
    return [[value for _ in range(cols)] for _ in range(rows)]


class RelationshipTests(unittest.TestCase):
    def test_filtered_count_cannot_exceed_raw_or_valid(self):
        valid = [[10, 10], [0, 4]]
        raw = [[10, 3], [0, 4]]
        filtered = [[9, 4], [0, 4]]
        problems = review.count_relationships(valid, raw, filtered)
        self.assertTrue(any("exceeds raw" in item for item in problems))

    def test_consistent_counts_pass(self):
        valid = [[1092, 10], [0, 4]]
        raw = [[1092, 0], [0, 2]]
        filtered = [[0, 0], [0, 2]]
        self.assertEqual(review.count_relationships(valid, raw, filtered), [])


class InventoryTests(unittest.TestCase):
    def test_diagonal_pixels_stay_separate_and_are_not_a_lake(self):
        raw_stability = grid(3, 3, -1)
        filtered_stability = grid(3, 3, -1)
        validity = grid(3, 3, 1)
        raw_counts = grid(3, 3, 0)
        filtered_counts = grid(3, 3, 0)
        raw_stability[0][0] = 2
        raw_stability[1][1] = 2
        raw_counts[0][0] = 1092
        raw_counts[1][1] = 1092
        records = review.inventory_regions(
            "20260906",
            raw_stability,
            filtered_stability,
            raw_counts,
            filtered_counts,
            validity,
        )
        stable = [item for item in records if item["candidate_class"] == "raw_fully_sweep_stable"]
        self.assertEqual(len(stable), 2)
        self.assertTrue(all(item["pixel_count"] == 1 for item in stable))
        self.assertNotIn("area_m2", stable[0])
        self.assertTrue(any("not a lake" in note for note in stable[0]["limitations"]))

    def test_boundary_and_invalid_contact_are_recorded(self):
        raw_stability = grid(2, 2, -1)
        filtered_stability = grid(2, 2, -1)
        validity = grid(2, 2, 1)
        validity[0][1] = -1
        filtered_stability[0][0] = 1
        raw_counts = grid(2, 2, 0)
        filtered_counts = grid(2, 2, 0)
        raw_counts[0][0] = 546
        filtered_counts[0][0] = 546
        records = review.inventory_regions(
            "20260930",
            raw_stability,
            filtered_stability,
            raw_counts,
            filtered_counts,
            validity,
        )
        partial = [item for item in records if "partially_valid" in item["candidate_class"]]
        self.assertEqual(len(partial), 1)
        self.assertTrue(partial[0]["touches_raster_boundary"])
        self.assertTrue(partial[0]["touches_invalid_pixels"])


class EvidenceAndDecisionTests(unittest.TestCase):
    def test_evidence_records_are_complete_and_do_not_retune(self):
        for record in review.EVIDENCE:
            self.assertEqual(review.validate_evidence(record), [])

    def test_missing_evidence_field_is_rejected(self):
        incomplete = {field: "x" for field in review.EVIDENCE_FIELDS}
        del incomplete["access"]
        problems = review.validate_evidence(incomplete)
        self.assertTrue(any("access" in item for item in problems))

    def test_review_decision_cannot_confirm_water(self):
        record = review.review_record("R007-test", "unresolved_insufficient_evidence", "waiting")
        self.assertFalse(record["confirmed_water"])
        self.assertFalse(record["area_estimated"])
        with self.assertRaises(ValueError):
            review.review_record("R007-test", "confirmed_water", "no")


if __name__ == "__main__":
    unittest.main()
