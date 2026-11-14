"""Hardened tests for the water-candidate screen (Mission 005).

These fixtures are invented arrays. A passing test shows that the rules behave
as specified. It is not a measurement of the Kuwari crops and it is not an
accuracy figure.
"""

from __future__ import annotations

import importlib.util
import math
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "tools" / "water_candidate.py"
SPEC = importlib.util.spec_from_file_location("water_candidate", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
screen_module = importlib.util.module_from_spec(SPEC)
sys.modules["water_candidate"] = screen_module
SPEC.loader.exec_module(screen_module)

Parameters = screen_module.CandidateParameters


def grid(value: float, rows: int = 4, cols: int = 4) -> list[list[float]]:
    return [[value for _ in range(cols)] for _ in range(rows)]


def mask(value: int, rows: int = 4, cols: int = 4) -> list[list[int]]:
    return [[value for _ in range(cols)] for _ in range(rows)]


def paint(array, positions, value):
    for row, col in positions:
        array[row][col] = value
    return array


RULES = Parameters(
    hh_max_linear=0.05,
    hv_max_linear=0.02,
    min_looks=2.0,
    min_patch_pixels=2,
    max_hv_over_hh=0.5,
)


# ---------------------------------------------------------------------------
# Parameter validation: NaN and infinity
# ---------------------------------------------------------------------------

class ParameterValidationTests(unittest.TestCase):
    def test_nan_hh_limit_rejected(self):
        with self.assertRaises(ValueError):
            Parameters(math.nan, 0.02, 2.0, 2)

    def test_inf_hh_limit_rejected(self):
        with self.assertRaises(ValueError):
            Parameters(math.inf, 0.02, 2.0, 2)

    def test_nan_hv_limit_rejected(self):
        with self.assertRaises(ValueError):
            Parameters(0.05, math.nan, 2.0, 2)

    def test_inf_hv_limit_rejected(self):
        with self.assertRaises(ValueError):
            Parameters(0.05, math.inf, 2.0, 2)

    def test_nan_min_looks_rejected(self):
        with self.assertRaises(ValueError):
            Parameters(0.05, 0.02, math.nan, 2)

    def test_inf_min_looks_rejected(self):
        with self.assertRaises(ValueError):
            Parameters(0.05, 0.02, math.inf, 2)

    def test_nan_ratio_gate_rejected(self):
        with self.assertRaises(ValueError):
            Parameters(0.05, 0.02, 2.0, 2, math.nan)

    def test_inf_ratio_gate_rejected(self):
        with self.assertRaises(ValueError):
            Parameters(0.05, 0.02, 2.0, 2, math.inf)


# ---------------------------------------------------------------------------
# Parameter validation: zero and negative
# ---------------------------------------------------------------------------

class ParameterBoundsTests(unittest.TestCase):
    def test_zero_hh_limit_rejected(self):
        with self.assertRaises(ValueError):
            Parameters(0.0, 0.02, 2.0, 2)

    def test_negative_hh_limit_rejected(self):
        with self.assertRaises(ValueError):
            Parameters(-0.05, 0.02, 2.0, 2)

    def test_zero_hv_limit_rejected(self):
        with self.assertRaises(ValueError):
            Parameters(0.05, 0.0, 2.0, 2)

    def test_negative_hv_limit_rejected(self):
        with self.assertRaises(ValueError):
            Parameters(0.05, -0.02, 2.0, 2)

    def test_negative_min_looks_rejected(self):
        with self.assertRaises(ValueError):
            Parameters(0.05, 0.02, -1.0, 2)

    def test_zero_min_patch_pixels_rejected(self):
        with self.assertRaises(ValueError):
            Parameters(0.05, 0.02, 2.0, 0)

    def test_negative_min_patch_pixels_rejected(self):
        with self.assertRaises(ValueError):
            Parameters(0.05, 0.02, 2.0, -1)

    def test_zero_ratio_gate_rejected(self):
        with self.assertRaises(ValueError):
            Parameters(0.05, 0.02, 2.0, 2, 0.0)

    def test_negative_ratio_gate_rejected(self):
        with self.assertRaises(ValueError):
            Parameters(0.05, 0.02, 2.0, 2, -0.5)

    def test_non_integer_min_patch_pixels_rejected(self):
        with self.assertRaises(ValueError):
            Parameters(0.05, 0.02, 2.0, 2.5)

    def test_bool_min_patch_pixels_rejected(self):
        with self.assertRaises(ValueError):
            Parameters(0.05, 0.02, 2.0, True)


# ---------------------------------------------------------------------------
# Sensitivity: validity classification
# ---------------------------------------------------------------------------

class SensitivityValidityTests(unittest.TestCase):
    def setUp(self):
        self.hhhh = grid(0.4, rows=4, cols=4)
        self.hvhv = grid(0.08, rows=4, cols=4)
        self.looks = grid(6.0, rows=4, cols=4)
        self.gcov = mask(1, rows=4, cols=4)
        # Make top-left pixel invalid on all dates (mask code 0)
        self.gcov[0][0] = 0

    def test_pixel_invalid_in_every_set(self):
        strict = Parameters(0.05, 0.02, 2.0, 2)
        loose = Parameters(0.50, 0.50, 2.0, 2)
        result = screen_module.sensitivity(
            self.hhhh, self.hvhv, self.looks, self.gcov, (strict, loose)
        )
        validity = result.validity_class()
        # (0,0) has gcov mask 0 -> invalid in every set
        self.assertEqual(validity[0][0], -1)

    def test_pixel_valid_in_some_but_not_all_sets(self):
        # high min_looks makes some pixels invalid
        hhhh = grid(0.01, rows=4, cols=4)
        hvhv = grid(0.002, rows=4, cols=4)
        looks = grid(6.0, rows=4, cols=4)
        gcov = mask(1, rows=4, cols=4)
        looks[0][0] = 1.0  # below min_looks=2
        strict = Parameters(0.05, 0.02, 2.0, 2)
        loose = Parameters(0.05, 0.02, 1.0, 2)
        result = screen_module.sensitivity(hhhh, hvhv, looks, gcov, (strict, loose))
        validity = result.validity_class()
        self.assertEqual(validity[0][0], 0)

    def test_pixel_valid_in_every_set(self):
        hhhh = grid(0.01, rows=4, cols=4)
        hvhv = grid(0.002, rows=4, cols=4)
        looks = grid(6.0, rows=4, cols=4)
        gcov = mask(1, rows=4, cols=4)
        strict = Parameters(0.05, 0.02, 2.0, 2)
        loose = Parameters(0.50, 0.50, 2.0, 2)
        result = screen_module.sensitivity(hhhh, hvhv, looks, gcov, (strict, loose))
        validity = result.validity_class()
        self.assertEqual(validity[1][1], 1)

    def test_candidate_in_every_valid_set(self):
        hhhh = grid(0.01, rows=4, cols=4)
        hvhv = grid(0.002, rows=4, cols=4)
        looks = grid(6.0, rows=4, cols=4)
        gcov = mask(1, rows=4, cols=4)
        strict = Parameters(0.05, 0.02, 2.0, 2)
        loose = Parameters(0.50, 0.50, 2.0, 2)
        result = screen_module.sensitivity(hhhh, hvhv, looks, gcov, (strict, loose))
        stability = result.candidate_stability_class()
        self.assertEqual(stability[1][1], 1)

    def test_candidate_in_some_but_not_all_valid_sets(self):
        hhhh = grid(0.08, rows=4, cols=4)
        hvhv = grid(0.002, rows=4, cols=4)
        looks = grid(6.0, rows=4, cols=4)
        gcov = mask(1, rows=4, cols=4)
        paint(hhhh, [(2, 2), (2, 3), (3, 2), (3, 3)], 0.01)
        strict = Parameters(0.05, 0.02, 2.0, 2)
        loose = Parameters(0.10, 0.02, 2.0, 2)
        result = screen_module.sensitivity(hhhh, hvhv, looks, gcov, (strict, loose))
        stability = result.candidate_stability_class()
        self.assertEqual(stability[2][2], 1)
        self.assertEqual(stability[0][0], 0)

    def test_never_candidate_while_valid(self):
        hhhh = grid(0.4, rows=4, cols=4)
        hvhv = grid(0.4, rows=4, cols=4)
        looks = grid(6.0, rows=4, cols=4)
        gcov = mask(1, rows=4, cols=4)
        strict = Parameters(0.05, 0.02, 2.0, 2)
        loose = Parameters(0.2, 0.2, 2.0, 2)
        result = screen_module.sensitivity(hhhh, hvhv, looks, gcov, (strict, loose))
        stability = result.candidate_stability_class()
        self.assertEqual(stability[1][1], -1)

    def test_raw_vs_filtered_candidate_counts(self):
        hhhh = grid(0.4, rows=4, cols=4)
        hvhv = grid(0.08, rows=4, cols=4)
        looks = grid(6.0, rows=4, cols=4)
        gcov = mask(1, rows=4, cols=4)
        # 2x2 patch of low backscatter at top-left
        paint(hhhh, [(0, 0), (0, 1), (1, 0), (1, 1)], 0.01)
        paint(hvhv, [(0, 0), (0, 1), (1, 0), (1, 1)], 0.002)
        strict = Parameters(0.05, 0.02, 2.0, 4)  # min_patch=4, patch of 4 survives
        loose = Parameters(0.05, 0.02, 2.0, 5)   # min_patch=5, patch of 4 removed
        result = screen_module.sensitivity(hhhh, hvhv, looks, gcov, (strict, loose))
        # raw_candidate_count[0][0] should be 2 (raw candidate in both)
        self.assertEqual(result.raw_candidate_count[0][0], 2)
        # filtered_candidate_count[0][0] should be 1 (kept in strict, removed in loose)
        self.assertEqual(result.filtered_candidate_count[0][0], 1)


class SensitivityEdgeTests(unittest.TestCase):
    def test_single_parameter_set(self):
        hhhh = grid(0.01, rows=2, cols=2)
        hvhv = grid(0.002, rows=2, cols=2)
        looks = grid(6.0, rows=2, cols=2)
        gcov = mask(1, rows=2, cols=2)
        params = Parameters(0.05, 0.02, 2.0, 2)
        result = screen_module.sensitivity(hhhh, hvhv, looks, gcov, (params,))
        self.assertEqual(result.total_sets, 1)
        self.assertEqual(result.valid_count[0][0], 1)
        self.assertEqual(result.filtered_candidate_count[0][0], 1)

    def test_empty_parameter_sets_rejected(self):
        hhhh = grid(0.01, rows=2, cols=2)
        hvhv = grid(0.002, rows=2, cols=2)
        looks = grid(6.0, rows=2, cols=2)
        gcov = mask(1, rows=2, cols=2)
        with self.assertRaises(ValueError):
            screen_module.sensitivity(hhhh, hvhv, looks, gcov, ())

    def test_deterministic_repeated_runs(self):
        hhhh = grid(0.01, rows=4, cols=4)
        hvhv = grid(0.002, rows=4, cols=4)
        looks = grid(6.0, rows=4, cols=4)
        gcov = mask(1, rows=4, cols=4)
        params = [
            Parameters(0.05, 0.02, 2.0, 2),
            Parameters(0.10, 0.02, 2.0, 2),
        ]
        first = screen_module.sensitivity(hhhh, hvhv, looks, gcov, params)
        second = screen_module.sensitivity(hhhh, hvhv, looks, gcov, params)
        self.assertEqual(first.valid_count, second.valid_count)
        self.assertEqual(first.raw_candidate_count, second.raw_candidate_count)
        self.assertEqual(first.filtered_candidate_count, second.filtered_candidate_count)


class ScreenDetailedTests(unittest.TestCase):
    def test_raw_labels_preserved_before_patch_filter(self):
        hhhh = grid(0.4, rows=4, cols=4)
        hvhv = grid(0.08, rows=4, cols=4)
        looks = grid(6.0, rows=4, cols=4)
        gcov = mask(1, rows=4, cols=4)
        paint(hhhh, [(0, 0)], 0.01)
        paint(hvhv, [(0, 0)], 0.002)
        result = screen_module.screen_detailed(hhhh, hvhv, looks, gcov, RULES)
        # Single pixel raw candidate -> raw=1, but filtered=0 (patch too small)
        self.assertEqual(result.raw[0][0], 1)
        self.assertEqual(result.filtered[0][0], 0)
        self.assertEqual(result.valid[0][0], 1)

    def test_invalid_pixel_not_raw_candidate(self):
        hhhh = grid(0.01, rows=4, cols=4)
        hvhv = grid(0.002, rows=4, cols=4)
        looks = grid(6.0, rows=4, cols=4)
        gcov = mask(1, rows=4, cols=4)
        gcov[0][0] = 0
        result = screen_module.screen_detailed(hhhh, hvhv, looks, gcov, RULES)
        self.assertEqual(result.raw[0][0], -1)
        self.assertEqual(result.filtered[0][0], -1)
        self.assertEqual(result.valid[0][0], 0)

    def test_source_arrays_unchanged(self):
        hhhh = grid(0.4, rows=4, cols=4)
        hvhv = grid(0.08, rows=4, cols=4)
        looks = grid(6.0, rows=4, cols=4)
        gcov = mask(1, rows=4, cols=4)
        before_hhhh = [row[:] for row in hhhh]
        before_hvhv = [row[:] for row in hvhv]
        screen_module.screen(hhhh, hvhv, looks, gcov, RULES)
        self.assertEqual(hhhh, before_hhhh)
        self.assertEqual(hvhv, before_hvhv)


if __name__ == "__main__":
    unittest.main()
