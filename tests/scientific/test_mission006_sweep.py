"""Mission 006 sweep tests. They use synthetic arrays, not the Kuwari crops."""

from __future__ import annotations

import importlib.util
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


SWEEP = load("mission006_sweep", "mission006_sweep.py")
SCREEN = load("water_candidate", "water_candidate.py")

try:
    import numpy as np
except ModuleNotFoundError:
    np = None


class DomainTests(unittest.TestCase):
    def test_domain_has_1092_sets_and_ratio_gate_off(self):
        domain = SWEEP.parameter_domain()
        self.assertEqual(len(domain), 1092)
        self.assertEqual(SWEEP.TOTAL_SETS, 1092)
        self.assertTrue(all(item["max_hv_over_hh"] is None for item in domain))
        self.assertEqual(domain[0]["hh_db"], -22)
        self.assertEqual(domain[0]["hv_db"], -28)
        self.assertEqual(domain[0]["min_looks"], 0.0)
        self.assertEqual(domain[0]["min_patch_pixels"], 1)
        self.assertEqual(domain[-1]["hh_db"], -10)
        self.assertEqual(domain[-1]["hv_db"], -15)
        self.assertEqual(domain[-1]["min_looks"], 2.0)
        self.assertEqual(domain[-1]["min_patch_pixels"], 9)
        self.assertAlmostEqual(domain[0]["hh_max_linear"], 10 ** (-22 / 10))

    def test_domain_digest_is_stable(self):
        self.assertEqual(SWEEP.domain_digest(), SWEEP.domain_digest(SWEEP.parameter_domain()))
        self.assertEqual(len(SWEEP.domain_digest()), 64)


class StabilityCodeTests(unittest.TestCase):
    def test_full_stability_requires_validity_in_every_set(self):
        self.assertEqual(SWEEP.stability_code(1092, 1092, 1092), 2)
        self.assertEqual(SWEEP.stability_code(10, 10, 1092), 1)
        self.assertEqual(SWEEP.stability_code(10, 4, 1092), 0)
        self.assertEqual(SWEEP.stability_code(10, 0, 1092), -1)
        self.assertEqual(SWEEP.stability_code(0, 0, 1092), -2)
        self.assertEqual(SWEEP.validity_code(1092, 1092), 1)
        self.assertEqual(SWEEP.validity_code(3, 1092), 0)
        self.assertEqual(SWEEP.validity_code(0, 1092), -1)


@unittest.skipUnless(np is not None, "numpy is required for the sweep equivalence checks")
class ComponentEquivalenceTests(unittest.TestCase):
    def test_diagonal_pixels_are_not_one_component(self):
        raw = np.zeros((3, 3), dtype=bool)
        raw[0, 0] = True
        raw[1, 1] = True
        kept = SWEEP.keep_large_components(raw, 2)
        self.assertFalse(kept.any())

    def test_vertical_pair_survives_and_exact_size_is_kept(self):
        raw = np.zeros((3, 3), dtype=bool)
        raw[0, 0] = True
        raw[1, 0] = True
        kept = SWEEP.keep_large_components(raw, 2)
        self.assertEqual(int(kept.sum()), 2)
        self.assertTrue(bool(kept[0, 0] and kept[1, 0]))
        block = np.zeros((3, 3), dtype=bool)
        block[0:2, 0:2] = True
        self.assertEqual(int(SWEEP.keep_large_components(block, 4).sum()), 4)
        self.assertEqual(int(SWEEP.keep_large_components(block, 5).sum()), 0)

    def test_sweep_matches_sensitivity_and_repeats(self):
        hh = np.full((5, 5), 0.4)
        hv = np.full((5, 5), 0.08)
        looks = np.full((5, 5), 3.0)
        mask = np.ones((5, 5), dtype=np.int16)
        hh[0, 0] = 0.01
        hv[0, 0] = 0.002
        hh[0, 1] = 0.01
        hv[0, 1] = 0.002
        hh[1, 0] = 0.01
        hv[1, 0] = 0.002
        hh[4, 4] = 0.01
        hv[4, 4] = 0.002
        looks[2, 2] = 0.0
        looks[2, 3] = 0.4
        looks[3, 3] = math.nan
        mask[4, 0] = 0
        mask[4, 1] = 255
        hh_limits = [0.05, 0.2]
        hv_limits = [0.02, 0.2]
        floors = [0.0, 2.0]
        patches = [1, 4, 9]
        parameters = []
        for hh_limit in hh_limits:
            for hv_limit in hv_limits:
                for floor in floors:
                    for patch in patches:
                        parameters.append(SCREEN.CandidateParameters(hh_limit, hv_limit, floor, patch))
        reference = SCREEN.sensitivity(hh.tolist(), hv.tolist(), looks.tolist(), mask.tolist(), parameters)
        valid, raw, filtered = SWEEP.sweep_counts(hh, hv, looks, mask, hh_limits, hv_limits, floors, patches)
        self.assertEqual(reference.total_sets, 24)
        self.assertTrue(np.array_equal(valid, reference.valid_count))
        self.assertTrue(np.array_equal(raw, reference.raw_candidate_count))
        self.assertTrue(np.array_equal(filtered, reference.filtered_candidate_count))
        self.assertTrue(np.all(raw <= valid))
        self.assertTrue(np.all(filtered <= raw))
        again = SWEEP.sweep_counts(hh, hv, looks, mask, hh_limits, hv_limits, floors, patches)
        self.assertTrue(np.array_equal(valid, again[0]))
        self.assertTrue(np.array_equal(raw, again[1]))
        self.assertTrue(np.array_equal(filtered, again[2]))
        self.assertEqual(int(valid[2, 2]), 0)
        self.assertGreater(int(valid[2, 3]), 0)
        self.assertLess(int(valid[2, 3]), 24)


if __name__ == "__main__":
    unittest.main()
