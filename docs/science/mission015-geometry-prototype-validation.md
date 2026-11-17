# Mission 015 — Geometry Model Prototype & Numerical Validation

> **Mission 015.1 correction (review branch `fix/mission015-geometry-review`):** The original Mission 015 results below were superseded after scientific review. The corrected work is recorded in the "Mission 015.1 Correction" section appended at the end of this document. Most importantly: the earlier median 0.618° agreement came from an **incorrect** Approach B that used one mean orbit timestamp for every target and from an incidence-only Approach A. After correction (target-specific zero-Doppler solve using orbit position AND velocity), the median incidence difference is **0.0057°**, zero-Doppler residual is ~0, and agreement with the product `zeroDopplerAzimuthTime` is ~0.0001 s — but the two approaches are **not independent** (shared orbit/DEM lineage). See the correction section for the authoritative current findings.

**Final Decision (both Mission 015 and 015.1): CONDITIONAL GO**

Numerical feasibility of NISAR radar geometry reconstruction at ~30 m is demonstrated. A **limited diagnostic geometry implementation** is justified with a documented error budget, but specific conditions remain — most importantly, no independent non-candidate real terrain validation target was selected (BLOCKED).

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

---

# Mission 015.1 — Geometry Prototype Corrections & Independent Validation

**Branch:** `fix/mission015-geometry-review` from base `1d68985`  
**Final Decision: CONDITIONAL GO** (limited diagnostic calculations only)

## 0. What changed and why

Scientific review found the original Mission 015 comparison was not defensible:

1. **Approach B used one mean orbit epoch for every target** — not the target's acquisition time. This is physically wrong for a zero-Doppler product.
2. **Approach B was mislabeled "attitude-based LOS reconstruction"** — the quaternion never contributed to the LOS.
3. **Approach A interpolated incidence only** — slant range and LOS components were not compared.
4. **Interpolation silently clamped/extrapolated** outside the sample-center domain and did not reject bad axes.
5. **The 0.618° "agreement" was not meaningful** without a target-specific time and an independence analysis.

## 1. Authoritative conventions established from the product

Dataset attributes were read directly from the HDF5 (recorded in the manifest):
- `incidenceAngle`: angle between LOS and ellipsoid normal at target height; degrees.
- `losUnitVectorX` / `losUnitVectorY`: **East / North components of the LOS unit vector, direction target→sensor, in ENU at the target**. The Up component is not stored; it is derived as `+sqrt(1 - E² - N²)` (sensor above target).
- `slantRange`: meters. `heightAboveEllipsoid`: heights above WGS84 ellipsoid (21 levels, −1000…9000 m).
- `zeroDopplerAzimuthTime`: **seconds since 2026-09-06T00:00:00**, cube [21,699,710] — the product's target-specific acquisition times.
- Orbit position/velocity: **WGS84 G1762** ECEF, m and m/s; `interpMethod=Hermite` (we use documented linear interpolation as an approximation and record it as such).
- Attitude quaternions `(q0,q1,q2,q3)` scalar-first, but attributes define **no reference frame, rotation direction or antenna boresight**. Therefore attitude cannot defensibly rotate the geometric LOS.

Axes are verified from the actual coordinate arrays (x: 296250→650750 m step +500; y: 3570250→3221250 m step −500; height step +500); no spacing is hardcoded in the interpolation path.

## 2. Corrected Approach B — target-specific zero-Doppler

For each target ECEF position, the zero-Doppler condition `range_rate(t) = dot(unit(target − sensor(t)), velocity(t)) = 0` is solved by bisection over the orbit span using **interpolated position AND velocity**. Recorded per sample: acquisition time, sensor position, velocity, residual, convergence/failure. Out-of-range and no-bracket cases are recorded as failures, never replaced by the mean epoch.

**Validation:** the solved acquisition times match the product's own `zeroDopplerAzimuthTime` cube to a maximum absolute difference of ~0.0001 s across the 17 common samples, with zero-Doppler residual ~0 m/s. This confirms the solution implements the product's stated convention.

## 3. Attitude handling — accurately described

Approach B is now named **"Orbit zero-Doppler LOS reconstruction"**, not attitude-based. Attitude quaternions are validated separately (normalization, slerp endpoints, sign/double-cover equivalence, 90° frame rotation via scalar-first rotation matrix) but are **not** applied to the geometric LOS, because the product does not define a sufficient boresight/frame convention. Beam/boresight consistency is therefore recorded as unavailable, not claimed.

## 4. Corrected Approach A — all geometry fields

Trilinear interpolation now covers `incidenceAngle`, `slantRange`, `losUnitVectorX` (ENU East) and `losUnitVectorY` (ENU North), with LOS-Up derived from the unit-norm constraint. Strict boundary rules: sample-center domain only; exact boundary samples allowed; just-outside rejected; NaN/inf/nodata rejected; duplicate/non-monotonic axes rejected; never clamped or extrapolated.

## 5. Corrected comparison (17 reproducible samples, 2026-09-06)

| Metric (absolute difference, A vs B) | Min | Median | Max |
|---|---|---|---|
| Incidence (deg) | 0.0056 | 0.0057 | 0.0059 |
| Slant range (m) | 75.6 | 78.5 | 79.8 |
| LOS angular (deg) | 0.9779 | 0.9781 | 0.9783 |
| Acquisition time vs product ZDT (s) | 0.000085 | 0.000093 | 0.000098 |
| Zero-Doppler residual (m/s) | 0 | 0 | 0 |

The far smaller incidence difference (0.0057° vs the old 0.618°) is a direct consequence of the target-specific time correction — the earlier result was an artifact of the mean-epoch error. The ~78 m slant-range difference and ~0.98° LOS difference reflect height-reference/interpolation-model differences (Approach A interpolates product cubes at the DEM-derived continuous height; Approach B reconstructs from orbit at that height) and require further study; they are reported, not hidden.

**Independence:** the two approaches are **not independent** — the product radar-grid cube and the orbit solution share source orbit/geocoding lineage. Agreement is internal consistency, not independent validation.

**2026-09-30:** geometry access initially failed (transient `SystemError`), then succeeded on retry (206, valid HDF5, bounded window saved). Full comparison for that granule remains a follow-up; conclusions here are restricted where noted.

## 6. Numerical interpolation error (measured)

Withheld height-plane cross-validation on the native incidence cube: 128 withheld samples; max abs error 1.14e-5°, median 7.6e-6°, mean 8.3e-6°. This is **numerical interpolation error of the 500 m product grid only** — not physical 30 m terrain accuracy, and not a claim that interpolation creates 30 m information.

## 7. Strengthened synthetic validation (uses actual prototype functions)

Shadow: ridge below ray → clear; ridge intersecting ray → shadow (both via `ray_clear`). Layover: slope below incidence → no layover; exceeding → layover (via `layover_condition`). Slant-range ordering checked via `slant_range_ordering`. Coordinate-frame reversal changes ENU LOS components. Quaternion tests cover normalization, endpoints, sign equivalence and a 90° frame rotation. Strict interpolation boundary tests cover just-inside/on/just-outside each axis. Expected values derived independently. All 27 Mission 015.1 tests pass (179 total).

## 8. Reassessed error budget

Separate estimates: DEM elevation 4 m LE90; EGM2008 interpolation 0.135 m max; radar-grid interpolation measured numerically (1.1e-5° incidence) but physical meaning limited; orbit interpolation unmeasured (MOE); attitude interpolation unmeasured (not applied to LOS); coordinate transform ~1 mm numerical; acquisition-time solution residual ~0 m/s (but agreement with product ZDT is not independent evidence). **Combined uncertainty is NOT reported** — important components are unmeasured and the approaches are correlated.

## 9. Unresolved blockers / conditions

1. Numerical interpolation error is not physical 30 m terrain accuracy; real 30 m accuracy remains unverified.
2. Independent non-candidate real terrain validation target: **BLOCKED**.
3. MOE orbit interpolation error unmeasured; ZDT agreement is not independent evidence.
4. DEM release identity (`2023_1`) unconfirmed.
5. ~78 m slant / ~0.98° LOS A-vs-B differences require a height-reference study.

## 10. Final decision — CONDITIONAL GO

Target-specific zero-Doppler geometry is numerically reproducible and matches the product convention. A limited diagnostic implementation is justified with the named restrictions. No production classification products. No Mission 016. No commit/push/merge/modification of main history for this mission.
