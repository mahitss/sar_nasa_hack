# Measurement protocol for a water-candidate experiment

This protocol defines how a later experiment may apply the Mission 004 screen. It does not authorize a lake boundary, an area, or a confirmed change. Mission 004 did not run the screen on the Kuwari rasters.

The algorithm and its failure modes are in `docs/science/water-candidate-method.md`. The implementation is `tools/water_candidate.py`.

## Provenance

| Item | Required record |
| --- | --- |
| Dates | 6 September 2026 and 30 September 2026 |
| GCOV granules | The counter-001 P05023 granules already inspected in Mission 003 |
| GSLC granules | 6 September counter 002 and 30 September counter 001, CRID P05023 |
| Layers | GCOV `HHHH`, `HVHV`, `numberOfLooks`, and valid-samples mask; GSLC valid-samples mask as a companion record only |
| Comparability | Track 5, frame 73, descending, Frequency A 40 MHz, HH+HV, CRID P05023 on every record |
| Units | Linear gamma0 for HHHH and HVHV. dB features are derived and stored separately |
| Grid | GCOV crops stay on their native 10 m EPSG:32644 grid. The GSLC 5 m mask is not resampled onto that grid |
| Checksums | Recompute each crop checksum and match `data/manifests/mission003_raster_qc.json` and `data/manifests/mission003_gslc_mask_qc.json` before use |
| Orbit labels | Filename code `N` and internal `orbitType` `MOE` stay separate and unresolved |

P05023 is provisional. It is not mixed with P05036.

## Valid-pixel rule

On the GCOV grid, a pixel enters the screen only when:

1. The GCOV mask is a positive subswath code. Codes 0 and 255 are invalid.
2. HHHH and HVHV are finite and strictly positive.
3. `numberOfLooks` is finite and at least the declared `min_looks`.

The real GSLC mask is not applied pixel by pixel. Its grid does not match the GCOV crop, and resampling is outside this protocol. The prototype accepts a same-grid GSLC mask only for a synthetic fixture. A later alignment method would be a separate mission.

Invalid pixels remain invalid. They are not candidates, and they are excluded when two dates are compared.

## Feature definitions

For each valid pixel, retain the linear powers and derive:

- `HHHH_dB = 10 * log10(HHHH)`
- `HVHV_dB = 10 * log10(HVHV)`
- `hv_over_hh = HVHV / HHHH`

Do not replace the linear GeoTIFFs with dB rasters. Do not multiply by `rtcGammaToSigmaFactor`. Do not form beta0 or sigma0 in this protocol.

## Candidate rule

Declare one `CandidateParameters` set before looking at the result. A valid pixel is a raw candidate when HHHH and HVHV are each at or below their declared linear limits and, if the ratio gate is on, `hv_over_hh` is at or below its declared limit. Four-connected patches smaller than `min_patch_pixels` are removed.

The output class is `water_candidate`. It is not confirmed water. The synthetic limits in the unit tests are fixture values, not the limits for Kuwari.

## Minimum mapping unit and boundaries

The minimum mapping unit is `min_patch_pixels` posted samples, reported together with the 10 m posting. Posting is not resolution. Adaptive multi-looking means neighbouring samples are not independent observations.

A candidate that touches an invalid pixel is kept only as a candidate with an incomplete neighborhood. The protocol records that edge. It does not fill NoData and it does not grow the patch across the invalid pixel.

## Two-date comparison

Where both dates are valid, label each pixel as one of:

- persistent candidate
- gained candidate, present only on 30 September
- lost candidate, present only on 6 September
- valid non-candidate on both dates

Where either date is invalid, label the pixel excluded. Do not call the excluded set a shoreline. Do not convert pixel counts to area.

## Sensitivity procedure

Run the screen on a predeclared collection of parameter sets:

1. Step both power limits by 1 dB around the declared set, and convert each dB step to linear power before comparison.
2. Repeat with the HV/HH gate on and off.
3. Repeat `min_looks` at the declared value and at one stricter value.
4. Repeat `min_patch_pixels` at 1, 4, and 9.

The 1 dB step is larger than the 0.53 dB adjacent row-profile step recorded for the September 6 HHHH crop. A pixel is sweep-stable when it is valid and a candidate in every set. Any other selected pixel is a threshold-edge pixel. Report both counts. Do not turn the tally into a confidence percentage. The tally does not measure shadow, moisture, wind, calibration, or geolocation error.

## Quality-control checks before review

- Both dates still share EPSG:32644, the 10 m spacing, and the Mission 003 crop geotransform.
- Mask values outside the documented set 0, positive subswath codes, and 255 are listed and left unclassified.
- The maximum and the bright cluster recorded in Mission 003 are not given a physical label by this protocol.
- No sigma0 conversion and no GSLC resampling occurred.
- The parameter set and the sensitivity collection are written in the experiment record before the candidate map is interpreted.
- The output is still named `water_candidate`.

## Human review

A reviewer sees the candidate map, the excluded pixels, the sweep-stable and threshold-edge counts, and the two gamma0 images. The reviewer may:

- Accept a candidate patch as a water candidate that still lacks a terrain-shadow screen.
- Reject a patch. Reasons that are sufficient on their own include: the patch sits where radar shadow or layover is plausible, the patch disappears in the 1 dB sweep, the patch is an isolated dark pixel after the mapping unit is applied, the patch follows a radiometric band, or the supporting looks are too few for the reviewer even though they passed `min_looks`.
- Request more evidence. Optical imagery, a terrain screen, incidence angle, or another comparability group are requests, not results of this protocol. Ascending track 127 is a different geometry and is not subtracted from this pair.

Rejection and acceptance are review decisions. They are not a new classifier and they do not create an area.

## Limitations

The screen confuses dark land, wet soil, and radar shadow with a smooth water-like response. It misses water that is rough, debris-covered, vegetated, or smaller than the mapping unit. Two provisional dates do not estimate a calibration offset. The unresolved filename code `N` versus `orbitType` `MOE` means the geolocation error of this pair was not measured. No accuracy percentage is claimed.

## Unresolved decisions

- The linear power limits for this valley are not chosen. They have to come from the sensitivity collection and review, not from the Yucatan or wetland-notebook examples.
- Whether the HV/HH gate is on by default is not chosen.
- The operational `min_looks` and `min_patch_pixels` are not chosen.
- No approved method exists for terrain shadow and layover.
- Incidence angle is not in the approved crops.
- The real GSLC mask remains on its 5 m grid until an alignment mission exists.

## Gate for a later real-data experiment

**CONDITIONAL GO**, only for an experiment that runs this screen on the existing crops, publishes candidate labels rather than water or area, keeps the GSLC mask unresampled, reports the sensitivity split, and sends the result to human review. It is not a go for a confirmed shoreline or an extent.
