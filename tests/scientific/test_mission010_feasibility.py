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

    def test_filename_n_expects_noe_and_moe_is_an_unresolved_mismatch(self):
        labels = feasibility.orbit_labels_remain_unresolved("N", "MOE")
        self.assertEqual(labels["filename_expected_orbit_ephemeris"], "NOE")
        self.assertEqual(labels["observed_orbit_type"], "MOE")
        self.assertEqual(labels["consistency"], "mismatch")
        self.assertFalse(labels["resolved"])
        self.assertFalse(labels["verified_against_product_file"])
        self.assertIn("disagree", labels["reason"])

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
        paths = {item["path"]: item["role"] for item in manifest["nisar_geometry"]["datasets"]}
        for name in ("bias/x", "bias/y", "standardDeviation/x", "standardDeviation/y"):
            role = paths["/science/LSAR/GCOV/metadata/ceosAnalysisReadyData/geometricAccuracy/" + name]
            self.assertIn("estimate", role)
            self.assertIn("not independent surveyed ground truth", role)
        self.assertIn("demSource", "".join(paths))
        self.assertIn("demFiles", "".join(paths))
        self.assertIn("/science/LSAR/GCOV/metadata/radarGrid/xCoordinates", paths)
        self.assertIn("/science/LSAR/GCOV/metadata/radarGrid/yCoordinates", paths)
        self.assertIn("/science/LSAR/GCOV/metadata/radarGrid/heightAboveEllipsoid", paths)
        self.assertIn("not read", paths["/science/LSAR/GCOV/metadata/radarGrid/xCoordinates"])
        orbit = manifest["nisar_geometry"]["orbit_labels"]
        self.assertEqual(orbit["consistency"], "mismatch")
        self.assertFalse(manifest["nisar_product_downloaded"])
        saved = Path(__file__).resolve().parents[2] / "data" / "manifests" / "mission010_terrain_geometry.json"
        if saved.exists():
            import json
            self.assertEqual(json.loads(saved.read_text(encoding="utf-8")), manifest)


if __name__ == "__main__":
    unittest.main()
