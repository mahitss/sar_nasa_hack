# Mission 015 — Geometry Model Prototype & Numerical Validation

**Final Decision: CONDITIONAL GO**

Numerical feasibility of NISAR radar geometry reconstruction at ~30 m is demonstrated: two independent approaches agree within a median 0.618° incidence angle across 17 real common samples. A **limited diagnostic geometry implementation** is justified with a documented error budget, but specific conditions remain — most importantly, no independent non-candidate real terrain validation target was selected (BLOCKED).

## 1. Repository State — Preserved

- Branch `main`, HEAD `a509f78`, tracking `origin/main`; no unexpected modifications.
- All Mission 013 and 014 deliverables located, manifests and tests verified (152 tests passing before this mission).
- No reset, clean, stash, overwrite, commit, push, or merge. No `main` history change.
- Remote `main` does not contain Missions 013/014/015; all work remains local/untracked.

## 2. DEM and Geoid Numerical Preparation

- **Checksums verified:** geoid `egm2008-2_5.tar.bz2` SHA-256 `d602e134…` matched exactly; all 32 Mission 011 DEM files and the 793×793 DEM crop matched their manifest checksums.
- **Geoid grid:** EGM2008 2.5′, 8640×4321 PGM, Offset −108 / Scale 0.003, WGS84, sign convention `h = H + N` confirmed (matches Mission 014 and the mission specification).
- **Height conversion applied** only after source/interpolation validation, preserving original DEM elevation values.
- **Local DEM vs processor release `2023_1`:** same product family (COP-DEM_GLO-30-DGED / WorldDEM DSM); exact `2023_1` release **not proven** from local metadata and processor DEM files are absent from the granules. No equivalence claimed from family name alone (Mission 014 PARTIAL finding carried forward).

At the study point: DEM orthometric H ≈ 1776.08 m; geoid N ≈ −34.93 m; ellipsoidal h ≈ 1741.15 m.

## 3. Two Independent Geometry Prototypes

Actual NISAR geometry values were read from the 2026-09-06 GCOV product via authenticated, bounded HTTPS range reads (earthaccess netrc session; no complete HDF5 download). Orbit (45 states), attitude (126 quaternion records), radar-grid axes, and a focused geometry cube window were recorded under gitignored `data/raw/mission015/`.

### Approach A — Product metadata interpolation
Trilinear interpolation of `incidenceAngle` (and slant range/LOS cubes) from the native 500 m radar grid to DEM sample locations. Native grid: 710 × 699 × 21, 500 m posting. Global-to-local window index conversion handled explicitly. Out-of-range and nodata entries are rejected rather than extrapolated.

### Approach B — Orbit and attitude reconstruction
- Orbit position/velocity: documented **linear interpolation** of the 45 state vectors (~10 s sampling per ASF).
- Attitude: documented **slerp** (spherical linear interpolation) of the 126 quaternion records.
- Sensor-to-ground line of sight reconstructed in **WGS84 ECEF**; local incidence = angle between the LOS and the local ellipsoid normal (ENU up), with quaternion conventions, timestamps, units and direction conventions stated. Scene heading/orbit direction alone is **not** used to define local geometry.

## 4. Approach Comparison (17 common real samples)

| Metric (incidence abs difference, A vs B) | Value |
|-------------------------------------------|-------|
| Minimum | 0.5869° |
| Median | 0.6182° |
| Mean | 0.6248° |
| Maximum | 0.6666° |

Both approaches yield physically plausible incidence (~37.5°–38.4°) and agree within ~0.6°, providing independent numerical cross-checking. Spatial variation of disagreement is small (~0.08° spread). The small systematic offset (A slightly lower than B) is consistent with the documented approximation differences (product ellipsoid-incidence cube at discrete height levels vs orbit-reconstructed LOS at DEM-derived ellipsoidal height) and is **not** interpreted as a validated error.

## 5. Numerical Error Budget

| Component | Estimate | Status |
|-----------|----------|--------|
| DEM elevation | 4 m LE90 absolute (<2 m relative where slope ≤20%) | Copernicus GLO-30 (Mission 010) |
| Geoid interpolation | 0.135 m max bilinear (0.031 m cubic) | EGM2008 2.5′ (Mission 014) |
| Radar-grid interpolation | **Not measured** | 500 m → 30 m; no new physical information |
| Orbit interpolation | **Not measured** | 45 states, MOE geolocation unmeasured |
| Attitude interpolation | **Not measured** | 126 records, Custom attitude type |
| Coordinate transform | ~1 mm numerical | Double-precision ECEF; excludes datum differences |

The combined uncertainty is **not** reported as a simple sum of components: several are unmeasured and the components are correlated. A statistically valid total requires measuring the radar-grid, orbit, and attitude terms in a future mission with an explicit propagation method.

## 6. Synthetic Validation (25 deterministic tests, all passing)

1. Flat terrain → local incidence equals ellipsoid incidence (independent analytic check).
2. Radar-facing slope → smaller incidence than flat (analytic normal-tilt check).
3. Radar-away slope → larger incidence than flat.
4. Known shadow geometry → ray-height vs ridge check.
5. Known layover geometry → slope > incidence maps top to closer slant range.
6. DEM height conversion → `h = H + N` verified against independently computed N.
7. Geoid interpolation → bilinear plane exact at center/corners.
8. Orbit interpolation → linear midpoint and out-of-range behavior.
9. Quaternion interpolation → slerp identity/endpoint checks.
10. Invalid coordinates, nodata, extrapolation → rejected (None), never silently extrapolated.

All expected values were calculated independently of the prototype outputs.

## 7. Independent Real-Terrain Validation Target — BLOCKED

No real terrain target outside all Mission 006 candidate components was selected from independent evidence in this mission. Selection must occur independently of candidate-raster values, and no independently validated non-candidate target was available. This condition is explicitly recorded as **BLOCKED** in the manifest; no candidate raster was used to fit or validate the model.

## 8. Resolution Decision

- Native radar-grid metadata: 500 m posting; geometry cubes are **not** 10 m data.
- Orbit/attitude reconstruction: demonstrates ~30 m local incidence is numerically feasible and independently checkable.
- DEM: ~30 m posting; GCOV image posting: 10 m.

**Conclusion:** 30 m geometry is supported **only for limited diagnostic use** with quantified uncertainty. **10 m precision is not claimed** — GCOV posting alone does not create physical geometry information at 10 m.

## 9. Conditions for Full GO

1. Measure radar-grid-to-DEM interpolation error with an explicit error budget.
2. Quantify MOE orbit and Custom attitude interpolation error.
3. Select an independent non-candidate real terrain validation target (currently BLOCKED).
4. Confirm local DEM release identity (`2023_1`) or quantify height differences versus the processor DEM.

## 10. Restrictions — All Honored

No production shadow/layover masks; no water reclassification; no candidate threshold change; no water boundary/area/shoreline; no physical-class labels; no candidate-guided fitting; no validated-water claims. Mission 005/006 data and outputs unmodified. Diagnostic point calculations and synthetic geometry outputs only.

## 11. Verification

- 178/178 scientific tests pass (26 new Mission 015 tests).
- DEM and geoid checksums verified; height conversion independently tested.
- Both approaches evaluated on actual NISAR geometry; error budget documented.
- Independent terrain target explicitly BLOCKED.
- No production classification products generated.

**Do not begin Mission 016 automatically. No commit, push, merge, or modification of main history.**
