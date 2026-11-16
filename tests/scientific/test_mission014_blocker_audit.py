"""Deterministic tests for Mission 014 blocker audit. No network calls."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load():
    path = ROOT / "tools" / "mission014_blocker_audit.py"
    spec = importlib.util.spec_from_file_location("mission014_blocker_audit", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["mission014_blocker_audit"] = module
    spec.loader.exec_module(module)
    return module


AUDIT = load()


class DecisionTests:
    pass


import unittest


class DecisionTests(unittest.TestCase):
    def test_final_decision_is_conditional_go(self):
        self.assertEqual(AUDIT.build_manifest()["final_decision"], "CONDITIONAL GO")

    def test_named_conditions_present(self):
        conditions = AUDIT.build_manifest()["conditions"]
        self.assertGreaterEqual(len(conditions), 3)
        joined = " ".join(conditions).lower()
        self.assertIn("dem", joined)
        self.assertIn("interpolation", joined)
        self.assertIn("validation", joined)


class AuthenticationTests(unittest.TestCase):
    def test_auth_contradiction_resolved(self):
        a = AUDIT.AUTH_RECORD
        self.assertIn("earthaccess", a["mission012_method"])
        self.assertTrue(a["both_granules_read"])
        self.assertTrue(a["probe_hdf5_signature_valid"])
        self.assertEqual(a["mission013_failure_status"], 401)
        self.assertEqual(a["probe_status_after_fix"], 206)
        self.assertFalse(a["credentials_exposed"])
        self.assertFalse(a["netrc_modified"])
        self.assertFalse(a["complete_hdf5_downloaded"])

    def test_resolution_explains_netrc_handling(self):
        self.assertIn("NETRC", AUDIT.AUTH_RECORD["resolution"])


class EGM2008Tests(unittest.TestCase):
    def test_sign_convention_matches_mission(self):
        e = AUDIT.EGM2008_RECORD
        self.assertTrue(e["sign_matches_mission"])
        self.assertIn("h = H + N", e["sign_convention"])

    def test_checksum_recorded(self):
        self.assertEqual(len(AUDIT.EGM2008_RECORD["distribution_sha256"]), 64)

    def test_grid_metadata(self):
        e = AUDIT.EGM2008_RECORD
        self.assertEqual(e["grid_dimensions"], [8640, 4321])
        self.assertEqual(e["posting_arcmin"], 2.5)
        self.assertEqual(e["reference_ellipsoid"], "WGS84")
        self.assertTrue(e["bounded_subset_feasible"])

    def test_computed_undulation_present(self):
        u = AUDIT.EGM2008_RECORD["computed_undulation_m"]
        self.assertIn("study_point_30.088337N_79.808685E", u)
        self.assertLess(u["study_point_30.088337N_79.808685E"], 0)  # negative over India

    def test_interpolation_errors_documented(self):
        e = AUDIT.EGM2008_RECORD
        self.assertLess(e["cubic_error_max_m"], e["bilinear_error_max_m"])


class DEMIdentityTests(unittest.TestCase):
    def test_release_not_falsely_claimed(self):
        d = AUDIT.DEM_IDENTITY_RECORD
        self.assertTrue(d["same_product_family"])
        self.assertFalse(d["local_release_explicitly_recorded"])
        self.assertFalse(d["byte_identity_verified"])

    def test_vertical_datum_difference_recorded(self):
        self.assertIn("EGM2008", AUDIT.DEM_IDENTITY_RECORD["vertical_datum_difference"])


class ResolutionTests(unittest.TestCase):
    def test_both_approaches_present(self):
        r = AUDIT.RESOLUTION_RECORD
        self.assertIn("approach_A", r)
        self.assertIn("approach_B", r)
        self.assertEqual(r["radar_grid_posting_m"], 500)
        self.assertEqual(r["gcov_image_posting_m"], 10)

    def test_no_10m_promise(self):
        self.assertIn("NOT justified", AUDIT.RESOLUTION_RECORD["conclusion"])


class DiscrepancyTests(unittest.TestCase):
    def test_labels_preserved_not_rewritten(self):
        d = AUDIT.DISCREPANCY_RECORD
        self.assertFalse(d["orbit"]["resolved"])
        self.assertTrue(d["orbit"]["values_preserved"])
        self.assertFalse(d["orbit"]["geolocation_error_inferred"])
        self.assertTrue(d["physical_geometry_reconstructable"])


class ValidationTests(unittest.TestCase):
    def test_synthetic_cases_complete(self):
        cases = " ".join(t["case"] for t in AUDIT.VALIDATION_RECORD["synthetic_tests"])
        for key in ("flat", "radar-facing", "radar-away", "shadow", "layover"):
            self.assertIn(key, cases)

    def test_mission006_candidates_excluded(self):
        principles = " ".join(AUDIT.VALIDATION_RECORD["principles"])
        self.assertIn("NOT used", principles)


class ProhibitedOutputTests(unittest.TestCase):
    def test_all_prohibited_outputs_false(self):
        for key, value in AUDIT.PROHIBITED.items():
            self.assertFalse(value, key)


if __name__ == "__main__":
    unittest.main()
