# Mission 007 — Human review and independent evidence

This mission checks the Mission 006 count rasters and turns the small, reconstructible candidate groups into review records. It does not change the Mission 005 parameter domain, rerun the classifier, or assign a confirmed water label, an area, or a shoreline.

The machine-readable record is `data/manifests/mission007_review_manifest.json`. The checker is `tools/mission007_review.py`. Tests are `tests/scientific/test_mission007_review.py`.

Starting point: Git `main` at `a7fadb9d6c144d856563f310c4ada26c18e70c83`, the same commit as `origin/main`. The working tree was clean before this mission. The twelve Mission 006 rasters were already on disk under `data/derived/mission006/` and were opened read-only. They were not rewritten.

Review timestamp: 2026-11-14T14:59:02Z.

## Checksum and grid verification

All 12 Mission 006 rasters matched the SHA-256 values in `data/manifests/mission006_sweep_manifest.json`. Each raster is Int16, EPSG:32644, 1171 by 1343, geotransform `(379470, 10, 0, 3336070, 0, -10)`, with a non-empty band description. That geotransform matches the Mission 006 product grid. It was not independently surveyed, so the inventory below uses crop row and column, origin at the upper left.

Recomputed counts match the Mission 006 date blocks:

- No candidate count exceeds the valid count.
- No filtered count exceeds the raw count.
- No count exceeds 1092.
- Filtered stability code 2 has 0 pixels on both dates.
- Raw stability code 2 has 6 pixels on 2026-09-06 and 12 pixels on 2026-09-30.
- Filtered stability code 1 has 88 pixels on 2026-09-06 and 129 pixels on 2026-09-30.

Verification passed. No discrepancy stopped the inventory.

## How a review patch was defined

Four-connected components were built separately for three classes:

- Raw stability code 2: valid in all 1092 sets and a raw candidate in all 1092 sets.
- Filtered stability code 2: the same rule after the patch filter. This class is empty.
- Filtered stability code 1: a filtered candidate in every set where the pixel is valid, but not valid in every set.

Diagonal pixels stay separate. A bounding box can contain pixels of another class. `pixel_count` is the component, not the rectangle. The parameter-sensitive class (filtered stability code 0) is summarized and is not listed as review patches.

| Date | Filtered code 0 pixels | Components | Largest component | Median component size |
| --- | ---: | ---: | ---: | ---: |
| 2026-09-06 | 84,468 | 18,853 | 916 | 1 |
| 2026-09-30 | 108,830 | 24,991 | 787 | 1 |

None of the 23 review components touch a validity-code `-1` pixel or the raster edge.

A read of the stored Mission 003 `numberOfLooks` crops, at these class pixels only, gives:

| Date | Class | Pixels | Looks minimum | Looks maximum |
| --- | --- | ---: | ---: | ---: |
| 2026-09-06 | raw code 2 | 6 | 2.0266547203063965 | 6.383866786956787 |
| 2026-09-06 | filtered code 1 | 88 | 0.01516193151473999 | 1.9356980323791504 |
| 2026-09-30 | raw code 2 | 12 | 2.0277576446533203 | 6.3839826583862305 |
| 2026-09-30 | filtered code 1 | 129 | 0.009020080789923668 | 1.962552785873413 |

Every filtered code 1 pixel in the inventory has raw and filtered selection count 546. That is half of 1092, the split between `min_looks` 0 and `min_looks` 2. Their stored looks lie strictly between 0 and 2, so they fail the floor of 2 and pass the floor of 0. They remain filtered candidates in each set where they are valid. The raw code 2 pixels have looks above 2, so both floors can accept them, and their filtered counts are lower than 1092 because the patch filter removes them from some sets.

## Region inventory

Coordinates are inclusive row and column bounds. Selection counts are out of 1092. No component is a lake.

### 2026-09-06, raw fully sweep-stable

| Identifier | Rows | Columns | Pixels | Raw count | Filtered count |
| --- | --- | --- | ---: | ---: | ---: |
| R007-20260906-raw_fully_sweep_stable-001 | 30–30 | 37–37 | 1 | 1092 | 737 |
| R007-20260906-raw_fully_sweep_stable-002 | 147–147 | 631–631 | 1 | 1092 | 767 |
| R007-20260906-raw_fully_sweep_stable-003 | 478–478 | 182–182 | 1 | 1092 | 728 |
| R007-20260906-raw_fully_sweep_stable-004 | 571–571 | 185–185 | 1 | 1092 | 524 |
| R007-20260906-raw_fully_sweep_stable-005 | 1208–1208 | 147–147 | 1 | 1092 | 644 |
| R007-20260906-raw_fully_sweep_stable-006 | 1215–1215 | 172–172 | 1 | 1092 | 810 |

### 2026-09-06, filtered candidate whenever valid

| Identifier | Rows | Columns | Pixels | Raw count | Filtered count |
| --- | --- | --- | ---: | ---: | ---: |
| R007-20260906-filtered_candidate_in_every_valid_set_but_partially_valid-001 | 145–150 | 635–642 | 26 | 546 | 546 |
| R007-20260906-filtered_candidate_in_every_valid_set_but_partially_valid-002 | 475–480 | 182–185 | 16 | 546 | 546 |
| R007-20260906-filtered_candidate_in_every_valid_set_but_partially_valid-003 | 518–520 | 549–555 | 15 | 546 | 546 |
| R007-20260906-filtered_candidate_in_every_valid_set_but_partially_valid-004 | 1218–1222 | 178–191 | 31 | 546 | 546 |

### 2026-09-30, raw fully sweep-stable

| Identifier | Rows | Columns | Pixels | Raw count | Filtered count |
| --- | --- | --- | ---: | ---: | ---: |
| R007-20260930-raw_fully_sweep_stable-001 | 258–258 | 151–151 | 1 | 1092 | 652 |
| R007-20260930-raw_fully_sweep_stable-002 | 474–476 | 178–178 | 3 | 1092 | 893 |
| R007-20260930-raw_fully_sweep_stable-003 | 476–477 | 182–182 | 2 | 1092 | 728 |
| R007-20260930-raw_fully_sweep_stable-004 | 478–478 | 186–186 | 1 | 1092 | 803 |
| R007-20260930-raw_fully_sweep_stable-005 | 546–546 | 69–69 | 1 | 1092 | 634 |
| R007-20260930-raw_fully_sweep_stable-006 | 840–840 | 259–259 | 1 | 1092 | 766 |
| R007-20260930-raw_fully_sweep_stable-007 | 1208–1208 | 147–147 | 1 | 1092 | 650 |
| R007-20260930-raw_fully_sweep_stable-008 | 1214–1215 | 172–172 | 2 | 1092 | 903 |

### 2026-09-30, filtered candidate whenever valid

| Identifier | Rows | Columns | Pixels | Raw count | Filtered count |
| --- | --- | --- | ---: | ---: | ---: |
| R007-20260930-filtered_candidate_in_every_valid_set_but_partially_valid-001 | 142–149 | 633–642 | 37 | 546 | 546 |
| R007-20260930-filtered_candidate_in_every_valid_set_but_partially_valid-002 | 474–477 | 182–187 | 12 | 546 | 546 |
| R007-20260930-filtered_candidate_in_every_valid_set_but_partially_valid-003 | 476–477 | 181–181 | 2 | 546 | 546 |
| R007-20260930-filtered_candidate_in_every_valid_set_but_partially_valid-004 | 517–522 | 549–555 | 27 | 546 | 546 |
| R007-20260930-filtered_candidate_in_every_valid_set_but_partially_valid-005 | 1217–1223 | 178–192 | 51 | 546 | 546 |

Several bounding boxes sit near one another, especially around rows 474–480 and rows 1208–1223. They are separate components and separate classes. This mission does not difference the two dates and does not call a shared location a persistent lake.

## Independent evidence

No source below was used to change a threshold. Same-date optical and terrain rasters were not downloaded.

| Source | What it covers | Overlap with these pixels and dates | Limitation |
| --- | --- | --- | --- |
| Ghoke and colleagues, Discover Geoscience, DOI `10.1007/s44288-026-00717-w`, published 2026-09-05 | Kuwari landslide, optical scenes 2013–2025, Sentinel-1 SBAS through October 2024, and a HEC-RAS scenario | Same valley, historically. Not 2026-09-06 or 2026-09-30. | Their lake lengths and volume are prior results, not a measurement of these pixels. |
| Bisht and colleagues, 2022, DOI `10.1007/s12594-022-1927-3` | Geological note on Kuwari Lake | Same valley, years earlier. | Cannot accept or reject a September 2026 pixel. |
| SANDRP, 22 November 2024 | Secondary note. Study point 30.088337 N, 79.808685 E. | The point was already used to choose the catalogue window. | Not a survey and not imagery of these dates. |
| Sentinel-2 MSI L2A, Copernicus Data Space | Global 10 m optical tiles. September 2026 acquisition plans exist. | A scene query for these two dates was not run. No tile identifier is claimed. | One L2A tile is commonly several hundred megabytes to about a gigabyte. |
| Landsat 8/9 Collection 2 Level-2, DOI `10.5066/P9OGBGM6` | 30 m optical scenes | Path, row, and scene were not resolved. | Coarser than the 10 m GCOV posting. No scene was downloaded. |
| Copernicus DEM GLO-30, 2021 public DSM | About 30 m posting, static | A crop of the diagnostic window would be a few hundred pixels on a side, on the order of a few megabytes. It was not downloaded. | A DSM is not an observation on either NISAR date and is not a water label. CartoDEM is not an open default. SRTM 30 m was not downloaded. |

## Terrain ambiguity

The crops do not contain a local incidence-angle layer. Look direction Left and descending orbit were already known from product metadata. That is not enough to map radar shadow or layover.

The GCOV and GSLC valid-samples masks are subswath masks. Code 0 is invalid or partially focused. A positive code is a valid subswath. They are not a terrain, water, shadow, or layover classification. The ASF product-overview wording that still mentions water and shadow-layover remains unresolved and was not used here.

A later terrain mission would need, before any candidate map is consulted:

1. One named DEM, with posting, vertical datum, and a size for the diagnostic window.
2. NISAR orbit geometry and an incidence or range-azimuth layer taken from the source product.
3. A forward shadow and layover calculation on that DEM in radar geometry.
4. A validation target that is a known non-water feature, chosen before the candidate rasters are compared.
5. A rule that the shadow model is not fitted to the Mission 006 counts and cannot by itself create a water label or an area.

## Review records

The schema allows four decisions: `accept_unresolved_water_candidate`, `reject_likely_non_water_or_confounder`, `request_independent_evidence`, and `unresolved_insufficient_evidence`. Each record forces `confirmed_water`, `area_estimated`, and `shoreline_estimated` to false. An unknown decision is rejected.

All 23 components are recorded as `request_independent_evidence`. No reviewer has accepted or rejected a patch. The recorded reason is that no same-date optical or terrain observation was retrieved.

## Tests

`tests/scientific/test_mission007_review.py` checks count inequalities, four-connected separation, boundary and invalid-pixel flags, evidence fields, the ban on using evidence to retune thresholds, and the ban on a review decision confirming water.

On uv CPython 3.12.13, the scientific suite ran 85 tests: 82 passed and 3 skipped because that interpreter has no NumPy. The 7 Mission 007 tests passed. On OSGeo4W Python 3.12.16, `test_mission006_sweep` and `test_mission007_review` together ran 13 tests and all passed, including the NumPy-dependent Mission 006 tests.

## Unresolved questions

- Whether any review component is water, radar shadow, layover, or another dark surface.
- Whether a cloud-free Sentinel-2 or Landsat scene exists for 2026-09-06 or 2026-09-30 over this window.
- What local incidence, slope, aspect, and relief are at these row and column positions.
- Filename fidelity `N` versus internal `orbitType` `MOE`.
- The conflict between the GSLC valid-samples mask and the ASF overview sentence about water and shadow-layover.
- The two dates were not compared. Nearness in row and column is not persistence.

## Recommended next mission

Query Sentinel-2 and Landsat catalogues for 2026-09-06 and 2026-09-30 over the diagnostic window. Record scene identifiers, cloud cover, and whether a scene actually overlaps the crop. Do not download a full tile until a scene is named and its size is stated. Do not retune the 1092-set domain, and do not calculate area or a shoreline.

A DEM shadow and layover test stays a separate mission, with the inputs above. It should not be folded into the optical query, and it should not relabel these candidates.
