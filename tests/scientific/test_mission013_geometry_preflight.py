"""Tests for Mission 013 radar-geometry preflight tool.

Uses synthetic inputs; does not download NISAR products or read real crops.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(name: str, filename: str):
    path = ROOT / "tools" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


SWEEP = load("mission013_geometry_preflight", "mission013_geometry_preflight.py")


class ChecksumTests(unittest.TestCase):
    def test_sha256_is_deterministic(self):
        a = SWEEP.sha256(Path(__file__))
        b = SWEEP.sha256(Path(__file__))
        self.assertEqual(a, b)
        self.assertEqual(len(a), 64)


class GridTests(unittest.TestCase):
    def test_expected_grid_matches_mission003(self):
        self.assertEqual(SWEEP.EXPECTED_GRID["crs"], "EPSG:32644")
        self.assertEqual(SWEEP.EXPECTED_GRID["width"], 1171)
        self.assertEqual(SWEEP.EXPECTED_GRID["height"], 1343)
        self.assertEqual(SWEEP.EXPECTED_GRID["geotransform"], (379470.0, 10.0, 0.0, 3336070.0, 0.0, -10.0))


class DesignAssessmentTests(unittest.TestCase):
    def test_decision_go_when_no_blockers(self):
        granule_records = [
            {
                "filename": "granule_001.h5",
                "access_error": None,
                "scalars": {
                    "science/LSAR/GCOV/metadata/orbit/orbitType": "MOE",
                    "science/LSAR/GCOV/metadata/attitude/attitudeType": "Custom",
                    "science/LSAR/GCOV/metadata/processingInformation/parameters/shadowMaskingApplied": "False",
                },
                "datasets": {
                    "science/LSAR/GCOV/metadata/radarGrid/xCoordinates": {"shape": [710]},
                    "science/LSAR/GCOV/metadata/radarGrid/yCoordinates": {"shape": [699]},
                },
            }
        ]
        dem_record = {
            "vertical_reference": {
                "dem_vertical_datum": "WGS84 ellipsoid",
                "transformation_applied": False,
            }
        }
        result = SWEEP.design_assessment(granule_records, dem_record)
        self.assertEqual(result["decision"], "GO")
        self.assertEqual(result["blockers"], [])

    def test_decision_blocked_when_missing_geometry_dataset(self):
        granule_records = [
            {
                "filename": "granule_001.h5",
                "access_error": None,
                "scalars": {},
                "datasets": {
                    "science/LSAR/GCOV/metadata/radarGrid/incidenceAngle": {"absent": True},
                    "science/LSAR/GCOV/metadata/radarGrid/xCoordinates": {"shape": [710]},
                    "science/LSAR/GCOV/metadata/radarGrid/yCoordinates": {"shape": [699]},
                },
            }
        ]
        dem_record = {
            "vertical_reference": {
                "dem_vertical_datum": "WGS84 ellipsoid",
                "transformation_applied": False,
            }
        }
        result = SWEEP.design_assessment(granule_records, dem_record)
        self.assertEqual(result["decision"], "NO-GO")
        self.assertTrue(any("absent" in b for b in result["blockers"]))

    def test_decision_conditional_when_dem_transform_needed(self):
        granule_records = [
            {
                "filename": "granule_001.h5",
                "access_error": None,
                "scalars": {
                    "science/LSAR/GCOV/metadata/orbit/orbitType": "MOE",
                    "science/LSAR/GCOV/metadata/attitude/attitudeType": "Custom",
                },
                "datasets": {
                    "science/LSAR/GCOV/metadata/radarGrid/xCoordinates": {"shape": [710]},
                    "science/LSAR/GCOV/metadata/radarGrid/yCoordinates": {"shape": [699]},
                },
            }
        ]
        dem_record = {
            "vertical_reference": {
                "dem_vertical_datum": "EGM2008 orthometric height",
                "transformation_applied": False,
                "required_model": "EGM2008 geoid-undulation grid",
            }
        }
        result = SWEEP.design_assessment(granule_records, dem_record)
        self.assertEqual(result["decision"], "CONDITIONAL GO")
        self.assertTrue(result["dem_transform_required"])

    def test_orbit_label_discrepancy_preserved(self):
        granule_records = [
            {
                "filename": "granule_001.h5",
                "access_error": None,
                "scalars": {
                    "science/LSAR/GCOV/metadata/orbit/orbitType": "MOE",
                    "science/LSAR/GCOV/metadata/attitude/attitudeType": "Custom",
                },
                "datasets": {
                    "science/LSAR/GCOV/metadata/radarGrid/xCoordinates": {"shape": [710]},
                    "science/LSAR/GCOV/metadata/radarGrid/yCoordinates": {"shape": [699]},
                },
            }
        ]
        dem_record = {
            "vertical_reference": {
                "dem_vertical_datum": "WGS84 ellipsoid",
                "transformation_applied": False,
            }
        }
        result = SWEEP.design_assessment(granule_records, dem_record)
        self.assertTrue(result["orbit_label_discrepancy_preserved"])
        self.assertTrue(result["pointing_label_discrepancy_preserved"])


class GeometryDatasetTests(unittest.TestCase):
    def test_geometry_dataset_list_is_complete(self):
        expected = [
            "science/LSAR/GCOV/metadata/radarGrid/incidenceAngle",
            "science/LSAR/GCOV/metadata/radarGrid/slantRange",
            "science/LSAR/GCOV/metadata/radarGrid/losUnitVectorX",
            "science/LSAR/GCOV/metadata/radarGrid/losUnitVectorY",
            "science/LSAR/GCOV/metadata/radarGrid/elevationAngle",
            "science/LSAR/GCOV/metadata/radarGrid/heightAboveEllipsoid",
        ]
        for path in expected:
            self.assertIn(path, SWEEP.GEOMETRY_DATASETS)


if __name__ == "__main__":
    unittest.main()
