"""Synthetic tests for Mission 011. They do not download DEM or NISAR files."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "tools" / "mission011_acquisition.py"
SPEC = importlib.util.spec_from_file_location("mission011_acquisition", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
acquisition = importlib.util.module_from_spec(SPEC)
sys.modules["mission011_acquisition"] = acquisition
SPEC.loader.exec_module(acquisition)

SEP6 = "NISAR_L2_PR_GCOV_030_005_D_073_4005_DHDH_A_20260906T132236_20260906T132311_P05023_N_F_J_001.h5"


class FilenameTests(unittest.TestCase):
    def test_accuracy_n_expects_noe_and_nrp_separately_from_coverage(self):
        parsed = acquisition.parse_gcov_filename(SEP6)
        self.assertEqual(parsed["accuracy"], "N")
        self.assertEqual(parsed["expected_orbit_ephemeris"], "NOE")
        self.assertEqual(parsed["expected_radar_pointing"], "NRP")
        self.assertEqual(parsed["coverage"], "F")
        self.assertTrue(parsed["coverage_is_not_pointing"])
        self.assertEqual(len(SEP6[:-3].split("_")), 18)

    def test_moe_against_noe_stays_an_unresolved_mismatch(self):
        result = acquisition.compare_orbit_and_pointing(SEP6, "MOE", "NRP")
        self.assertEqual(result["orbit_consistency"], "mismatch")
        self.assertEqual(result["pointing_consistency"], "match")
        self.assertFalse(result["resolved"])
        self.assertFalse(result["geolocation_error_inferred"])


class DemTests(unittest.TestCase):
    def test_buffered_window_needs_the_two_named_geocells(self):
        self.assertEqual(acquisition.buffered_window_geocells(), list(acquisition.GEOCELLS))
        self.assertTrue(acquisition.geocell_covers_bbox(29, 79, [79.70, 29.98, 79.92, 30.0]))
        self.assertTrue(acquisition.geocell_covers_bbox(30, 79, [79.70, 30.0, 79.92, 30.20]))
        self.assertFalse(acquisition.geocell_covers_bbox(30, 79, acquisition.BUFFERED_BBOX))

    def test_missing_file_is_reported_without_a_checksum(self):
        record = acquisition.file_record(Path(tempfile.gettempdir()) / "rivet-missing-dem.tif")
        self.assertFalse(record["present"])
        self.assertIsNone(record["sha256"])

    def test_checksum_matches_the_bytes_on_disk(self):
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            handle.write(b"dem")
            name = handle.name
        record = acquisition.file_record(Path(name))
        self.assertEqual(record["bytes"], 3)
        self.assertEqual(record["sha256"], hashlib.sha256(b"dem").hexdigest())
        Path(name).unlink()


class BoundaryTests(unittest.TestCase):
    def test_vertical_reference_is_recorded_and_not_applied(self):
        note = acquisition.vertical_reference_note()
        self.assertFalse(note["transformation_applied"])
        self.assertIn("EGM2008", note["dem_vertical_datum"])
        self.assertIn("ellipsoid", note["radar_grid_height"])
        self.assertTrue(note["horizontal_crs_is_not_a_vertical_datum"])

    def test_prohibited_outputs_stay_false(self):
        flags = acquisition.prohibited_outputs()
        self.assertTrue(flags)
        self.assertFalse(any(flags.values()))


if __name__ == "__main__":
    unittest.main()
