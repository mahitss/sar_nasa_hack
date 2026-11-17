"""Mission 015.1 deterministic tests for the corrected geometry prototype.

Synthetic expectations are calculated independently; no network calls; no
production classification products.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load():
    p = ROOT / "tools" / "mission015_geometry_prototype.py"
    spec = importlib.util.spec_from_file_location("m15", p)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["m15"] = mod
    spec.loader.exec_module(mod)
    return mod


M = load()


import unittest


# ---------------------------------------------------------------------------
# Section 6: strict interpolation boundary behaviour
# ---------------------------------------------------------------------------

class InterpolationBoundaryTests(unittest.TestCase):
    def test_bilinear_exact_boundaries_allowed(self):
        arr = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
        self.assertEqual(M.bilinear_2d(arr, 0.0, 0.0), 1.0)   # top-left center
        self.assertEqual(M.bilinear_2d(arr, 2.0, 1.0), 6.0)   # bottom-right center

    def test_bilinear_just_inside_and_outside(self):
        arr = [[0.0, 10.0], [20.0, 30.0]]
        self.assertIsNotNone(M.bilinear_2d(arr, 0.999, 0.999))
        self.assertIsNotNone(M.bilinear_2d(arr, 0.001, 0.001))
        self.assertIsNone(M.bilinear_2d(arr, -1e-6, 0.5))   # just outside left
        self.assertIsNone(M.bilinear_2d(arr, 2.0001, 0.5))  # just outside right
        self.assertIsNone(M.bilinear_2d(arr, 0.5, -1e-6))   # just outside top
        self.assertIsNone(M.bilinear_2d(arr, 0.5, 1.5))     # just outside bottom

    def test_bilinear_rejects_nan_inf_nodata(self):
        arr = [[1.0, float("nan")], [3.0, 4.0]]
        self.assertIsNone(M.bilinear_2d(arr, 0.9, 0.1))
        self.assertIsNone(M.bilinear_2d(arr, float("nan"), 0.5))
        self.assertIsNone(M.bilinear_2d(arr, float("inf"), 0.5))
        self.assertIsNone(M.bilinear_2d([[1.0, None], [3.0, 4.0]], 0.9, 0.1))

    def test_trilinear_boundaries_and_just_outside(self):
        cube = [[[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]],
                [[6.0, 7.0, 8.0], [9.0, 10.0, 11.0]]]
        self.assertEqual(M.trilinear_3d(cube, 0.0, 0.0, 0.0), 0.0)
        self.assertEqual(M.trilinear_3d(cube, 1.0, 1.0, 2.0), 11.0)
        self.assertIsNotNone(M.trilinear_3d(cube, 0.999, 0.5, 1.5))
        self.assertIsNone(M.trilinear_3d(cube, -1e-6, 0.5, 0.5))
        self.assertIsNone(M.trilinear_3d(cube, 1.5, 0.5, 0.5))
        self.assertIsNone(M.trilinear_3d(cube, 0.5, 0.5, 2.5))

    def test_axis_validation(self):
        self.assertEqual(len(M.validate_axis([0.0, 500.0, 1000.0], "x")), 3)
        with self.assertRaises(ValueError):
            M.validate_axis([0.0, 500.0, 500.0], "x")  # duplicate
        with self.assertRaises(ValueError):
            M.validate_axis([0.0, 500.0, 100.0], "x")  # non-monotonic
        with self.assertRaises(ValueError):
            M.validate_axis([0.0, float("nan")], "x")  # non-finite

    def test_axis_index_out_of_range(self):
        axis = [0.0, 500.0, 1000.0]
        self.assertEqual(M.axis_index(axis, 500.0, "x"), 1.0)
        self.assertIsNone(M.axis_index(axis, -1.0, "x"))
        self.assertIsNone(M.axis_index(axis, 1001.0, "x"))


# ---------------------------------------------------------------------------
# Height conversion, geoid, coordinate transforms
# ---------------------------------------------------------------------------

class HeightAndFrameTests(unittest.TestCase):
    def test_height_convention(self):
        H = 1000.0
        N = M.geoid_undulation(30.088337, 79.808685)
        h, n = M.orthometric_to_ellipsoidal(H, 30.088337, 79.808685)
        self.assertEqual(n, N)
        self.assertAlmostEqual(h, H + N, places=9)

    def test_geoid_study_point(self):
        self.assertAlmostEqual(M.geoid_undulation(30.088337, 79.808685), -34.9258, places=3)

    def test_geoid_bilinear_plane(self):
        # bilinear of a linear field is exact at the center
        plane = [[0.0, 10.0], [20.0, 30.0]]
        self.assertAlmostEqual(M.bilinear_2d(plane, 0.5, 0.5), 15.0)

    def test_ecef_and_incidence(self):
        x, y, z = M.geodetic_to_ecef(0.0, 0.0, 0.0)
        self.assertAlmostEqual(x, M.A_EARTH, places=3)
        _, _, up = M.enu_basis(30.0, 79.0)
        self.assertAlmostEqual(M.incidence_from_los(up, 30.0, 79.0), 0.0, places=6)
        east, _, _ = M.enu_basis(30.0, 79.0)
        self.assertAlmostEqual(M.incidence_from_los(east, 30.0, 79.0), 90.0, places=6)

    def test_frame_reversal_changes_los_components(self):
        # Same LOS expressed in two different local frames must differ in ENU
        lat, lon = 30.0, 79.0
        los = M.unit(M.geodetic_to_ecef(lat + 0.1, lon + 0.1, 1500.0))
        enu_a = M.ecef_to_enu(los, lat, lon)
        enu_b = M.ecef_to_enu(los, -lat, lon)  # reversed target latitude
        self.assertGreater(M.angle_between(enu_a, enu_b), 1.0)


# ---------------------------------------------------------------------------
# Orbit and quaternion
# ---------------------------------------------------------------------------

class OrbitAttitudeTests(unittest.TestCase):
    def test_orbit_linear_and_out_of_range(self):
        self.assertEqual(M.interpolate_orbit([0.0, 10.0], [[0, 0, 0], [10, 20, 30]], 5.0), (5.0, 10.0, 15.0))
        self.assertIsNone(M.interpolate_orbit([0.0, 10.0], [[0, 0, 0], [1, 1, 1]], -1.0))
        self.assertIsNone(M.interpolate_orbit([0.0, 10.0], [[0, 0, 0], [1, 1, 1]], 11.0))

    def test_quaternion_normalization_and_endpoints(self):
        q = [2.0, 0.0, 0.0, 0.0]
        self.assertAlmostEqual(M.quat_norm(M.quat_normalize(q)), 1.0, places=12)
        q0, q1 = [1.0, 0, 0, 0], [0.0, 1.0, 0, 0]
        self.assertAlmostEqual(M.slerp(q0, q1, 0.0)[0], 1.0, places=9)
        self.assertAlmostEqual(M.slerp(q0, q1, 1.0)[1], 1.0, places=9)

    def test_quaternion_sign_equivalence(self):
        q = [1.0, 0.0, 0.0, 0.0]
        r1 = M.quat_rotate(q, (1.0, 0.0, 0.0))
        r2 = M.quat_rotate([-v for v in q], (1.0, 0.0, 0.0))
        for a, b in zip(r1, r2):
            self.assertAlmostEqual(a, b, places=9)

    def test_quaternion_90deg_frame_transform(self):
        # 90 deg about Z maps X -> Y
        q = [math.cos(math.radians(45)), 0, 0, math.sin(math.radians(45))]
        r = M.quat_rotate(q, (1.0, 0.0, 0.0))
        self.assertAlmostEqual(r[0], 0.0, places=9)
        self.assertAlmostEqual(r[1], 1.0, places=9)

    def test_attitude_not_applied_to_los(self):
        self.assertIn("NOT rotated by attitude", M.ATTITUDE_NOTE)
        self.assertIn("ORBIT zero-Doppler", M.ATTITUDE_NOTE)


# ---------------------------------------------------------------------------
# Zero-Doppler correction (target-specific, velocity incorporated)
# ---------------------------------------------------------------------------

class ZeroDopplerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = M.load_window("20260906")

    def test_target_specific_times_not_mean(self):
        data = self.data
        times = []
        for xi, yi in [(171, 485), (177, 479), (181, 483)]:
            from pyproj import Transformer
            tr = Transformer.from_crs("EPSG:32644", "EPSG:4326", always_xy=True)
            lon, lat = tr.transform(296250 + xi * 500, 3570250 + yi * -500)
            H = M.dem_sample_height(lat, lon)
            h_ell, _ = M.orthometric_to_ellipsoidal(H, lat, lon)
            b = M.approach_b_fields(data, lat, lon, h_ell)
            self.assertIsNotNone(b)
            times.append(b["zd"]["acquisition_time_s"])
        mean_epoch = sum(data["orbit_time"]) / len(data["orbit_time"])
        # target times must differ from one another and from the mean epoch
        self.assertGreater(max(times) - min(times), 0.05)
        self.assertTrue(all(abs(t - mean_epoch) > 1.0 for t in times))

    def test_velocity_and_residual(self):
        from pyproj import Transformer
        tr = Transformer.from_crs("EPSG:32644", "EPSG:4326", always_xy=True)
        lon, lat = tr.transform(296250 + 177 * 500, 3570250 + 482 * -500)
        H = M.dem_sample_height(lat, lon)
        h_ell, _ = M.orthometric_to_ellipsoidal(H, lat, lon)
        b = M.approach_b_fields(self.data, lat, lon, h_ell)
        self.assertIsNotNone(b)
        self.assertIsNotNone(b["zd"]["velocity_ecef"])
        self.assertTrue(b["zd"]["converged"])
        self.assertLess(abs(b["zd"]["zero_doppler_residual_mps"]), 1e-6)

    def test_out_of_range_failure_recorded(self):
        # target far outside orbit span -> no bracket / out-of-range failure, not a mean fallback
        bad = dict(self.data)
        bad["orbit_time"] = [48187.0, 48188.0]
        bad["orbit_position"] = self.data["orbit_position"][:2]
        bad["orbit_velocity"] = self.data["orbit_velocity"][:2]
        res = M.solve_zero_doppler((1e7, 1e7, 1e7), bad)
        self.assertFalse(res["converged"])
        self.assertIsNotNone(res["failure"])


# ---------------------------------------------------------------------------
# Synthetic shadow/layover with ACTUAL prototype functions
# ---------------------------------------------------------------------------

class SyntheticGeometryTests(unittest.TestCase):
    def test_shadow_negative_and_positive(self):
        # Use actual prototype function ray_clear with a real target geometry
        lat, lon = 30.0881, 79.8087
        h = 1741.1
        target = M.geodetic_to_ecef(lat, lon, h)
        los = M.unit(M.sub(M.interpolate_orbit(M.load_window("20260906")["orbit_time"],
                                               M.load_window("20260906")["orbit_position"], 48187.6), target))
        los_enu = M.ecef_to_enu(los, lat, lon)
        inc = M.incidence_from_los(los, lat, lon)
        target_enu = (0.0, 0.0, 0.0)
        # ridge below the ray -> clear (no shadow)
        low_ridge = 100.0
        self.assertTrue(M.ray_clear(target_enu, los_enu, 3000.0, low_ridge, inc))
        # ridge intersecting the ray -> shadow (ray_clear False)
        high_ridge = 1e7
        self.assertFalse(M.ray_clear(target_enu, los_enu, 3000.0, high_ridge, inc))

    def test_layover_below_and_exceeding(self):
        self.assertFalse(M.layover_condition(30.0, 40.0))  # slope < incidence
        self.assertTrue(M.layover_condition(45.0, 40.0))   # slope > incidence

    def test_slant_range_ordering(self):
        self.assertTrue(M.slant_range_ordering(900000.0, 905000.0))
        self.assertFalse(M.slant_range_ordering(905000.0, 900000.0))


# ---------------------------------------------------------------------------
# Real-data reproducibility and manifest
# ---------------------------------------------------------------------------

class RealDataTests(unittest.TestCase):
    def test_17_sample_reproducible(self):
        a = M.approach_comparison("20260906")
        b = M.approach_comparison("20260906")
        self.assertEqual(a["status"], "computed")
        self.assertEqual(a["sample_count"], 17)
        self.assertEqual(a["samples"], b["samples"])

    def test_zero_doppler_matches_product_time(self):
        c = M.approach_comparison("20260906")
        self.assertIsNotNone(c["acquisition_time_abs_diff_s"])
        self.assertLess(c["acquisition_time_abs_diff_s"]["max"], 0.01)

    def test_20260930_attempt_recorded(self):
        man = M.build_manifest()
        self.assertIn(man["granule_20260930_access"]["status"], ("success", "failed"))

    def test_numerical_interpolation_error_measured(self):
        d = M.load_window("20260906")
        err = M.withheld_node_error(d["incidenceAngle"])
        self.assertEqual(err["status"], "measured")
        self.assertGreater(err["sample_count"], 0)
        self.assertGreaterEqual(err["max_abs_error"], 0.0)
        self.assertIn("not physical 30 m accuracy", err["interpretation"])

    def test_manifest_fields(self):
        man = M.build_manifest()
        self.assertEqual(man["final_decision"], "CONDITIONAL GO")
        self.assertFalse(man["axis_verification"]["spacing_hardcoded"])
        self.assertIn("NOT independent", man["independence_note"])
        self.assertIn("NOT REPORTED", man["error_budget"]["combined_uncertainty"])
        self.assertIn("BLOCKED", man["validation"]["independent_terrain_target"])
        for k, v in man["prohibited_outputs"].items():
            self.assertFalse(v, k)


if __name__ == "__main__":
    unittest.main()
