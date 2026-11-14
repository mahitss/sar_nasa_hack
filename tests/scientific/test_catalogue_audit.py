"""Unit tests for the CMR catalogue audit. No network and no satellite files."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "tools" / "catalogue_audit.py"
SPEC = importlib.util.spec_from_file_location("catalogue_audit", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)

SQUARE = ((0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0), (0.0, 0.0))


def record(**overrides):
    base = {
        "product_type": "GCOV",
        "collection_short_name": "NISAR_L2_GCOV_PROVISIONAL_V1",
        "orbit_direction": "DESCENDING",
        "track": 5,
        "frame": 73,
        "frequency_a_bandwidth_mhz": 40,
        "frequency_a_polarizations": ("HH", "HV"),
        "crid": "P05023",
        "contains_study_point": True,
        "acquisition_start": "2026-09-06T13:22:36.000000Z",
        "granule_ur": "GRANULE-A",
        "product_counter": 1,
        "revision_id": 1,
    }
    base.update(overrides)
    return base


class PointInPolygonTests(unittest.TestCase):
    def test_point_inside_polygon(self):
        self.assertTrue(audit.point_in_ring(1.0, 1.0, SQUARE))

    def test_point_outside_polygon(self):
        self.assertFalse(audit.point_in_ring(3.0, 1.0, SQUARE))

    def test_point_on_edge_counts_as_inside(self):
        self.assertTrue(audit.point_in_ring(1.0, 0.0, SQUARE))

    def test_point_on_vertex_counts_as_inside(self):
        self.assertTrue(audit.point_in_ring(0.0, 0.0, SQUARE))

    def test_point_just_outside_edge_is_outside(self):
        self.assertFalse(audit.point_in_ring(-0.01, 1.0, SQUARE))


class ComparabilityTests(unittest.TestCase):
    def test_different_crid_is_rejected(self):
        reasons = audit.incompatibility_reasons(record(), record(crid="P05036"))
        self.assertIn("different_crid", reasons)
        self.assertNotEqual(
            audit.comparability_key(record()),
            audit.comparability_key(record(crid="P05036")),
        )

    def test_different_bandwidth_is_rejected(self):
        reasons = audit.incompatibility_reasons(
            record(),
            record(frequency_a_bandwidth_mhz=20),
        )
        self.assertIn("different_bandwidth", reasons)

    def test_different_polarization_is_rejected(self):
        reasons = audit.incompatibility_reasons(
            record(),
            record(frequency_a_polarizations=("HH", "HV", "VH", "VV")),
        )
        self.assertIn("different_polarization", reasons)

    def test_different_orbit_is_rejected(self):
        reasons = audit.incompatibility_reasons(
            record(),
            record(orbit_direction="ASCENDING", track=127, frame=17),
        )
        self.assertIn("different_orbit", reasons)

    def test_matching_mode_has_no_incompatibility(self):
        self.assertEqual(audit.incompatibility_reasons(record(), record(granule_ur="B")), [])


class DuplicateTests(unittest.TestCase):
    def test_repeated_granule_ur_is_detected(self):
        duplicates = audit.find_duplicates([record(), record()])
        self.assertTrue(any(item["kind"] == "repeated_granule_ur" for item in duplicates))

    def test_two_versions_of_one_acquisition_are_detected(self):
        first = record(granule_ur="GRANULE-001", product_counter=1)
        second = record(granule_ur="GRANULE-002", product_counter=2)
        duplicates = audit.find_duplicates([first, second])
        versions = [
            item
            for item in duplicates
            if item["kind"] == "multiple_versions_of_one_acquisition"
        ]
        self.assertEqual(len(versions), 1)
        self.assertEqual(
            versions[0]["granule_urs"],
            ["GRANULE-001", "GRANULE-002"],
        )
        self.assertEqual(audit.prefer_version([first, second])["granule_ur"], "GRANULE-002")


class ManifestBehaviorTests(unittest.TestCase):
    def test_pagination_stops_at_the_reported_hit_count(self):
        pages = {
            1: [{"umm": {}, "meta": {}}],
            2: [{"umm": {}, "meta": {}}],
        }

        def opener(request, timeout):
            page_num = int(request.full_url.rsplit("page_num=", 1)[1])
            body = {"items": pages.get(page_num, [])}

            class Response:
                headers = {"CMR-Hits": "2"}

                def read(self):
                    return json.dumps(body).encode("utf-8")

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return False

            return Response()

        fetched = audit.fetch_collection("NISAR_L2_GCOV_PROVISIONAL_V1", opener)
        self.assertEqual(fetched["hits"], 2)
        self.assertEqual(len(fetched["items"]), 2)
        self.assertEqual([page["page_num"] for page in fetched["pages"]], [1, 2])

    def test_signed_download_query_is_removed(self):
        cleaned = audit.sanitize_url(
            "https://data.example.test/file.h5?X-Amz-Signature=secret&X-Amz-Credential=hidden"
        )
        self.assertEqual(cleaned["url"], "https://data.example.test/file.h5")
        self.assertTrue(cleaned["signed_query_removed"])
        self.assertIsNone(audit.sanitize_url("s3://bucket/file.h5"))

    def test_latest_pair_is_ranked_first(self):
        older = record(
            granule_ur="OLDER",
            acquisition_start="2026-07-20T13:22:38.000000Z",
        )
        middle = record(
            granule_ur="MIDDLE",
            acquisition_start="2026-09-06T13:22:36.000000Z",
        )
        newer = record(
            granule_ur="NEWER",
            acquisition_start="2026-09-30T13:22:36.000000Z",
        )
        pairs = audit.rank_pairs([older, newer, middle])
        self.assertEqual(pairs[0]["rank"], 1)
        self.assertEqual(pairs[0]["earlier_granule_ur"], "MIDDLE")
        self.assertEqual(pairs[0]["later_granule_ur"], "NEWER")
        self.assertTrue(all(pair["status"] == "pending_raster_quality_control" for pair in pairs))


if __name__ == "__main__":
    unittest.main()
