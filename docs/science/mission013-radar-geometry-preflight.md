# Mission 013 — NISAR Radar Geometry Preflight & Model Design

**Status:** NO-GO  
**Decision:** Inputs and independent validation strategy are NOT yet adequate for a separately authorized geometry-model implementation. Named blockers must be resolved first.

## 1. Purpose

This preflight establishes whether a scientifically defensible NISAR radar-shadow and layover model can be designed and implemented. It does NOT produce shadow rasters, layover rasters, water reclassification, or area calculations. Mission 005 and Mission 006 sources and outputs are not modified.

## 2. DEM Provenance and Vertical Datum

### Local DEM (Mission 011)

Two Copernicus GLO-30 geocells were acquired:
- `Copernicus_DSM_COG_10_N29_00_E079_00_DEM` (3,600 × 3,600, 1 arc-second posting)
- `Copernicus_DSM_COG_10_N30_00_E079_00_DEM` (3,600 × 3,600, 1 arc-second posting)

Both are buffered to cover the discovery window [79.70, 29.98, 79.92, 30.20] and cropped to 793 × 793 samples.

**Vertical reference:** EGM2008 orthometric height (EPSG:3855). Confirmed by the product XML metadata:
- `vertical: "WGS 84 Geoid EGM08"` (gmd:RS_Identifier)
- `gml:VerticalDatum` with name "EGM2008 geoid" (EPSG:1027)
- Horizontal CRS: WGS84-G1150 (EPSG:4326)

**Horizontal CRS:** WGS84-G1150 / EPSG:4326, 1 arc-second posting (~30.87 m north-south, ~26.76 m east-west at 30.09°N).

### NISAR Processor DEM (Mission 012)

Both GCOV granules (2026-09-06 and 2026-09-30) record:
- `dem_source_identity`: "NISAR DEM version 1.2, Copernicus DEM 30 m release 2023_1, COP-DEM_GLO-30-DGED/2023_1, referenced to the WGS84 ellipsoid"
- `dem_source_doi`: 10.5067/NIDEM-1
- `heightAboveEllipsoid` radar-grid axis: heights above the WGS84 ellipsoid

### Comparison

| Attribute | Local DEM (Mission 011) | NISAR Processor (Mission 012) |
|-----------|------------------------|-------------------------------|
| Product | Copernicus DEM 30-m (2023_1) | Copernicus DEM 30-m (2023_1) |
| Vertical datum | EGM2008 orthometric (EPSG:3855) | WGS84 ellipsoid |
| Horizontal CRS | WGS84-G1150 / EPSG:4326 | WGS84-G1150 / EPSG:4326 |
| Posting | 1 arc-second (~30 m) | 500 m radar grid |

**Finding:** Same DEM product and release, but **different vertical datums**. The local DEM stores EGM2008 orthometric heights; the NISAR processor references WGS84 ellipsoidal heights. Conversion requires:

`ellipsoidal height = orthometric height + geoid undilation`

where geoid undulation = ellipsoid − geoid (EGM2008 separation).

**Status:** No verified EGM2008 geoid-undulation source has been identified. The transformation cannot be applied reproducibly without one.

### Unresolved XML Conflict

The Copernicus DEM XML metadata contains `gml:verticalDatumCodes` including "WGS84-G1150" alongside "EGM2008 geoid". These statements are not reconciled in the product documentation. The format document and copied attributes (EGM2008) are used from Mission 003D onward; the conflict is not given an explanation.

## 3. NISAR Geometry Extraction

### Bounded HTTPS Access

Both GCOV granules were accessed via bounded HTTPS Range requests with h5py over a fileobj wrapper:
- 2026-09-06: `NISAR_L2_PR_GCOV_030_005_D_073_4005_DHDH_A_20260906T132236_20260906T132311_P05023_N_F_J_001.h5` (7,277,117,440 bytes)
- 2026-09-30: `NISAR_L2_PR_GCOV_032_005_D_073_4005_DHDH_A_20260930T132236_20260930T132311_P05023_N_F_J_001.h5` (7,277,117,440 bytes)

**Access result:** The 2026-09-06 granule was successfully opened and its HDF5 signature verified. The 2026-09-30 granule consistently returned CloudFront errors (401 Basic auth required) during this preflight. Complete HDF5 products were not downloaded. Transfer budget: 64 MiB (not exceeded).

### Geometry Datasets Inspected (2026-09-06)

| Dataset | Shape | Dtype | Units |
|---------|-------|-------|-------|
| `radarGrid/incidenceAngle` | [21, 699, 710] | float32 | degrees |
| `radarGrid/slantRange` | [21, 699, 710] | float64 | — |
| `radarGrid/losUnitVectorX` | [21, 699, 710] | float32 | — |
| `radarGrid/losUnitVectorY` | [21, 699, 710] | float32 | — |
| `radarGrid/elevationAngle` | [21, 699, 710] | float32 | — |
| `radarGrid/heightAboveEllipsoid` | [21] | float64 | m |
| `radarGrid/xCoordinates` | [710] | float64 | m |
| `radarGrid/yCoordinates` | [699] | float64 | m |
| `radarGrid/projection` | () | uint32 | — |

**Radar grid:** 710 × 699 × 21 at 500 m posting, confirming Mission 012 metadata. The full scene spans approximately 355 km × 349.5 km.

### Scalar Metadata (2026-09-06)

| Field | Value |
|-------|-------|
| `orbitType` | MOE |
| `orbitInterpMethod` | Hermite |
| `attitudeType` | Custom |
| `shadowMaskingApplied` | False |
| `validSamplesSubSwathMaskingApplied` | False |

### Orbit and Attitude Samples

Orbit state vectors (WGS84 G1762 frame), first 3 epochs:
- Position (m): [953913, 4947601, 5036000], [982488, 4994558, 4984018], [1011024, 5040926, 4931488]
- Velocity (m/s): [2859, 4724, -5170], [2855, 4666, -5225], [2851, 4607, -5280]

Attitude quaternions, first 3 epochs:
- [0.2762, -0.3437, -0.8214, 0.3617], [0.2762, -0.3439, -0.8212, 0.3621], [0.2762, -0.3441, -0.8209, 0.3625]

Euler angles (deg), first 3 epochs:
- [0.134, 37.002, -89.918], [0.134, 37.002, -89.918], [0.134, 37.002, -89.918]

## 4. Metadata Inconsistencies

### Filename Orbit Token vs HDF5 OrbitType

- Filename code: `N` (Near Real-Time fidelity per Product Format Document 1.2.1 section 2.2.4)
- Internal `orbitType`: `MOE` (Medium precision Orbit Ephemeris)
- CMR `ORBIT_TYPE`: `MOE`
- **Status:** Unresolved. Values are not treated as equivalent. No correction claimed.

### Filename Pointing Token vs HDF5 AttitudeType

- Filename pointing token: `N` (would imply NRP per Mission 012 mapping)
- Internal `attitudeType`: `Custom`
- **Status:** Unresolved. Values are not treated as equivalent.

### DEM Vertical Reference

- Local DEM: EGM2008 orthometric
- Processor DEM: WGS84 ellipsoid
- **Status:** Unresolved. Geoid-undulation conversion required but no verified source identified.

## 5. Geometry Model Design

### Coordinate Transformations

1. **DEM-to-ellipsoid:** `ellipsoidal_height = orthometric_height + geoid_undulation` (EGM2008 separation). Requires verified geoid undulation grid (not yet identified).
2. **Ellipsoid-to-radar-grid:** Transform ellipsoidal heights to the radar-grid heightAboveEllipsoid axis (21 levels, -1000 to 9000 m, 500 m step).
3. **Geodetic-to-cartesian:** Convert lat/lon/ellipsoidal-height to ECEF using WGS84 ellipsoid parameters.
4. **Radar look vector:** Combine `losUnitVectorX` and `losUnitVectorY` with the implicit Z component (unit vector constraint) to form the full line-of-sight unit vector in the local-level frame.

### Radar Look Direction and Line-of-Sight

The line-of-sight unit vector components `losUnitVectorX` and `losUnitVectorY` are provided on the 500 m radar grid. The Z component is derived from the unit-vector constraint:
`losZ = sqrt(1 - losX² - losY²)`

Look direction from Mission 012 metadata: Left, Descending.

### Incidence and Slant-Range Usage

- `incidenceAngle`: Ellipsoid incidence angle at target height (NOT local slope incidence). Provided on the 500 m radar grid cube [21, 699, 710].
- `slantRange`: Radar-grid geometry cube [21, 699, 710], NOT the 10 m GCOV image grid.
- `elevationAngle`: Complementary to incidence angle on the radar grid.

**Critical:** Ellipsoid incidence is NOT local slope incidence. Terrain slope must be derived from the DEM and combined with the look vector to compute local incidence.

### Slope and Aspect Derivation

Slope and aspect are derived from the DEM using finite differences on the 30 m posting. The DEM must first be converted from EGM2008 orthometric to WGS84 ellipsoidal heights.

### Radar-Facing Slope and Layover Conditions

- **Radar-facing slope:** Slope aspect aligned with the look direction; terrain surface normal has a component toward the radar.
- **Layover condition:** Occurs when the terrain slope exceeds the incidence angle in the range direction, causing the top of a feature to appear closer in slant range than the bottom.
- **Layover criterion:** `tan(slope) > tan(incidence)` in the range direction, where slope is the terrain inclination toward/away from the radar.

### Terrain Occlusion and Radar-Shadow Conditions

- **Radar shadow:** Occurs when the terrain blocks the line-of-sight from the radar to a surface point. Determined by ray-tracing from each DEM point along the inverse look vector and checking for intervening terrain.
- **Shadow criterion:** A point is in shadow if any intervening DEM sample along the look ray has an elevation above the line-of-sight interpolant.

### Interpolation and Resolution Limitations

**Critical limitation:** The radar grid is at 500 m posting; the GCOV image grid is at 10 m posting; the DEM is at ~30 m posting. A defensible terrain-shadow/layover model requires terrain at or near the radar-grid resolution (500 m) or finer. Interpolating the 30 m DEM to 500 m loses fine-scale terrain detail that determines shadow/layover. Interpolating the 500 m radar grid to 10 m invents spatial detail not present in the source data.

**Do not silently interpolate coarse geometry into a supposedly precise 10 m result.**

### Numerical Uncertainty and Known Failure Cases

- Geoid undulation uncertainty (EGM2008 accuracy ~1-2 m in mountainous terrain)
- DEM vertical accuracy: < 4 m LE90 absolute, < 2 m LE90 relative (slope ≤ 20%), < 4 m LE90 (slope > 20%)
- Orbit ephemeris: MOE (Medium precision), geolocation error not measured
- Attitude type: Custom, pointing fidelity not established
- Filename N vs orbitType MOE discrepancy affects orbit ephemeris interpretation
- Provisional calibration P05023, not mixed with P05036

## 6. Independent Validation Strategy

Validation targets are defined independently of Mission 006 candidate rasters.

### Synthetic Terrain Tests

| Test Case | Expected Result |
|-----------|----------------|
| Flat terrain (zero slope) | No shadow, no layover; incidence = ellipsoid incidence |
| Radar-facing slope (slope toward radar) | Increased local incidence; potential layover if slope > incidence |
| Radar-away slope (slope away from radar) | Decreased local incidence; no layover |
| Known synthetic shadow geometry | Points behind a ridge relative to look direction are shadowed |
| Known synthetic layover geometry | Top of a steep feature maps to closer slant range than its base |

### Independent Non-Candidate Target

A non-water, non-candidate real terrain target (e.g., a known ridge or valley feature from independent optical imagery) should be used to verify that the geometry model correctly classifies it as shadow/non-shadow without reference to Mission 006 candidates.

**Do not use Mission 006 candidates to train, tune, or validate the geometry model.**

## 7. Scientific Restrictions

This mission is a preflight and design mission only. Absolutely no:

- Shadow raster generation
- Layover raster generation
- Water reclassification
- Candidate threshold modifications
- Water boundary calculation
- Water-area calculation
- Shoreline extraction
- Physical-class labeling
- Claims of validated water

Mission 005 and Mission 006 sources and outputs are not modified.

## 8. Decision Gate

**NO-GO**

The available data cannot yet support a defensible geometry model. Named blockers:

1. **Bounded HDF5 access blocked:** Earthdata requires authentication (401 Basic auth challenge) for the NISAR GCOV granules. Geometry datasets could not be reliably read from both granules during this preflight.
2. **No verified geoid-undulation source:** EGM2008-to-WGS84 conversion required but no geoid source identified.
3. **Filename orbit token N vs orbitType MOE discrepancy:** Unresolved; affects orbit ephemeris interpretation.
4. **Filename pointing token vs attitudeType Custom discrepancy:** Unresolved; affects attitude interpretation.

### Conditions for a Future GO

1. Resolve Earthdata authentication for bounded HDF5 access (or obtain geometry datasets through an alternative approved channel).
2. Identify and document a verified EGM2008 geoid-undulation source.
3. Resolve or preserve-as-unresolved the orbit and pointing label discrepancies with architect approval.
4. Confirm that 500 m radar-grid geometry is sufficient for the intended shadow/layover analysis, or obtain finer-resolution geometry.

**Do not begin Mission 014 without explicit approval.**

## 9. Deliverables

| Deliverable | Path | Status |
|-------------|------|--------|
| Preflight report (this document) | `docs/science/mission013-radar-geometry-preflight.md` | Created |
| Machine-readable manifest | `data/manifests/mission013_radar_geometry_preflight.json` | Created |
| Preflight tool | `tools/mission013_geometry_preflight.py` | Created |
| Preflight tests | `tests/scientific/test_mission013_geometry_preflight.py` | Created |

## 10. Verification

- All source data opened read-only
- No source checksum changed (verified before and after)
- No complete NISAR product downloaded
- DEM and processor provenance explicitly compared
- Geometry datasets inspected with actual values (2026-09-06 granule)
- Synthetic tests deterministic and passing (7/7)
- All assumptions and unresolved issues documented
- Model limitations and spatial-resolution constraints explicitly stated
