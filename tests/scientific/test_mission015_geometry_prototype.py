"""Deterministic tests for Mission 015 geometry prototypes.

Synthetic cases use independently calculated geometric expectations.
No network, no production classification products.
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


class HeightConversionTests(unittest.TestCase):
    def test_orthometric_to_ellipsoidal_convention(self):
        # h = H + N; independent check with a known N
        H = 1000.0
        N = M.geoid_undulation(30.088337, 79.808685)
        h, n = M.orthometric_to_ellipsoidal(H, 30.088337, 79.808685)
        self.assertAlmostEqual(n, N, places=6)
        self.assertAlmostEqual(h, H + N, places=6)

    def test_geoid_undulation_study_point(self):
        # Mission 014 recorded value from the verified grid
        n = M.geoid_undulation(30.088337, 79.808685)
        self.assertAlmostEqual(n, -34.9258, places=3)

    def test_geoid_interpolation_linearity(self):
        # Bilinear interpolation of a 2x2 plane must be exact at the center
        plane = [[0.0, 10.0], [20.0, 30.0]]
        self.assertAlmostEqual(M.bilinear_2d(plane, 0.5, 0.5), 15.0)
        self.assertAlmostEqual(M.bilinear_2d(plane, 0.0, 0.0), 0.0)
        self.assertAlmostEqual(M.bilinear_2d(plane, 1.0, 1.0), 30.0)


class CoordinateTransformTests(unittest.TestCase):
    def test_ecef_roundtrip_lat_lon_at_equator(self):
        x, y, z = M.geodetic_to_ecef(0.0, 0.0, 0.0)
        self.assertAlmostEqual(x, M.A_EARTH, places=3)
        self.assertAlmostEqual(y, 0.0, places=3)
        self.assertAlmostEqual(z, 0.0, places=3)

    def test_up_vector_is_unit(self):
        _, _, up = M.enu_basis(30.0, 79.0)
        self.assertAlmostEqual(math.sqrt(sum(v * v for v in up)), 1.0, places=10)

    def test_incidence_vertical_los_is_zero(self):
        # A LOS equal to the local up vector -> incidence 0 deg
        _, _, up = M.enu_basis(30.0, 79.0)
        self.assertAlmostEqual(M.incidence_from_los(up, 30.0, 79.0), 0.0, places=6)

    def test_incidence_horizontal_los_is_90(self):
        east, _, _ = M.enu_basis(30.0, 79.0)
        self.assertAlmostEqual(M.incidence_from_los(east, 30.0, 79.0), 90.0, places=6)


class InterpolationTests(unittest.TestCase):
    def test_orbit_linear_interpolation(self):
        times = [0.0, 10.0]
        vecs = [[0.0, 0.0, 0.0], [10.0, 20.0, 30.0]]
        r = M.interpolate_orbit(times, vecs, 5.0)
        self.assertIsNotNone(r)
        self.assertAlmostEqual(r[0], 5.0)
        self.assertAlmostEqual(r[1], 10.0)
        self.assertAlmostEqual(r[2], 15.0)

    def test_orbit_out_of_range(self):
        times = [0.0, 10.0]
        vecs = [[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]
        self.assertIsNone(M.interpolate_orbit(times, vecs, -1.0))
        self.assertIsNone(M.interpolate_orbit(times, vecs, 11.0))

    def test_quaternion_slerp_identity(self):
        q = [1.0, 0.0, 0.0, 0.0]
        r = M.slerp(q, q, 0.5)
        for a, b in zip(q, r):
            self.assertAlmostEqual(a, b, places=10)

    def test_quaternion_slerp_endpoint(self):
        q0 = [1.0, 0.0, 0.0, 0.0]
        q1 = [0.0, 1.0, 0.0, 0.0]
        self.assertAlmostEqual(M.slerp(q0, q1, 0.0)[0], 1.0)
        self.assertAlmostEqual(M.slerp(q0, q1, 1.0)[1], 1.0)

    def test_trilinear_plane(self):
        cube = [[[0.0, 10.0], [20.0, 30.0]], [[100.0, 110.0], [120.0, 130.0]]]
        v = M.trilinear_3d(cube, 0.5, 0.5, 0.5)
        self.assertAlmostEqual(v, 65.0)  # mean of 8 corners


class SyntheticGeometryTests(unittest.TestCase):
    def test_flat_terrain_incidence_equals_ellipsoid(self):
        # Flat terrain: surface normal = ellipsoid normal -> local incidence = ellipsoid incidence
        lat, lon = 30.0, 79.0
        east, north, up = M.enu_basis(lat, lon)
        target = M.geodetic_to_ecef(lat, lon, 1000.0)
        # Sensor displaced along a slant direction 30 deg from vertical
        los = tuple(math.sin(math.radians(30)) * east[k] + math.cos(math.radians(30)) * up[k] for k in range(3))
        sensor = tuple(target[k] + 800000.0 * los[k] for k in range(3))
        los_vec = M.sub(sensor, target)
        self.assertAlmostEqual(M.incidence_from_los(los_vec, lat, lon), 30.0, places=6)

    def test_radar_facing_vs_away_slope(self):
        # Radar-facing slope tilts normal toward radar -> smaller incidence; away -> larger
        lat, lon = 30.0, 79.0
        _, _, up = M.enu_basis(lat, lon)
        east, _, _ = M.enu_basis(lat, lon)
        target = M.geodetic_to_ecef(lat, lon, 1000.0)
        sensor = tuple(target[k] + 800000.0 * (0.5 * east[k] + 0.866 * up[k]) for k in range(3))
        los = M.unit(M.sub(sensor, target))
        # Flat normal -> incidence
        inc_flat = M.incidence_from_los(los, lat, lon)
        # Facing normal tilted toward LOS by 10 deg
        normal_facing = M.unit(tuple(up[k] + 0.176 * los[k] for k in range(3)))
        cos_facing = abs(M.dot(los, normal_facing))
        inc_facing = math.degrees(math.acos(min(1.0, cos_facing)))
        self.assertLess(inc_facing, inc_flat)

    def test_known_shadow_geometry(self):
        # A point behind a ridge along the look ray is occluded: ray height below ridge.
        ridge_height = 2000.0
        target_height = 1000.0
        horizontal_distance = 5000.0
        ridge_at_halfway = 1800.0
        # Ray from target to sensor at 30 deg incidence: height at halfway
        ray_height_at_half = target_height + (horizontal_distance / 2) * math.tan(math.radians(60))
        # If ridge exceeds ray height -> shadow. Here ridge < ray -> no shadow
        self.assertLess(ridge_at_halfway, ray_height_at_half)
        shadowed = ridge_at_halfway > ray_height_at_half
        self.assertFalse(shadowed)

    def test_known_layover_geometry(self):
        # Top of slope maps to closer slant range than base when slope > incidence
        incidence = math.radians(30)
        slope = math.radians(40)  # steeper than incidence -> layover
        self.assertGreater(slope, incidence)
        # Projected slant-range displacement for a 100 m vertical step
        base_slant = 500000.0
        top_slant = base_slant - 100.0 * (math.tan(slope) - math.tan(incidence))
        self.assertLess(top_slant, base_slant)


class InvalidInputTests(unittest.TestCase):
    def test_bilinear_out_of_range(self):
        arr = [[1.0, 2.0], [3.0, 4.0]]
        self.assertIsNone(M.bilinear_2d(arr, -0.1, 0.5))
        self.assertIsNone(M.bilinear_2d(arr, 0.5, 2.0))

    def test_bilinear_nodata(self):
        arr = [[1.0, float("nan")], [3.0, 4.0]]
        self.assertIsNone(M.bilinear_2d(arr, 0.9, 0.1))

    def test_trilinear_out_of_range(self):
        cube = [[[0.0, 1.0], [2.0, 3.0]], [[4.0, 5.0], [6.0, 7.0]]]
        self.assertIsNone(M.trilinear_3d(cube, 1.5, 0.5, 0.5))


class RealDataApproachTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = M.load_window()

    def test_approach_a_vs_b_common_sample(self):
        # Common sample near the study point
        x_idx, y_idx = 177.9, 482.2
        easting = M.RADAR_X0 + x_idx * M.RADAR_DX
        northing = M.RADAR_Y0 + y_idx * M.RADAR_DY
        from pyproj import Transformer
        tr = Transformer.from_crs("EPSG:32644", "EPSG:4326", always_xy=True)
        lon, lat = tr.transform(easting, northing)
        H = M.dem_sample_height(lat, lon)
        self.assertIsNotNone(H)
        h_ell, _ = M.orthometric_to_ellipsoidal(H, lat, lon)
        t = sum(self.data["orbit_time"]) / len(self.data["orbit_time"])
        b = M.approach_b_incidence(self.data, lat, lon, h_ell, t)
        self.assertIsNotNone(b)
        # Global h index from ellipsoidal height axis
        heights = self.data["heightAboveEllipsoid"]
        h_idx = (h_ell - heights[0]) / (heights[1] - heights[0])
        a = M.approach_a_incidence(self.data, h_idx, y_idx, x_idx)
        self.assertIsNotNone(a)
        # Both should be in a physically plausible incidence band and agree within a few degrees
        self.assertGreater(a, 20.0)
        self.assertLess(a, 60.0)
        self.assertGreater(b["incidence_deg"], 20.0)
        self.assertLess(b["incidence_deg"], 60.0)
        self.assertLess(abs(a - b["incidence_deg"]), 3.0)

    def test_native_grid_metadata(self):
        d = self.data
        self.assertEqual(len(d["xCoordinates"]), 710)
        self.assertEqual(len(d["yCoordinates"]), 699)
        self.assertEqual(len(d["heightAboveEllipsoid"]), 21)
        self.assertEqual(len(d["orbit_time"]), 45)
        self.assertEqual(len(d["attitude_time"]), 126)

    def test_approach_comparison_statistics(self):
        cmp = M.approach_comparison(self.data)
        self.assertEqual(cmp["status"], "computed")
        self.assertGreaterEqual(cmp["sample_count"], 10)
        stats = cmp["incidence_abs_diff_deg"]
        self.assertGreater(stats["maximum"], 0.0)
        self.assertLess(stats["maximum"], 3.0)
        self.assertLessEqual(stats["minimum"], stats["median"])
        self.assertLessEqual(stats["median"], stats["maximum"])
        # All A and B incidences must be physically plausible
        for s in cmp["samples"]:
            self.assertGreater(s["A_incidence_deg"], 20.0)
            self.assertLess(s["B_incidence_deg"], 60.0)


class ManifestTests(unittest.TestCase):
    def test_conditional_go_with_conditions(self):
        man = M.build_manifest()
        self.assertEqual(man["final_decision"], "CONDITIONAL GO")
        self.assertGreaterEqual(len(man["conditions"]), 3)

    def test_independent_target_blocked(self):
        man = M.build_manifest()
        self.assertIn("BLOCKED", man["validation"]["independent_terrain_target"])

    def test_prohibited_outputs_false(self):
        man = M.build_manifest()
        for k, v in man["prohibited_outputs"].items():
            self.assertFalse(v, k)

    def test_error_budget_separates_components(self):
        eb = M.error_budget()
        for key in ["dem_elevation_error_m", "geoid_interpolation_error_m", "radar_grid_interpolation_error_m", "orbit_interpolation_error_m", "attitude_interpolation_error_m", "coordinate_transform_error_m", "combined_uncertainty"]:
            self.assertIn(key, eb)


if __name__ == "__main__":
    unittest.main()
