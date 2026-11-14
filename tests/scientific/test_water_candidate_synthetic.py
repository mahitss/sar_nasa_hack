"""Synthetic tests for the water-candidate screen.

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


class ScreenTests(unittest.TestCase):
    def test_low_backscatter_patch_is_candidate_and_source_is_unchanged(self):
        hhhh = grid(0.4)
        hvhv = grid(0.08)
        looks = grid(6.0)
        gcov = mask(1)
        paint(hhhh, [(0, 0), (0, 1), (1, 0), (1, 1)], 0.01)
        paint(hvhv, [(0, 0), (0, 1), (1, 0), (1, 1)], 0.002)
        before = [row[:] for row in hhhh]
        labels = screen_module.screen(hhhh, hvhv, looks, gcov, RULES)
        self.assertEqual(hhhh, before)
        self.assertEqual(labels[0][0], 1)
        self.assertEqual(labels[0][1], 1)
        self.assertEqual(labels[2][2], 0)

    def test_output_is_deterministic(self):
        hhhh = grid(0.01)
        hvhv = grid(0.002)
        looks = grid(5.0)
        gcov = mask(1)
        first = screen_module.screen(hhhh, hvhv, looks, gcov, RULES)
        second = screen_module.screen(hhhh, hvhv, looks, gcov, RULES)
        self.assertEqual(first, second)

    def test_wet_soil_vegetation_debris_and_extreme_values_are_not_candidates(self):
        hhhh = grid(0.01)
        hvhv = grid(0.002)
        looks = grid(8.0)
        gcov = mask(1)
        paint(hhhh, [(0, 2), (0, 3)], 0.4)
        paint(hvhv, [(0, 2), (0, 3)], 0.01)
        paint(hhhh, [(1, 2), (1, 3)], 0.02)
        paint(hvhv, [(1, 2), (1, 3)], 0.2)
        paint(hhhh, [(2, 0), (2, 1)], 10.0)
        paint(hvhv, [(2, 0), (2, 1)], 2.0)
        paint(hhhh, [(2, 2), (2, 3)], 30000.0)
        paint(hvhv, [(2, 2), (2, 3)], 1000.0)
        labels = screen_module.screen(hhhh, hvhv, looks, gcov, RULES)
        for position in ((0, 2), (1, 2), (2, 0), (2, 2)):
            self.assertEqual(labels[position[0]][position[1]], 0, position)

    def test_invalid_mask_nodata_and_low_looks_stay_invalid(self):
        hhhh = grid(0.01)
        hvhv = grid(0.002)
        looks = grid(8.0)
        gcov = mask(1)
        gcov[0][0] = 0
        gcov[0][1] = 255
        hhhh[1][0] = math.nan
        hvhv[1][1] = math.inf
        looks[2][0] = 0.2
        looks[2][1] = math.nan
        gslc = mask(1)
        gslc[3][0] = 0
        labels = screen_module.screen(hhhh, hvhv, looks, gcov, RULES, gslc)
        for position in ((0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1), (3, 0)):
            self.assertEqual(labels[position[0]][position[1]], -1, position)
        self.assertEqual(labels[3][1], 1)

    def test_small_patch_is_removed_and_exact_threshold_is_kept(self):
        hhhh = grid(0.4)
        hvhv = grid(0.08)
        looks = grid(4.0)
        gcov = mask(1)
        paint(hhhh, [(0, 0)], 0.01)
        paint(hvhv, [(0, 0)], 0.002)
        paint(hhhh, [(2, 2), (2, 3)], 0.05)
        paint(hvhv, [(2, 2), (2, 3)], 0.02)
        labels = screen_module.screen(hhhh, hvhv, looks, gcov, RULES)
        self.assertEqual(labels[0][0], 0)
        self.assertEqual(labels[2][2], 1)
        self.assertEqual(labels[2][3], 1)

    def test_pixel_just_above_threshold_is_not_a_candidate(self):
        hhhh = grid(0.4)
        hvhv = grid(0.08)
        looks = grid(4.0)
        gcov = mask(1)
        paint(hhhh, [(0, 0), (0, 1)], 0.05 + 1e-12)
        paint(hvhv, [(0, 0), (0, 1)], 0.002)
        labels = screen_module.screen(hhhh, hvhv, looks, gcov, RULES)
        self.assertEqual(labels[0][0], 0)
        self.assertEqual(labels[0][1], 0)

    def test_ratio_gate_rejects_high_cross_pol_fraction(self):
        hhhh = grid(0.02, rows=2, cols=2)
        hvhv = grid(0.015, rows=2, cols=2)
        looks = grid(5.0, rows=2, cols=2)
        gcov = mask(1, rows=2, cols=2)
        closed = screen_module.screen(hhhh, hvhv, looks, gcov, RULES)
        opened = screen_module.screen(
            hhhh,
            hvhv,
            looks,
            gcov,
            Parameters(0.05, 0.02, 2.0, 2, max_hv_over_hh=None),
        )
        self.assertEqual(closed[0][0], 0)
        self.assertEqual(opened[0][0], 1)

    def test_db_feature_is_separate_from_linear_source(self):
        power = 0.05
        self.assertAlmostEqual(screen_module.linear_to_db(power), 10.0 * math.log10(power))
        self.assertAlmostEqual(screen_module.db_to_linear(-20.0), 0.01)
        with self.assertRaises(ValueError):
            screen_module.linear_to_db(0.0)

    def test_misaligned_grids_are_rejected(self):
        with self.assertRaises(screen_module.GridMismatch):
            screen_module.screen(grid(0.01, 2, 2), grid(0.002, 2, 3), grid(4, 2, 2), mask(1, 2, 2), RULES)
        with self.assertRaises(screen_module.GridMismatch):
            screen_module.compare([[1, 0]], [[1, 0], [0, 0]])

    def test_change_classes_ignore_invalid_pixels(self):
        earlier = [
            [1, 1, 0, -1],
            [0, -1, 1, 0],
        ]
        later = [
            [1, 0, 1, 1],
            [0, 1, 1, -1],
        ]
        result = screen_module.compare(earlier, later)
        self.assertEqual(result["persistent"], 2)
        self.assertEqual(result["gained"], 1)
        self.assertEqual(result["lost"], 1)
        self.assertEqual(result["excluded"], 3)
        self.assertEqual(result["classes"][0][3], 0)
        self.assertEqual(result["classes"][1][1], 0)

    def test_sensitivity_count_is_not_a_fraction(self):
        hhhh = grid(0.4, rows=2, cols=2)
        hvhv = grid(0.002, rows=2, cols=2)
        looks = grid(5.0, rows=2, cols=2)
        gcov = mask(1, rows=2, cols=2)
        paint(hhhh, [(0, 0), (0, 1)], 0.01)
        paint(hhhh, [(1, 0), (1, 1)], 0.08)
        strict = Parameters(0.05, 0.02, 2.0, 2, 0.5)
        loose = Parameters(0.10, 0.02, 2.0, 2, 0.5)
        result = screen_module.sensitivity(hhhh, hvhv, looks, gcov, (strict, loose))
        counts = result.filtered_candidate_count
        self.assertEqual(counts[0][0], 2)
        self.assertEqual(counts[1][0], 1)
        self.assertLessEqual(max(max(row) for row in counts), result.total_sets)
        self.assertEqual(result.validity_class()[0][0], 1)


if __name__ == "__main__":
    unittest.main()
