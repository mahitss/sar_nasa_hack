"""Synthetic tests for Mission 009 mask rules. They do not download imagery."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "tools" / "mission009_mask_review.py"
SPEC = importlib.util.spec_from_file_location("mission009_mask_review", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
review = importlib.util.module_from_spec(SPEC)
sys.modules["mission009_mask_review"] = review
SPEC.loader.exec_module(review)


class SclTests(unittest.TestCase):
    def test_class_counts_keep_water_as_a_label_only(self):
        stats = review.summarize_scl([0, 1, 2, 3, 6, 8, 9, 10, 11, 4])
        self.assertEqual(stats["invalid_nodata_or_defective"], 2)
        self.assertEqual(stats["cloud_shadow"], 1)
        self.assertEqual(stats["cast_shadow"], 1)
        self.assertEqual(stats["cloud_or_cirrus"], 3)
        self.assertEqual(stats["snow_or_ice"], 1)
        self.assertEqual(stats["class_counts"]["WATER"], 1)
        self.assertFalse(stats["water_class_is_validation"])
        self.assertAlmostEqual(stats["percent_of_window_pixels"]["cloud_or_cirrus"], 30.0)

    def test_unspecified_codes_are_preserved(self):
        stats = review.summarize_scl([0, 15])
        self.assertEqual(stats["unspecified_counts"], {"15": 1})
        self.assertEqual(review.scl_label(15), "UNSPECIFIED")


class QaTests(unittest.TestCase):
    def test_documented_fill_and_high_cloud_values(self):
        fill = review.decode_qa_pixel(1)
        self.assertTrue(fill["fill"])
        self.assertFalse(fill["cloud"])
        high = review.decode_qa_pixel(22280)
        self.assertTrue(high["cloud"])
        self.assertEqual(high["cloud_confidence"], "high")
        self.assertFalse(high["clear"])
        self.assertFalse(high["water_bit_is_validation"])

    def test_simultaneous_flags_count_once_in_the_union(self):
        value = (1 << 2) | (1 << 3) | (1 << 4)
        decoded = review.decode_qa_pixel(value)
        self.assertTrue(decoded["cirrus"] and decoded["cloud"] and decoded["cloud_shadow"])
        stats = review.summarize_qa([1, value, 21824])
        self.assertEqual(stats["fill"], 1)
        self.assertEqual(stats["cloud_shadow_cirrus_or_dilated_union"], 1)
        self.assertEqual(stats["flags_among_observed"]["cloud"], 1)
        self.assertEqual(stats["flags_among_observed"]["cirrus"], 1)
        self.assertEqual(stats["clear_bit_count_among_observed"], 1)
        self.assertEqual(stats["observed_without_those_flags_and_without_clear_bit"], 0)

    def test_missing_one_cloud_flag_is_not_called_clear(self):
        shadow_only = 1 << 4
        stats = review.summarize_qa([shadow_only])
        self.assertEqual(stats["flags_among_observed"]["cloud"], 0)
        self.assertEqual(stats["clear_bit_count_among_observed"], 0)
        self.assertEqual(stats["observed_without_those_flags_and_without_clear_bit"], 0)
        self.assertEqual(stats["cloud_shadow_cirrus_or_dilated_union"], 1)

    def test_confidence_bits(self):
        medium_cloud = (1 << 9)
        decoded = review.decode_qa_pixel(medium_cloud)
        self.assertEqual(decoded["cloud_confidence"], "medium")
        self.assertEqual(decoded["cloud_shadow_confidence"], "none")
        reserved = 1 << 11
        self.assertEqual(review.decode_qa_pixel(reserved)["cloud_shadow_confidence"], "reserved")


class WindowTests(unittest.TestCase):
    def test_center_selection_uses_the_native_grid(self):
        coarse = (0, 30, 0, 100, 0, -30)
        fine = (0, 20, 0, 100, 0, -20)
        coarse_hits = review.centers_inside_bbox(coarse, 4, 4, 15, 25, 75, 85)
        fine_hits = review.centers_inside_bbox(fine, 5, 5, 15, 25, 75, 85)
        self.assertNotEqual(set(coarse_hits), set(fine_hits))
        self.assertIn((1, 1), fine_hits)
        self.assertEqual(review.native_pixel_size(coarse), (30, 30))
        self.assertEqual(review.native_pixel_size(fine), (20, 20))
        with self.assertRaises(ValueError):
            review.reject_cross_sensor_resample(20, 30)

    def test_statistics_are_deterministic(self):
        values = [8, 8, 3, 0, 10]
        self.assertEqual(review.summarize_scl(values), review.summarize_scl(list(values)))
        cld = [0, 10, 20, 100]
        self.assertEqual(review.cld_summary(cld), review.cld_summary(list(cld)))
        self.assertEqual(review.cld_summary(cld)["median"], 15.0)


class AccessTests(unittest.TestCase):
    def test_landsat_login_redirect_blocks_download(self):
        decision = review.landsat_access_decision(
            {"status": 200, "content_type": "text/html", "content_length": "1200", "redirected": True, "url": "https://ers.cr.usgs.gov/login"}
        )
        self.assertFalse(decision["download"])
        self.assertTrue(any("TIFF" in reason or "object URL" in reason for reason in decision["reasons"]))


if __name__ == "__main__":
    unittest.main()
