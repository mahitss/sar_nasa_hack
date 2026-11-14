"""Synthetic tests for Mission 012 access rules. They do not contact Earthdata."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "tools" / "mission012_nisar_access.py"
SPEC = importlib.util.spec_from_file_location("mission012_nisar_access", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
access = importlib.util.module_from_spec(SPEC)
sys.modules["mission012_nisar_access"] = access
SPEC.loader.exec_module(access)

SEP6 = "NISAR_L2_PR_GCOV_030_005_D_073_4005_DHDH_A_20260906T132236_20260906T132311_P05023_N_F_J_001.h5"


class ProbeTests(unittest.TestCase):
    def test_hdf5_signature_and_user_block_offset(self):
        blob = b"\x00" * 16 + access.HDF5_SIGNATURE + b"rest"
        self.assertEqual(access.hdf5_signature_offset(blob), 16)
        self.assertIsNone(access.hdf5_signature_offset(b'{"error":"login"}'))
        self.assertIsNone(access.hdf5_signature_offset(b"<html>login</html>"))

    def test_partial_response_accepts_only_a_206_with_a_signature(self):
        body = access.HDF5_SIGNATURE + b"\x00" * 8
        accepted = access.classify_probe(206, "application/octet-stream", body, "bytes 0-15/100")
        self.assertEqual(accepted["action"], "accept")
        self.assertTrue(accepted["hdf5_signature"])
        rejected = access.classify_probe(206, "application/json", b'{"login":true}', "bytes 0-15/100")
        self.assertEqual(rejected["action"], "reject")
        early = access.classify_probe(200, "application/x-hdf5", body, None)
        self.assertEqual(early["action"], "close_without_reading_body")

    def test_redirects_and_signed_queries_are_redacted(self):
        summary = access.redirect_summary([(302, "https://urs.earthdata.nasa.gov/oauth?token=secret&client_id=abc")])
        self.assertEqual(summary[0]["host"], "urs.earthdata.nasa.gov")
        self.assertTrue(summary[0]["query_removed"])
        self.assertNotIn("token", str(summary))
        cleaned = access.redact_url("https://example.test/file.h5?X-Amz-Signature=abc&file=a")
        self.assertNotIn("abc", cleaned)
        self.assertIn("file=a", cleaned)


class RecordTests(unittest.TestCase):
    def test_orbit_and_pointing_are_compared_independently(self):
        result = access.consistency(SEP6, "MOE", "NRP")
        self.assertEqual(result["orbit_consistency"], "mismatch")
        self.assertEqual(result["pointing_consistency"], "match")
        self.assertEqual(result["expected_orbit_ephemeris"], "NOE")
        unread = access.consistency(SEP6, None, None)
        self.assertEqual(unread["orbit_consistency"], "not_read")
        self.assertEqual(unread["pointing_consistency"], "not_read")
        self.assertFalse(unread["geolocation_error_inferred"])

    def test_budget_and_prohibited_outputs(self):
        access.enforce_budget(10, 10, limit=20)
        with self.assertRaises(RuntimeError):
            access.enforce_budget(10, 11, limit=20)
        flags = access.prohibited_outputs()
        self.assertFalse(any(flags.values()))
        self.assertIn("complete_hdf5_downloaded", flags)
