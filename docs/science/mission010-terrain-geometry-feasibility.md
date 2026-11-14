# Mission 010 — DEM and NISAR terrain-geometry feasibility

This mission identifies terrain and radar-geometry sources for the Kuwari discovery window. It does not download a DEM, open a NISAR HDF5 file, or run a shadow or layover model.

The record is `data/manifests/mission010_terrain_geometry.json`. The estimator is `tools/mission010_feasibility.py`. Tests are `tests/scientific/test_mission010_feasibility.py`.

Starting Git state: `main` and `origin/main` were `fc88b33fb5ad34ec44e2f84b1b9c47df99d84d74`. The tree was clean. Earlier mission files were not modified.

The discovery window remains WGS84 west 79.75, south 30.03, east 79.87, north 30.15. It is a catalogue window, not a lake boundary.

## Copernicus DEM GLO-30

The primary product is `COP-DEM_GLO-30-DGED`, described in the Copernicus DEM Product Handbook, geo1988-copernicusdem-spe-002, version 6.1, dated 09 October 2026.

It is a digital surface model. The handbook defines the DSM as the edited surface, including buildings, infrastructure, and vegetation. It is not a bare-earth terrain model.

| Item | Value from the handbook |
| --- | --- |
| Horizontal reference | WGS84-G1150, EPSG:4326 |
| Vertical reference | EGM2008, EPSG:3855, meters |
| Grid | 1.0 arc second, geographic coordinates |
| Delivery unit | 1° by 1° |
| DGED elevation | 32-bit floating-point GeoTIFF |
| Absolute vertical accuracy | less than 4 m, 90% linear error |
| Relative vertical accuracy | less than 2 m where slope is at most 20%; less than 4 m where slope is greater than 20%, 90% linear point-to-point error inside a 1° cell |
| Absolute horizontal accuracy | less than 6 m, 90% circular error |

The relative-accuracy split is the handbook's own statement about steep ground. A Himalayan slope steeper than 20% falls in the looser class. A DSM also places vegetation and structures in the elevation, so a radar simulation on it is not a simulation on bare rock. The source DEM is an edited WorldDEM with local infill from other elevation datasets. Those infill patches are not the same measurement as the TanDEM-X surface.

The Copernicus Data Space collection page and the EGNOS GLO-30 guide describe GLO-30 as a free and open dataset. The licence PDF itself was not retrieved. Access is the Copernicus Data Space collection `COP-DEM`, not a file copied into this repository.

The handbook names a DGED geocell from its lower-left corner. For this window the corner is `Copernicus_DSM_10_N30_00_E079_00`. At latitude 30.09°, 1 arc second is about 30.87 m north–south and 26.76 m east–west. That is an ellipsoidal approximation, not a surveyed posting, and it is not 30 m in both directions.

## Buffer and size

A planning buffer of 0.05° on every side produces the box west 79.70, south 29.98, east 79.92, north 30.20. The southern edge crosses latitude 30°. The delivery units are therefore two geocells:

- `Copernicus_DSM_10_N30_00_E079_00`
- `Copernicus_DSM_10_N29_00_E079_00`

The unbuffered window stays inside the northern geocell. The second geocell is required only because the buffer crosses 30° N.

An extracted elevation grid over that buffered box, at 1 arc second and including both edges, is 793 by 793 postings. Uncompressed 32-bit elevation is 2,515,396 bytes. One full geocell is 3601 by 3601 postings and 51,868,804 uncompressed bytes. Those figures are the elevation band only. The DGED product also contains quality layers, and no compressed object size was measured because no DEM URL was requested.

The 0.05° buffer is a planning distance. It is not a calculated shadow length. A ridge outside that buffer can still occult the window. The safe acquisition unit, until a line-of-sight length is computed, is the two geocells rather than a smaller crop.

## NASADEM and CartoDEM

`NASADEM_HGT.001` is the LP DAAC merged DEM, user guide V1.3, January 2025. The merged `hgt` band is a 2-byte signed integer at 1 arc second, with heights relative to the EGM96 geoid. The source radar is SRTM, 11–21 February 2000, later reprocessed and void-filled. The collection extent, about 56° S to 60° N, includes this latitude. The user-guide tile name for a southwest corner at 30° N, 79° E is `NASADEM_HGT_n30e079.zip`. The buffered window also meets `NASADEM_HGT_n29e079.zip`.

NASADEM is not a substitute for Copernicus DEM. The vertical datums differ, EGM96 against EGM2008. The epochs differ. One is an integer void-filled SRTM modernization and the other is a TanDEM-X surface model. NASADEM also distributes SRTM incidence layers, `inc0` relative to the ellipsoid and `inc` as a local incidence. Those are Shuttle-era angles. They are not NISAR incidence.

CartoDEM is an NRSC product. The Bhuvan download help says a login is required and Cartosat DEM downloads are limited to 10 tiles a day. NRSC states that a posting of 30 m or coarser is a free download, while postings finer than 30 m, including 10 m, follow separate clearance rules. The retrieved terms are a single-user licence, with no redistribution and no internet hosting of the original product. The vertical datum was not established from the pages read here. CartoDEM is not the open default for this mission.

## NISAR geometry

The source HDF5 files are not in the workspace. This mission did not download or open them. The paths below are the L-band form of the tables in the NISAR L and S Band Level-1 and Level-2 Data Product Format Document, version 1.2.1. Section 2.5.1 says the S-band layout applies to L-band when `SSAR` is replaced by `LSAR`.

The Mission 003 crops contain GCOV `HHHH`, `HVHV`, `numberOfLooks`, the GCOV valid-samples mask, and the GSLC valid-samples mask. They do not contain an incidence cube or a line-of-sight cube.

| Path | What the format document says it is |
| --- | --- |
| `/science/LSAR/identification/lookDirection` | Scalar, `Left` or `Right` |
| `/science/LSAR/identification/orbitPassDirection` | Scalar, `Ascending` or `Descending` |
| `/science/LSAR/GCOV/metadata/orbit/orbitType` | HDF5 orbit-ephemeris label: `FOE`, `NOE`, `MOE`, `POE`, or `Custom` |
| `/science/LSAR/GCOV/metadata/orbit/time` | Time tags for the position and velocity records |
| `/science/LSAR/GCOV/metadata/orbit/interpMethod` | Interpolation method, `Hermite` or `Legendre` in the format table |
| `/science/LSAR/GCOV/metadata/orbit/position` and `velocity` | State vectors in the WGS84 G1762 frame |
| `/science/LSAR/GCOV/metadata/attitude/time` | Time tags for the attitude records |
| `/science/LSAR/GCOV/metadata/attitude/quaternions` | Attitude quaternions |
| `/science/LSAR/GCOV/metadata/attitude/eulerAngles` | Roll, pitch, and yaw, in degrees |
| `/science/LSAR/GCOV/metadata/ceosAnalysisReadyData/geometricAccuracy/bias/x` and `bias/y` | Product estimates of localization bias, in meters. Not a surveyed ground truth |
| `/science/LSAR/GCOV/metadata/ceosAnalysisReadyData/geometricAccuracy/standardDeviation/x` and `standardDeviation/y` | Product estimates of localization standard deviation, in meters. Not a surveyed ground truth |
| `/science/LSAR/GCOV/metadata/processingInformation/inputs/demSource` | Processor description of the DEM used to make the GCOV product |
| `/science/LSAR/GCOV/metadata/processingInformation/inputs/demFiles` | List of DEM files named by the processor |
| `/science/LSAR/GCOV/metadata/radarGrid/xCoordinates` and `yCoordinates` | East and north axes of the radar-grid cube. Posting was not read |
| `/science/LSAR/GCOV/metadata/radarGrid/heightAboveEllipsoid` | Heights above the WGS84 ellipsoid for that cube. This is not a DEM |
| `/science/LSAR/GCOV/metadata/radarGrid/incidenceAngle` | Float32 cube. Incidence between the line of sight and the ellipsoid normal at the target height. Units degrees. Valid range 0 to 90 |
| `/science/LSAR/GCOV/metadata/radarGrid/slantRange` | Slant range, meters |
| `/science/LSAR/GCOV/metadata/radarGrid/losUnitVectorX` and `losUnitVectorY` | East and north components of the line-of-sight unit vector. The up component is not stored |
| `/science/LSAR/GCOV/metadata/radarGrid/elevationAngle` | Elevation angle at the sensor |
| `/science/LSAR/GSLC/metadata/radarGrid/` | The same cube family on the GSLC product |
| `/science/LSAR/GCOV/metadata/processingInformation/parameters/shadowMaskingApplied` | Scalar flag that shadow masking was or was not applied |

The incidence dataset is a radar-grid cube with height, length, and width dimensions. Its spacing is an attribute of the dataset. This mission did not read that attribute, so no posting is claimed for these granules. A scene-level look direction or heading is not that cube. The cube's incidence is ellipsoid incidence at a target height. It is not the angle between the line of sight and the local slope.

`shadowMaskingApplied` is not a shadow map. The GSLC path `/science/LSAR/GSLC/grids/frequencyA/mask` remains a valid-samples subswath mask. It is not a terrain, shadow, or layover mask. The same is true of the GCOV mask.

Filename code `N` and HDF5 `orbitType` `MOE` are a cross-field inconsistency. Section 2.2.4 maps `N` to Near real-time Orbit Ephemeris, `NOE`, and also pairs that filename token with Near real-time Radar Pointing, `NRP`. The HDF5 `orbitType` vocabulary is `FOE`, `NOE`, `MOE`, `POE`, or `Custom`, and `MOE` means Medium precision Orbit Ephemeris. Both fields describe orbit-ephemeris provenance, and the values disagree. The observed values are unchanged. The mismatch is not resolved, and it has not been rechecked against the product file or provider guidance. No geolocation error was measured for this valley. The geometric-accuracy datasets, if present, would still be product estimates rather than a survey.

## What a later model would need

A defensible shadow and layover test needs four separate inputs:

1. Elevation on a stated datum. Copernicus GLO-30 is orthometric, EGM2008. The NISAR incidence definition uses the ellipsoid normal at the target height. Those references have to be reconciled before a slope is combined with an incidence cube.
2. The line-of-sight vector from `losUnitVectorX` and `losUnitVectorY`, with the up component derived as in the format document, plus slant range.
3. Slope and aspect from the DEM, at the DEM posting, without resampling the DEM onto the 10 m GCOV grid until the posting difference is explicit.
4. A geometric rule that labels layover where a radar-facing slope reverses slant-range order, and shadow where terrain closer to the sensor occludes terrain farther along the same line of sight. The classical statement of that map is Kropatsch and Strobl, IEEE Transactions on Geoscience and Remote Sensing, 1990, "The generation of SAR layover and shadow maps from digital elevation models." This mission does not implement it.

The GCOV layers already in the repository are radiometrically terrain-corrected gamma0. A later shadow map would interpret those values. It would not reprocess them, and it would not be trained on the Mission 006 candidate pixels.

## Validation

A future test needs a target that is not a candidate patch. Useful checks are a published look direction and orbit pass, a radar-grid cube whose shape and spacing were read from the file, a DEM with its datum written down, and at least one radar-facing slope and one radar-away slope whose geometry labels differ for a reason stated in advance. Stable rock or a ridge outside the candidate set can serve. The candidate rasters cannot be the only truth for the geometry model.

## Blockers

- No DEM array is in the repository, and none was downloaded.
- The source GCOV and GSLC HDF5 files were not opened, so the cube shapes, spacing attributes, look direction, and `shadowMaskingApplied` value are not known for these two dates.
- Ellipsoid incidence and an EGM2008 surface model are not the same height reference.
- Filename code `N` expects `NOE`, while the recorded HDF5 `orbitType` is `MOE`. That mismatch is unresolved, so the geolocation error is unknown.
- The GSLC valid-samples mask cannot fill any of those gaps.
- NASADEM local incidence is SRTM geometry from 2000, not NISAR geometry.

## Recommendation

**CONDITIONAL GO** for a Mission 011 that only acquires inputs.

That mission may fetch the two GLO-30 DGED geocells, or a crop whose elevation band is on the order of 2.5 MB uncompressed, and it may read the geometry datasets listed above from the two existing GCOV files. It may not mix in NASADEM or CartoDEM. It may not build a shadow or layover mask, fit a rule to the Mission 006 candidates, or calculate an area.

A shadow model stays **NO-GO** until those inputs have been read and a non-candidate validation target has been named.
