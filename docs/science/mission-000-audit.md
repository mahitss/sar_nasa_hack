# Mission 000 audit record

- Date of catalogue queries: 2026-11-14
- Gate recorded then: CONDITIONAL GO
- This file preserves that inspection. It does not repeat it.

## How to read the granule identifiers

The identifiers below are provisional inputs. They were returned by NASA CMR during Mission 000. Mission 001 did not re-query the catalogue and did not open any science file. Do not copy this list into `data/manifests/` until a later mission checks each identifier again and records the query URL, the CMR hit, and the footprint test.

Shared metadata read from those provisional GCOV records: processing center JPL, product version 1.0.11, orbit type `MOE`, full frame, joint observation true, Frequency B bandwidth 5 MHz. Whether the HDF5 contains a usable S-band raster was not verified.

The point test used 30.088337°N, 79.808685°E from the SANDRP commentary of 22 November 2024. That coordinate lies inside the discovery box. It is a secondary source, not a survey mark. The ray-cast was a Mission 000 script against the CMR polygon. It is not a substitute for opening the raster.

## Release context

From the ASF availability page, queried in Mission 000:

- Provisional L-band products use CRID P05023 and cover acquisitions from 17 June 2026 until partway through 23 October 2026.
- Validated L0–L2 products were released 6 November 2026 at initial CRID P05036, for L-band acquisitions starting 21 October 2026.
- A permanent instrument gap is published from `2026-07-27T22:03:25Z` to `2026-08-10T00:55:27Z`.
- Validated reprocessing of data acquired before 21 October 2026 is described as a 2027 campaign.
- ASF tells users to be careful when combining products from different CRID generations.

User-guide posting used to interpret Frequency A bandwidth: 40 MHz GCOV at 10 m, 20 MHz GCOV at 20 m. GUNW unwrapped phase and GOFF offsets are posted at 80 m. Confirm those tables again before any measurement code depends on them.

## CMR hit counts for the discovery box and window

Box: 79.75, 30.03, 79.87, 30.15. Window: 2026-07-08 through 2026-11-14. Hits are bounding-box intersections, not point coverage.

| Short name | Concept ID | Hits |
| --- | --- | --- |
| `NISAR_L2_GCOV_PROVISIONAL_V1` | `C2854338529-ASF` | 23 |
| `NISAR_L2_GCOV_V1` | `C3622241360-ASF` | 5 |
| `NISAR_L2_GSLC_PROVISIONAL_V1` | `C2854332392-ASF` | 24 |
| `NISAR_L2_GSLC_V1` | `C3622244601-ASF` | 5 |
| `NISAR_L2_GUNW_PROVISIONAL_V1` | `C2854335566-ASF` | 22 |
| `NISAR_L2_GUNW_V1` | `C3622247503-ASF` | 0 |
| `NISAR_L2_GOFF_PROVISIONAL_V1` | `C2854341702-ASF` | 23 |
| `NISAR_L2_GOFF_V1` | `C3622250865-ASF` | 0 |

Provisional RSLC hits were 24 and validated RSLC hits were 6. Provisional SME2 hits were 23. SME2 is a soil-moisture product and Earthdata described the provisional collection as not fully calibrated. It is unused.

The provisional GSLC set included two versions, `_001` and `_002`, of the 6 September track-5 scene. A later ingest needs an explicit version rule.

## Group D40, primary comparison group

Descending, track 5, frame 73, Frequency A 40 MHz, HH+HV, CRID P05023. Mission 000 marked each footprint as containing the test point.

| Acquisition start | Provisional granule UR |
| --- | --- |
| 2026-07-20T13:22:38Z | `NISAR_L2_PR_GCOV_026_005_D_073_4005_DHDH_A_20260720T132238_20260720T132312_P05023_N_F_J_001` |
| 2026-08-13T13:22:36Z | `NISAR_L2_PR_GCOV_028_005_D_073_4005_DHDH_A_20260813T132236_20260813T132311_P05023_N_F_J_001` |
| 2026-09-06T13:22:36Z | `NISAR_L2_PR_GCOV_030_005_D_073_4005_DHDH_A_20260906T132236_20260906T132311_P05023_N_F_J_001` |
| 2026-09-30T13:22:36Z | `NISAR_L2_PR_GCOV_032_005_D_073_4005_DHDH_A_20260930T132236_20260930T132311_P05023_N_F_J_001` |

The gap between 20 July and 13 August matches the published instrument outage. These four are the approved pool for the first two-acquisition measurement. Which pair is used is a later mission decision, made after the ids are rechecked and the rasters are inspected.

## Group D20, separate

Same track and frame, 20 MHz, HH+HV+VH+VV, CRID P05023. Also marked inside the test point. Not interchangeable with D40.

| Acquisition start | Provisional granule UR |
| --- | --- |
| 2026-07-08T13:22:38Z | `NISAR_L2_PR_GCOV_025_005_D_073_2005_QPDH_A_20260708T132238_20260708T132313_P05023_N_F_J_001` |
| 2026-08-25T13:22:36Z | `NISAR_L2_PR_GCOV_029_005_D_073_2005_QPDH_A_20260825T132236_20260825T132311_P05023_N_F_J_001` |
| 2026-09-18T13:22:36Z | `NISAR_L2_PR_GCOV_031_005_D_073_2005_QPDH_A_20260918T132236_20260918T132311_P05023_F_F_J_001` |
| 2026-10-12T13:22:36Z | `NISAR_L2_PR_GCOV_033_005_D_073_2005_QPDH_A_20261012T132236_20261012T132311_P05023_N_F_J_001` |

The 18 September id contains `F_F` where the others contain `N_F`. The meaning of that flag was not confirmed.

## Group A40, separate geometry

Ascending, track 127, frame 17, 40 MHz, HH+HV, CRID P05023. Marked inside the test point.

| Acquisition start | Provisional granule UR |
| --- | --- |
| 2026-07-16T23:56:32Z | `NISAR_L2_PR_GCOV_025_127_A_017_4005_DHDH_A_20260716T235632_20260716T235707_P05023_N_F_J_001` |
| 2026-08-21T23:56:30Z | `NISAR_L2_PR_GCOV_028_127_A_017_4005_DHDH_A_20260821T235630_20260821T235705_P05023_N_F_J_001` |
| 2026-09-02T23:56:30Z | `NISAR_L2_PR_GCOV_029_127_A_017_4005_DHDH_A_20260902T235630_20260902T235705_P05023_N_F_J_001` |
| 2026-09-14T23:56:30Z | `NISAR_L2_PR_GCOV_030_127_A_017_4005_DHDH_A_20260914T235630_20260914T235705_P05023_N_F_J_001` |
| 2026-09-26T23:56:30Z | `NISAR_L2_PR_GCOV_031_127_A_017_4005_DHDH_A_20260926T235630_20260926T235705_P05023_N_F_J_001` |
| 2026-10-20T23:56:30Z | `NISAR_L2_PR_GCOV_033_127_A_017_4005_DHDH_A_20261020T235630_20261020T235705_P05023_N_F_J_001` |

## Box hits that failed the point test

Provisional GCOV on track 106, frame 73, and track 55, frame 17, intersect the discovery box and did not contain the test point. They are not members of D40, D20, or A40. Their granule URs remain in the Mission 000 session output and are omitted here so this table is not used as a download list.

## Validated GCOV in the window

These use CRID P05036. Mission 000 did not ray-cast the validated polygons, except that the 9 November track-55 bounding box ends at 79.789°E, west of the test point, so that scene cannot contain it. Coverage for the track-5 and track-127 validated scenes is inferred from the same track and frame numbers, not from a second point test.

| Acquisition | Mode | Provisional note from Mission 000 |
| --- | --- | --- |
| 2026-10-24 track 5 frame 73 | 40 MHz HH+HV | `NISAR_L2_PR_GCOV_034_005_D_073_4005_DHDH_A_20261024T132237_20261024T132311_P05036_N_F_J_001` |
| 2026-10-31 track 106 frame 73 | 40 MHz HH+HV | Outside, inferred from the provisional track-106 geometry |
| 2026-11-01 track 127 frame 17 | 40 MHz HH+HV | `NISAR_L2_PR_GCOV_034_127_A_017_4005_DHDH_A_20261101T235631_20261101T235705_P05036_N_F_J_001` |
| 2026-11-05 track 5 frame 73 | 20 MHz quad-pol | `NISAR_L2_PR_GCOV_035_005_D_073_2005_QPDH_A_20261105T132237_20261105T132312_P05036_N_F_J_001` |
| 2026-11-09 track 55 frame 17 | 40 MHz HH+HV | Outside the test point by bounding box |

No pair in this table shares track, frame, bandwidth, polarization, and CRID. That is why the approved comparison stays on provisional P05023.

## GUNW and GOFF

Validated counts were zero. Provisional products exist and are excluded from the first slice. One provisional GUNW id connects the two Group D40 dates 20 July and 13 August and is labeled 40 MHz HH:

`NISAR_L2_PR_GUNW_026_005_D_073_028_4000_SH_20260720T132238_20260720T132312_20260813T132236_20260813T132311_P05023_N_F_J_001`

Other provisional pairs join dates whose GCOV bandwidths differ. Coherence was not measured. This id is a catalogue fact, not a deformation result.

## S-band

ISRO's 24 July 2026 note says systematic S-band products on Bhoonidhi start with cycle 25 on 8 July 2026, at baseline v1.4.0, CRID P00500, with residual banding and possible residual RFI. No granule id for Kuwari was retrieved. Access requires a Bhoonidhi account. Status: blocked.

## Prior research that RIVET does not redo

Ghoke and colleagues, *Discover Geoscience*, 5 September 2026, report optical reconstruction for 2013–2025, Sentinel-1 SBAS for October 2014–September 2024, field geology, MOI 3.82, an HDSI instability class, a lake on the order of 1,130 m by 100 m, a debris dam on the order of 60 m by 58 m by 40 m, a DEM-based volume of about 3.7 million m³, and a HEC-RAS 6.7 scenario with about 15 m/s near the breach. The paper says the simulation cannot currently be validated, reports poor InSAR coherence, and states that the supporting NRSC data are available on request rather than posted openly.

The stream is called Shambhu in that paper and Baura gad in the 2022 NDEM note. Both place it as a Pindar tributary. RIVET keeps the discrepancy until a hydrographic source resolves it.

RIVET's distinct job is the 2026 NISAR evidence chain: provenance, comparability, uncertainty, and human review. It is not a second optical history and not a second breach model.

## Local environment observed during Mission 000

The scientific queries were run from `C:\Users\pc\OneDrive\Desktop\Nasa hackathon`, which was empty and not a Git repository. Toolchain notes are in ADR-002. Disk C had about 157 GB free. QGIS was not on PATH. `gh` was not installed. GDAL was not on PATH. Those facts were not rechecked in Mission 001. The repository itself now lives at `C:\Projects\RIVET`.
