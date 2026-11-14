"""Synthetic tests for Mission 008 catalogue rules. They do not query a STAC API."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "tools" / "mission008_catalogue.py"
SPEC = importlib.util.spec_from_file_location("mission008_catalogue", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
catalogue = importlib.util.module_from_spec(SPEC)
sys.modules["mission008_catalogue"] = catalogue
SPEC.loader.exec_module(catalogue)


def feature(collection, when, level="L2A", cloud=10):
    return {
        "id": "example",
        "collection": collection,
        "bbox": [79.7, 30.0, 79.9, 30.2],
        "geometry": {"type": "Polygon", "coordinates": [[[79.7, 30.0], [79.9, 30.0], [79.9, 30.2], [79.7, 30.2], [79.7, 30.0]]]},
        "properties": {
            "datetime": when,
            "platform": "sentinel-2c",
            "eo:cloud_cover": cloud,
            "s2:product_type": "S2MSI2A" if level == "L2A" else "S2MSI1C",
            "processing:level": "L2" if level == "L2A" else "L1",
        },
        "assets": {
            "red": {"type": "image/tiff", "roles": ["data"], "gsd": 10, "file:size": 100, "href": "https://example.test/red.tif?token=secret"},
            "scl": {"type": "image/tiff", "roles": ["data"], "href": "https://example.test/scl.tif"},
        },
    }


class TemporalTests(unittest.TestCase):
    def test_exact_and_nearby_stay_distinct(self):
        exact = catalogue.temporal_relation("2026-09-06T05:30:00Z", "2026-09-06", 5)
        nearby = catalogue.temporal_relation("2026-09-07T05:30:00Z", "2026-09-06", 5)
        outside = catalogue.temporal_relation("2026-09-20T05:30:00Z", "2026-09-06", 5)
        self.assertEqual(exact["temporal_class"], "exact")
        self.assertEqual(nearby["temporal_class"], "nearby")
        self.assertEqual(nearby["day_offset_from_nisar_date"], 1)
        self.assertEqual(outside["temporal_class"], "outside")
        self.assertFalse(exact["same_date_ground_truth"])
        self.assertFalse(nearby["same_date_ground_truth"])

    def test_landsat_fallback_is_eight_days(self):
        edge = catalogue.temporal_relation("2026-08-29T05:12:00Z", "2026-09-06", 8)
        beyond = catalogue.temporal_relation("2026-08-28T05:12:00Z", "2026-09-06", 8)
        self.assertEqual(edge["temporal_class"], "nearby")
        self.assertEqual(edge["day_offset_from_nisar_date"], -8)
        self.assertEqual(beyond["temporal_class"], "outside")


class LevelTests(unittest.TestCase):
    def test_l1c_is_not_reported_as_l2a(self):
        level = catalogue.processing_level("sentinel-2-l1c", {"processing:level": "L2", "s2:product_type": "S2MSI1C"})
        self.assertEqual(level["level"], "L1C")
        self.assertTrue(level["atmospheric_correction_required"])
        self.assertFalse(level["surface_reflectance"])

    def test_l2a_and_landsat_surface_reflectance_are_preserved(self):
        self.assertEqual(catalogue.processing_level("sentinel-2-c1-l2a", {})["level"], "L2A")
        self.assertEqual(catalogue.processing_level("sentinel-2-pre-c1-l2a", {})["level"], "L2A")
        landsat = catalogue.processing_level("landsat-c2l2-sr", {})
        self.assertIn("Surface Reflectance", landsat["level"])
        temperature = catalogue.processing_level("landsat-c2l2-st", {})
        self.assertFalse(temperature["substitutes_for_surface_reflectance"])
        self.assertNotIn("Surface Reflectance", temperature["level"])

    def test_query_plan_uses_the_live_collection_ids(self):
        collections = {item["collection_id"] for item in catalogue.query_plan()}
        self.assertTrue({"sentinel-2-l2a", "sentinel-2-c1-l2a", "sentinel-2-pre-c1-l2a", "sentinel-2-l1c", "landsat-c2l2-sr"} <= collections)
        exact = [item for item in catalogue.query_plan() if item["search_class"] == "exact"]
        nearby = [item for item in catalogue.query_plan() if item["search_class"] == "nearby_window"]
        self.assertTrue(exact)
        self.assertTrue(nearby)
        self.assertTrue(all(item["datetime"].startswith("2026-09-06") or item["datetime"].startswith("2026-09-30") for item in exact))


class GeometryAndProvenanceTests(unittest.TestCase):
    def test_overlap_percent_for_contained_partial_and_disjoint_footprints(self):
        window = catalogue.DISCOVERY_BBOX
        contained = catalogue.window_overlap_percent(
            {"type": "Polygon", "coordinates": [[[79.0, 29.0], [80.5, 29.0], [80.5, 31.0], [79.0, 31.0], [79.0, 29.0]]]},
            window,
        )
        half = catalogue.window_overlap_percent(
            {"type": "Polygon", "coordinates": [[[79.75, 30.03], [79.81, 30.03], [79.81, 30.15], [79.75, 30.15], [79.75, 30.03]]]},
            window,
        )
        disjoint = catalogue.window_overlap_percent(
            {"type": "Polygon", "coordinates": [[[1, 1], [2, 1], [2, 2], [1, 2], [1, 1]]]},
            window,
        )
        self.assertAlmostEqual(contained["discovery_window_covered_percent"], 100.0, places=6)
        self.assertAlmostEqual(half["discovery_window_covered_percent"], 50.0, places=6)
        self.assertFalse(disjoint["intersects_discovery_window"])

    def test_summary_keeps_level_and_does_not_download(self):
        item = catalogue.summarize_feature(feature("sentinel-2-l1c", "2026-09-07T05:30:00Z", "L1C"), "2026-09-06", 5, "element84")
        self.assertEqual(item["processing"]["level"], "L1C")
        self.assertFalse(item["imagery_downloaded"])
        self.assertFalse(item["water_classified"])
        self.assertFalse(item["diagnostic_window_cloud_known"])
        self.assertEqual(item["temporal"]["temporal_class"], "nearby")
        self.assertNotIn("token=secret", item["assets"][0]["href"])
        self.assertTrue(item["assets"][0]["query_secrets_removed"])
        self.assertIn("scl", item["cloud_mask_assets"])

    def test_pagination_complete_only_when_the_server_count_matches(self):
        complete = catalogue.pagination_status(2, ["a", "b"], False)
        incomplete = catalogue.pagination_status(5, ["a", "b"], True)
        uncounted = catalogue.pagination_status(None, ["a"], False)
        self.assertTrue(complete["complete"])
        self.assertFalse(incomplete["complete"])
        self.assertTrue(uncounted["complete"])
        self.assertFalse(uncounted["matched_reported"])

    def test_manifest_flags_forbid_water_and_downloads(self):
        manifest = catalogue.build_manifest([], [], "2026-11-14T00:00:00Z")
        self.assertFalse(manifest["imagery_downloaded"])
        self.assertFalse(manifest["water_classified"])
        self.assertFalse(manifest["area_calculated"])
        self.assertFalse(manifest["shoreline_calculated"])
        self.assertFalse(manifest["mission006_thresholds_changed"])
        self.assertEqual(manifest["discovery_window"]["bbox"], [79.75, 30.03, 79.87, 30.15])


if __name__ == "__main__":
    unittest.main()
