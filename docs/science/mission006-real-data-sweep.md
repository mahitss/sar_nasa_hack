# Mission 006 — Controlled real-data water-candidate sweep

This experiment ran the Mission 005 parameter domain on the September 6 and September 30, 2026 GCOV crops. The outputs are algorithmic candidate counts. They are not confirmed water, a lake boundary, a shoreline, or a physical change.

The machine-readable record is `data/manifests/mission006_sweep_manifest.json`. The runner is `tools/mission006_sweep.py`. Derived rasters are under `data/derived/mission006/`, which Git ignores.

## Looks rule used by the sweep

Before the crops were classified, `_valid_sample()` was corrected. `numberOfLooks` must be finite, strictly greater than zero, and greater than or equal to `min_looks`. `min_looks=0` adds no further floor. It does not accept a zero-look sample. The same rule is now stated in the Mission 005 preregistration, the water-candidate method, and the measurement protocol.

## Sources

Comparability group D40: CRID P05023, track 5, frame 73, descending, Frequency A 40 MHz, HH+HV. Filename fidelity code `N` and internal `orbitType` `MOE` stay unresolved.

| Date | Granule |
| --- | --- |
| 2026-09-06 | `NISAR_L2_PR_GCOV_030_005_D_073_4005_DHDH_A_20260906T132236_20260906T132311_P05023_N_F_J_001` |
| 2026-09-30 | `NISAR_L2_PR_GCOV_032_005_D_073_4005_DHDH_A_20260930T132236_20260930T132311_P05023_N_F_J_001` |

Every source crop matched its Mission 003 SHA-256 before the sweep and again after it. Both dates use EPSG:32644, 1171 by 1343, geotransform `(379470, 10, 0, 3336070, 0, -10)`, 10 m posting. Power and `numberOfLooks` are Float32. The mask is Byte.

GCOV mask codes are only 0 and 1. Code 0 is invalid or partially focused. Code 1 is a valid subswath. On every valid-mask pixel, HHHH and HVHV are finite and positive, and `numberOfLooks` is finite and strictly positive. The GSLC masks were not opened, resampled, or applied.

## Parameter domain

1092 sets on each date, ratio gate off. HH limits are -22 dB through -10 dB in 1 dB steps. HV limits are -28 dB through -15 dB in 1 dB steps. Linear limits are `10 ** (dB / 10)`. `min_looks` is 0 and 2. Patch sizes are 1, 4, and 9.

The ordered list is HH ascending, then HV ascending, then `min_looks` 0 then 2, then patch size 1 then 4 then 9. Its canonical SHA-256 is `d5cde564d35088cd5f4b6d8d814d247ff5cfa6eb4859f5956e49b98d27b2c6c9`.

The sweep count uses the same decisions as `water_candidate.sensitivity`. A synthetic equivalence test compares the two on a grid that includes zero looks, a sub-floor look value, NaN looks, mask codes 0 and 255, a diagonal pair, and a compact patch. The connected-component step is four-connected. Diagonal pixels are separate components. A component is removed only when it is smaller than `min_patch_pixels`.

## How to read a count

A pixel is fully sweep-stable only when it is valid in all 1092 sets and a candidate in all 1092 sets. Being a candidate in every set where it happened to be valid is a different class. Pixels with `0 < numberOfLooks < 2` are valid in the 546 sets that use `min_looks=0` and invalid in the 546 sets that use `min_looks=2`.

Stability codes in the rasters:

| Code | Meaning |
| ---: | --- |
| 2 | Fully sweep-stable |
| 1 | Candidate in every set in which the pixel was valid, but not valid in every set |
| 0 | Parameter-sensitive: candidate in some but not all valid sets |
| -1 | Never a candidate while valid |
| -2 | Invalid in every set |

Validity codes are 1, 0, and -1 for valid in all, some, and none of the sets. Counts are Int16. No count exceeds 1092, and candidate counts do not exceed valid counts.

## September 6

1,572,653 pixels. 1,568,042 are valid in at least one set. 1,203,719 are valid in all 1092 sets. 364,323 are valid in some sets. 4,611 are invalid in every set, matching mask code 0.

| Class | Raw | Filtered |
| --- | ---: | ---: |
| Fully sweep-stable | 6 | 0 |
| Candidate whenever valid, but only partially valid | 231 | 88 |
| Parameter-sensitive | 84,319 | 84,468 |
| Never selected while valid | 1,483,486 | 1,483,486 |

The filtered candidate count over valid pixels has minimum 0, median 0, 95th percentile 3, 99th percentile 75, 99.9th percentile 311, and maximum 810. The raw count maximum is 1092. Those six raw-stable pixels do not remain a candidate in every set after the patch filter. 67,230 pixels lose at least one selection to the patch filter. The filter removes 1,428,376 pixel-parameter selections.

Runtime 152.841 seconds. Tracemalloc peak 86,495,796 bytes.

## September 30

1,572,653 pixels. 1,568,054 are valid in at least one set. 1,203,757 are valid in all 1092 sets. 364,297 are valid in some sets. 4,599 are invalid in every set, matching mask code 0.

| Class | Raw | Filtered |
| --- | ---: | ---: |
| Fully sweep-stable | 12 | 0 |
| Candidate whenever valid, but only partially valid | 290 | 129 |
| Parameter-sensitive | 108,657 | 108,830 |
| Never selected while valid | 1,459,095 | 1,459,095 |

The filtered candidate count over valid pixels has minimum 0, median 0, 95th percentile 8, 99th percentile 93, 99.9th percentile 338, and maximum 903. The raw count maximum is 1092. The twelve raw-stable pixels do not remain a candidate in every set after the patch filter. 87,782 pixels lose at least one selection to the patch filter. The filter removes 1,897,971 pixel-parameter selections.

Runtime 170.750 seconds. Tracemalloc peak 87,064,203 bytes.

The two dates were not compared. No gained, lost, or persistent class was computed.

## Output checksums

Each product is Int16, 1171 by 1343, EPSG:32644, geotransform `(379470, 10, 0, 3336070, 0, -10)`.

| File | SHA-256 |
| --- | --- |
| `20260906_valid_count.tif` | `bd63d0c56ee3bc2aeadfc1d4fa0e2da5d4dbf377fa16d99ea84c30a436a9b1f3` |
| `20260906_raw_candidate_count.tif` | `c54e847401b24772b791b8b17e4f4678ee285eef38e6a9c3782c610657c5097d` |
| `20260906_filtered_candidate_count.tif` | `7046eedfab43dcdbd30aa39f7473d3bb5cdbacca43123cb83e84e62c28470e72` |
| `20260906_validity_class.tif` | `73ada88ede868e017a22e554d785aec930da736e56b466e0a7e8bd3337069bb7` |
| `20260906_raw_candidate_stability.tif` | `0aae393762b642b5cfae11cad5fceb27d96b054e3846f254feaa5a2140c433cf` |
| `20260906_filtered_candidate_stability.tif` | `68cd9f7515dc0bcba86585044ce87e829f099d3d23fa7cedfc07470a9c4d6f42` |
| `20260930_valid_count.tif` | `d3e6a244848fa3d97f8af0d7d413e572c66d6744186dcd5834477d02c524fe13` |
| `20260930_raw_candidate_count.tif` | `1599f90472aab2b5ad9b52bf7020d3265743cd5ae1929131dda4680c16ea8526` |
| `20260930_filtered_candidate_count.tif` | `d681e5a06bf6734b35ad72badce279f5b4efa937432cea49680f9f4dc5d78b38` |
| `20260930_validity_class.tif` | `4e7017fdfb977f4fed37c28b32ccec79af28100b1baae95c3aa689cfe5a9669b` |
| `20260930_raw_candidate_stability.tif` | `c23d87016d17c24a2b19b280d3707bc3896098228ec835a8654f34b817041d77` |
| `20260930_filtered_candidate_stability.tif` | `120d8447b904a015a654d4b2f0c1ef84c656fb676a04a1fa56483e1167d699ac` |

## Runtime

The Mission 005 estimate of about 1.8 hours came from scaling one small synthetic screen. It is not the observed runtime. The observed sweep took 152.841 seconds on September 6 and 170.750 seconds on September 30. The pure-Python per-pixel loop was the bottleneck that the count algebra and the run-length component filter avoid. The decisions match `sensitivity()` on the synthetic equivalence fixture.

Software: Python 3.12.16, NumPy 2.5.4, GDAL 3.13.3. The manifest timestamp is 2026-11-14T14:48:33Z.

## Limitations

Smooth wet soil can pass the screen. Radar shadow and layover can pass the screen. Wind-roughened water can fail the screen. Vegetation and debris can obscure water. Incidence geometry is not used. No terrain-shadow model is available. P05023 calibration is provisional. The orbit-label discrepancy remains unresolved. The ratio gate is off. The sweep is not a confidence score. `numberOfLooks` is not a confidence or accuracy score. Two dates cannot separate moisture change from shoreline movement.

No accuracy is claimed. Pixel counts are not an area. They were not multiplied by 100 square metres.
