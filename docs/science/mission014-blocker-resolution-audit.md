# Mission 014 — Geometry Blocker Resolution Audit

**Final Decision: CONDITIONAL GO**

A separate geometry-model implementation mission is scientifically justified. Inputs are now adequate, but four named conditions remain (see Section 8).

## 1. Starting State

- Branch `main`, HEAD `a509f78`, tracking `origin/main` — clean of unexpected modifications.
- All four Mission 013 deliverables present as untracked files and preserved unchanged:
  - `docs/science/mission013-radar-geometry-preflight.md`
  - `data/manifests/mission013_radar_geometry_preflight.json`
  - `tools/mission013_geometry_preflight.py`
  - `tests/scientific/test_mission013_geometry_preflight.py`
- Remote `main` does not contain Mission 013. No reset, clean, stash, or overwrite was performed.

## 2. Blocker Resolution Summary

| Mission 013 blocker | Outcome |
|---------------------|---------|
| EGM2008 geoid source missing | **RESOLVED** — official NGA source verified; grid downloaded with matching checksum; sign convention and interpolation verified; sample undulations computed |
| NISAR bounded HDF5 access blocked (401 / CloudFront) | **RESOLVED** — authentication contradiction explained; both granules read with all geometry datasets |
| 500 m radar-grid resolution | **REASSESSED** — 30 m output defensible with error budget; 10 m not justified |
| DEM release identity | **PARTIAL** — same product family; exact `2023_1` release not provable from local metadata |
| Orbit/pointing label discrepancy | **PRESERVED UNRESOLVED** — physical geometry still reconstructable from recorded state vectors |

## 3. NISAR Authentication Contradiction — RESOLVED

### Root cause

- **Mission 012** reported successful bounded HTTPS/HDF5 access using `earthaccess.login(strategy='netrc')`. Its inspection function is a **static record** ("Re-running this function does not contact the network") — the success was recorded, not reproduced live.
- **Mission 013** used raw `requests.get()` Range headers with no Earthdata session. That produces a **401** `text/html` Basic-auth challenge, and the second granule additionally hit a CloudFront **502**.

### Resolution

Earthaccess on Windows defaults to `_netrc`, but the existing credential file is `.netrc` (Mission 012 recorded `existing_file_is_dot_netrc: True`). Setting the `NETRC` environment variable to the existing `.netrc` path before `earthaccess.login(strategy='netrc')` produces an authenticated `earthaccess.auth.SessionWithHeaderRedirection`.

### Verified probe result (2026-11-17)

| Item | Result |
|------|--------|
| Login | `earthaccess.login(strategy='netrc')` → authenticated True |
| Session | `SessionWithHeaderRedirection` |
| Bounded GET | HTTP **206**, `binary/octet-stream`, `Content-Range: bytes 0-8191/7277117440` |
| Redirect history | 303 to CloudFront host (handled by the header-redirection session) |
| HDF5 signature | Valid at offset 0 |
| Both granules | **Read successfully** (2026-09-06 and 2026-09-30) |

Credentials were never printed, `.netrc` was never modified or copied, and no complete HDF5 product was downloaded.

### Geometry datasets confirmed on both dates

| Dataset | Shape | Dtype |
|---------|-------|-------|
| `incidenceAngle` | [21, 699, 710] | float32 |
| `slantRange` | [21, 699, 710] | float64 |
| `losUnitVectorX` | [21, 699, 710] | float32 |
| `losUnitVectorY` | [21, 699, 710] | float32 |
| `elevationAngle` | [21, 699, 710] | float32 |
| `heightAboveEllipsoid` | [21] | float64 |
| `xCoordinates` | [710] | float64 |
| `yCoordinates` | [699] | float64 |

Actual incidence values were read (e.g. ~27.76–27.93° in the sampled corner). Scalars confirmed on both dates: `orbitType=MOE`, `interpMethod=Hermite`, `attitudeType=Custom`, `shadowMaskingApplied=False`.

## 4. EGM2008 Geoid Source — RESOLVED

### Official source

- NGA WGS84 page: `https://earth-info.nga.mil/?action=wgs84&dir=wgs84`
- EGM2008: degree 2190 / order 2159; NGA STND.0036_1.0 (2014-07-08).
- NGA provides a **2.5-minute worldwide precomputed EGM2008 geoid-height grid**.

### Verified distribution

| Attribute | Value |
|-----------|-------|
| Distribution | GeographicLib `egm2008-2_5.tar.bz2` (built from NGA binary gridded data) |
| SHA-256 | `d602e13446a4a4a23f39aecfe6a2a0760a1bc6c1b497482c2ebc9f7d513be699` (verified exact match) |
| Grid file | `egm2008-2_5.pgm` (P5, 16-bit, big-endian) |
| Dimensions | 8640 × 4321 |
| Posting | 2.5 arc-minutes (0.0416667°) |
| Offset / Scale | −108 m / 0.003 m per pixel |
| Reference ellipsoid | WGS84 |
| Vertical datum | WGS84 (geoid height above ellipsoid) |

### Sign convention

GeographicLib and NGA define geoid undulation `N` as height of geoid above the WGS84 ellipsoid:

`h = H + N` → **ellipsoidal = orthometric + geoid undulation**

This **matches the mission-specified convention exactly**.

### Interpolation and error budget

| Method | Max error | RMS error |
|--------|-----------|-----------|
| Bilinear | 0.135 m | 0.003 m |
| Cubic (12-point) | 0.031 m | 0.001 m |

The PGM supports random pixel access, so a bounded regional subset is feasible — only the local stencil pixels around the Kuwari window are needed. The full global harmonic coefficient set was **not** downloaded.

### Reproducible sample values (computed from the verified grid)

| Point | Lat / Lon | N (m) |
|-------|-----------|-------|
| Study point | 30.088337 / 79.808685 | **−34.9258** |
| Window SW | 29.98 / 79.70 | −38.4978 |
| Window NE | 30.20 / 79.92 | −30.8202 |
| Window center | 30.09 / 79.81 | −34.8673 |

The tool `geoid_undulation_bilinear()` reproduces the study-point value from the verified grid on re-run (deterministic test confirmed).

## 5. DEM Product Identity — PARTIAL

| Attribute | Processor DEM (Mission 012) | Local DEM (Mission 011) |
|-----------|------------------------------|--------------------------|
| Family | COP-DEM_GLO-30-DGED | Copernicus GLO-30 DGED / WorldDEM DSM |
| Release | **2023_1** explicit | No explicit `2023_1` token in local XML |
| Vertical datum | WGS84 ellipsoid | EGM2008 orthometric |
| Processor DEM files present in granules | `dem_files_present: False` | — |

**Conclusion:** Same product family, but the exact `2023_1` release is **not proven** from local metadata, and the processor's DEM files are not in the granules, so byte-level identity cannot be verified. A matching family is not proof of an identical release. The vertical-datum difference is now resolvable using the verified EGM2008 source. **No transformation was applied in this audit.**

## 6. 500 m Resolution — REASSESSED

The 500 m radar grid does **not** automatically make finer geometry impossible. Two approaches were assessed:

**Approach A — product metadata interpolation:** Interpolate `incidenceAngle`, `slantRange`, and LOS cubes (500 m) to the DEM grid with an explicit error budget. Error sources: geoid 0.135 m, DEM <4 m LE90, radar-grid interpolation error (must be measured), MOE geolocation (unmeasured). Defensible at 30 m only after measuring interpolation error.

**Approach B — geometry reconstruction:** Reconstruct platform position and LOS from orbit position/velocity (45 states, ~10 s sampling per ASF), attitude quaternions (126 records), and `heightAboveEllipsoid` (21 levels). Compute local incidence from the DEM surface normal. This is independent of the coarse incidence cube and is independently checkable, but depends on MOE/attitude accuracy and Hermite orbit interpolation.

**Conclusion:** A **30 m** DEM-grid geometry output can be defensible with an explicit error budget and independent validation. **10 m geometry is NOT justified** merely because GCOV is posted at 10 m. No production raster was generated.

## 7. Orbit and Pointing Discrepancies — PRESERVED

- Filename token `N` vs HDF5 `orbitType=MOE`. ASF's authoritative Orbit Ephemeris guide states: "The NISAR mission uses Medium precision (MOE) data when generating new NISAR data products." MOE is therefore the **operational standard**, and `MOE` in the HDF5 is expected. The filename `N` likely reflects delivery/fidelity labeling. Both values preserved; not rewritten.
- Filename pointing token vs `attitudeType=Custom`. `Custom` indicates adaptive pointing; quaternions are recorded and usable.
- **Neither label was used to infer geolocation error.** Physical geometry can be reconstructed from the recorded state vectors regardless of the label semantics. Remaining uncertainty: exact label meaning and geolocation error (unmeasured).

## 8. Named Conditions for GO

1. Confirm the exact local DEM release is `COP-DEM_GLO-30-DGED/2023_1`, or quantify height differences versus the processor DEM.
2. Measure radar-grid-to-DEM interpolation error with an explicit error budget before producing 30 m geometry.
3. Identify a non-candidate real terrain validation target from independent evidence.
4. Preserve the unresolved orbit/pointing label values; do not infer geolocation error from labels.

## 9. Independent Validation Strategy

Synthetic tests (deterministic, independent of Mission 006 candidates): flat terrain; radar-facing slope; radar-away slope; known shadow geometry; known layover geometry. A non-candidate real terrain target (e.g., a catalogued ridge/valley from independent optical imagery or published topography, outside all Mission 006 candidate patches) must be identified for eventual validation. Mission 006 candidate rasters are **not** used to fit or validate the geometry model.

## 10. Restrictions — All Honored

No shadow/layover masks; no water reclassification; no Mission 005/006 threshold changes; no area or shoreline; no physical-class labels; no complete HDF5 download; no validated-model claim; Mission 013 files unmodified; no source raster modified.

## 11. Verification

- 152/152 scientific tests pass (17 new Mission 014 tests).
- EGM2008 grid SHA-256 verified; sample undulations reproduced from the grid.
- Auth contradiction explained with status/redirect/response-type evidence (no secrets).
- All deliverables created; decision = **CONDITIONAL GO**.

**Do not begin Mission 015 automatically. No commit, push, merge, or modification of main history.**
