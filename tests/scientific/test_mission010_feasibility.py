"""Synthetic tests for Mission 010 feasibility rules. They do not download data."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "tools" / "mission010_feasibility.py"
SPEC = importlib.util.spec_from_file_location("mission010_feasibility", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
feasibility = importlib.util.module_from_spec(SPEC)
sys.modules["mission010_feasibility"] = feasibility
SPEC.loader.exec_module(feasibility)


class CropTests(unittest.TestCase):
    def test_discovery_window_is_one_geocell_until_the_buffer_crosses_30n(self):
        cells = feasibility.geocells_for_bbox(*feasibility.DISCOVERY_BBOX)
        self.assertEqual(cells, [(30, 79)])
        plan = feasibility.crop_plan()
        stems = [item["dged_stem"] for item in plan["geocells_lower_left"]]
        self.assertEqual(
            stems,
            ["Copernicus_DSM_10_N29_00_E079_00", "Copernicus_DSM_10_N30_00_E079_00"],
        )
        self.assertEqual(plan["crop_postings"], {"east_west": 793, "north_south": 793})
        self.assertEqual(plan["uncompressed_elevation_bytes"], 793 * 793 * 4)
        self.assertEqual(plan["full_geocell_uncompressed_elevation_bytes"], 3601 * 3601 * 4)
        self.assertFalse(plan["downloaded"])

    def test_a_window_crossing_80e_adds_a_second_longitude_cell(self):
        cells = feasibility.geocells_for_bbox(79.9, 30.1, 80.1, 30.2)
        self.assertEqual(cells, [(30, 79), (30, 80)])


class GeometryTests(unittest.TestCase):
    def test_valid_samples_mask_is_not_terrain(self):
        role = feasibility.geometry_role(feasibility.GSLC_VALID_SAMPLES_MASK)
        self.assertIn("not a terrain", role)
        flag = feasibility.geometry_role(
            "/science/LSAR/GCOV/metadata/processingInformation/parameters/shadowMaskingApplied"
        )
        self.assertIn("scalar processing flag", flag)

    def test_incidence_cube_is_not_local_incidence(self):
        role = feasibility.geometry_role("/science/LSAR/GCOV/metadata/radarGrid/incidenceAngle")
        self.assertIn("not local slope incidence", role)
        self.assertIn("not the 10 m", role)

    def test_orbit_labels_stay_unresolved(self):
        labels = feasibility.orbit_labels_remain_unresolved("N", "MOE")
        self.assertFalse(labels["resolved"])
        self.assertEqual(labels["filename_fidelity_code"], "N")
        self.assertEqual(labels["internal_orbit_type"], "MOE")

    def test_manifest_does_not_download_or_run_a_model(self):
        manifest = feasibility.build_manifest()
        self.assertFalse(manifest["dem_downloaded"])
        self.assertFalse(manifest["nisar_product_opened"])
        self.assertFalse(manifest["terrain_model_run"])
        self.assertFalse(manifest["shadow_or_layover_mask_created"])
        self.assertFalse(manifest["nasadem"]["interchangeable_with_copernicus_dem"])
        self.assertFalse(manifest["cartodem"]["open_default"])
        self.assertFalse(manifest["gslc_mask_used_as_terrain"])
        self.assertIn("EGM2008", manifest["copernicus_dem"]["vertical_datum"])
        self.assertIn("EGM96", manifest["nasadem"]["vertical_datum"])


if __name__ == "__main__":
    unittest.main()
