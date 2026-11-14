# Water-candidate method

Mission 004 designs a screen for open-water-like radar responses. It does not measure the Kuwari lake. The prototype in `tools/water_candidate.py` was run only on synthetic arrays. A passing test shows that the rules are deterministic. It is not an accuracy figure for the September 2026 crops.

## Acceptance criteria

The prototype meets this mission when all of the following hold:

1. Source comparisons use linear gamma0. A dB value is a separate derived feature.
2. Invalid samples, NoData, and non-positive power never become candidates.
3. A smooth low-backscatter patch can become a candidate under an explicit parameter set.
4. Brighter wet-soil-like, vegetation-like, debris-like, and extreme values do not, under that same set.
5. Patches smaller than the stated minimum mapping unit are removed.
6. A pixel just above a power limit is not a candidate, and a pixel at the limit can be.
7. Arrays with different shapes are rejected instead of resampled.
8. Invalid pixels are excluded from gain and loss counts.
9. A sensitivity tally counts parameter sets. It does not emit a confidence percentage.
10. The real Kuwari rasters are not classified by this mission.

`tests/scientific/test_water_candidate_synthetic.py` is the evidence for items 2 through 9. Item 10 is the scope of this mission.

## What the inputs are

The approved pair is provisional CRID P05023, Group D40: descending track 5, frame 73, Frequency A 40 MHz, HH+HV. The measurement sources are the September 6 and September 30 GCOV layers `HHHH`, `HVHV`, and `numberOfLooks`, plus the GCOV valid-samples subswath mask. The GSLC valid-samples subswath mask is a companion validity layer only.

The ASF GCOV guide describes HHHH and HVHV as gamma0 power after radiometric terrain correction, and it describes the GCOV mask as information about the adaptive multi-looking ensemble ([GCOV](https://nisar-docs.asf.alaska.edu/gcov/)). Mission 003 copied the product attribute "Valid samples subswath mask" from both the GCOV and GSLC crops. Value 0 is an invalid or partially focused sample, a positive code is a subswath number for a valid sample, and 255 is outside the acquisition extent. Neither mask is water, shadow, or layover.

Mission 003 kept the native grids. The GCOV crops are 10 m posting in EPSG:32644. The GSLC crops are 5 m posting on a nested grid and were not resampled. This method does not resample them either.

Mission 003 recorded the September 6 HHHH crop, in linear power, with minimum 0.000353, 1st percentile 0.0263, median 0.305, and maximum 37714.5 (`data/manifests/mission003_raster_qc.json`). Those numbers describe that crop. They are not a water threshold. The same manifest records row-mean dB profiles spanning roughly -6.1 dB to -3.8 dB, with a largest adjacent step of about 0.53 dB. That profile is a quality observation, not a classified band.

## Approaches considered

### HH threshold

Calm open water often has low co-polar backscatter, so an upper bound on HHHH is the simplest screen. The assumption is that the water surface is smooth relative to the L-band wavelength and that the pixel is not dominated by something brighter. Wet soil, smooth bare ground, radar shadow, and a loose threshold all produce the same low HH. Wind and debris raise HH and can hide water. A single HH bound cannot separate those cases.

### HV threshold

The NISAR wetland notebook says HV is often a more reliable open-water indicator than HH, because cross-polar return from a smooth surface is weak, while vegetation raises HV through volume scattering (Chapman and colleagues, NISAR wetland inundation notebook, ASF OpenSARlab early-adopter workshop, October 2024, https://github.com/ASFOpenSARlab/NISAR-Early-Adopters-Workshop-Oct-2024/blob/main/NISAR_ATBD_wetlands.ipynb). The assumption fails for wind-roughened water, sloped terrain, and residual calibration structure. Low HV is also expected from dry smooth soil. HV alone is not a water class.

### HH and HV together

Requiring both polarizations to be low rejects vegetation that is dark in HH but bright in HV, and it rejects some bright debris. It still accepts any surface that is dark in both channels, including wet soil and unscreened radar shadow. This is the combination implemented below.

### Ratio and product features

The same notebook classifies open water from the product HH×HV, with example bounds 0.000001 and 0.0001, and it says those thresholds are to be calibrated with other data. It uses HH/HV for inundated vegetation, where double-bounce can brighten HH relative to HV. A separate cloud-workflow note reports open water where mean HH×HV was below 0.00005 at Yucatan Lake, Louisiana, from a short SLC time series, and inundated vegetation where mean HH exceeded 0.5 or HH/HV exceeded 8 (Chapman and colleagues, 2024, OSTI 2441094, https://www.osti.gov/servlets/purl/2441094).

Those numbers belong to other sites, other processing, and, in the notebook, to a time-series mean after a relative-calibration step. They are not adopted here. On the September 6 Kuwari HHHH crop, the 1st percentile is already 0.026, so a product gate near 0.0001 sits far below the crop's central distribution. Copying it would be an untested extrapolation. A cross-polar ratio HV/HH can still be used as an optional gate: a high ratio is more consistent with volume scattering than with a smooth surface. The gate is optional because wind, incidence, and calibration can change it.

### Local context

A minimum connected-patch size removes isolated dark pixels. Four-connected patches are used so that diagonal contact does not join patches. The assumption is that a mapped candidate should be larger than one posted sample. The weakness is that a real narrow water body can be removed, and a broad dark hillslope can be kept. Context here is only patch size. It is not a terrain model.

### Multi-threshold sensitivity

Running the same screen across a set of power limits, look limits, and patch sizes shows which pixels flip. That is algorithmic sensitivity. It is not a probability, a confidence interval, or a skill score. No such percentage is computed.

Sentinel-1 C-band VV thresholds are not used. This product is L-band gamma0 in HH and HV, radiometrically terrain corrected, provisional, and acquired over steep terrain. A C-band decibel habit would not transfer with a stated error budget.

## Proposed screen

`tools/water_candidate.py` labels each pixel as invalid (`-1`), valid non-candidate (`0`), or candidate (`1`).

A pixel is valid only when all of these hold:

- The GCOV mask code is a positive subswath code. Codes 0 and 255 are invalid.
- If a same-grid GSLC validity mask is supplied, its code is also a positive subswath code. The function does not resample. The real 5 m GSLC crop must not be passed to this function until a later mission approves an alignment method.
- HHHH and HVHV are finite and strictly positive.
- `numberOfLooks` is finite and strictly greater than zero, and it is at least `min_looks`. `min_looks=0` does not accept a zero-look sample.

A valid pixel is a raw candidate when HHHH is at most `hh_max_linear`, HVHV is at most `hv_max_linear`, and, if `max_hv_over_hh` is set, HVHV/HHHH is at most that ratio. Raw candidates are then grouped into four-connected patches. A patch smaller than `min_patch_pixels` is returned to the valid non-candidate class.

The two dates are compared only where both labels are valid. The classes are persistent candidate, gained candidate, lost candidate, and valid non-candidate. An invalid pixel on either date is excluded from the change counts so that a NoData boundary is not called a shoreline change.

`linear_to_db` and `db_to_linear` exist so a reviewer can state a limit in decibels and convert it once. The comparison itself stays in linear power. The source arrays are not modified.

The synthetic parameter set used in the tests is HH at most 0.05, HV at most 0.02, at least 2 looks, at least 2 pixels, and HV/HH at most 0.5. Those numbers were chosen so the fixtures separate. They are not a recommended threshold for Kuwari.

## Confounders

| Confounder | What the screen does | What remains unresolved |
| --- | --- | --- |
| Wet soil and moisture | A brighter HH fails the HH limit. A dark wet surface passes. | Two dates cannot separate a moisture change from a shoreline change. |
| Wind-roughened water | Raised HH or HV can remove real water. | No wind or roughness observation is in the approved inputs. |
| Vegetation | High HV, or a high HV/HH ratio when that gate is on, rejects the pixel. Water under a canopy is missed. | Inundated vegetation would need the brighter HH and HH/HV logic from the wetland notebook, which this screen does not implement. |
| Debris and sediment | Bright returns fail the upper bounds. Dark debris can pass. | The Mission 003 bright cluster is a quality issue, not a debris map. |
| Incidence geometry | Not used. | Incidence is not in the approved crops. A later extraction would be a new mission. |
| Layover and shadow | Not detected. Dark shadow can pass the low-power rules. | The current masks do not provide this screen. A terrain method may be proposed later. It is not available and it is not validated. |
| Residual RFI and banding | Not detected automatically. | Provisional joint-mode 40 MHz products can retain residual radiometric structure. The Mission 003 row-profile step of about 0.53 dB is a reason to vary limits by at least 1 dB before calling a candidate stable. |
| Provisional calibration | The CRID stays on every record. | P05023 is not mixed with P05036. Relative calibration between these two dates was not estimated. |
| Number of looks | Samples below `min_looks` are invalid. | Looks vary with topography. A higher look count is not a confidence score. |
| NoData and invalid samples | They stay invalid and are excluded from change classes. | A candidate touching an invalid edge has an incomplete neighborhood. |
| Posting versus resolution | The minimum unit is a pixel count. | 10 m posting is not a 10 m resolution. Adaptive multi-looking mixes a changing number of radar samples. |

## Known failure modes

- Radar shadow and smooth wet ground are accepted whenever they are dark in both polarizations.
- Open water is rejected when wind, debris, or vegetation raises either polarization, or when the patch is smaller than the mapping unit.
- A one-pixel shift in a power limit changes pixels that sit on that limit. The sensitivity tally is the record of that instability.
- The sensitivity tally is 0 both for a valid non-candidate and for a pixel that was invalid. The validity label from the screen has to be read with it.
- Two dates with no terrain screen cannot support a lake-area or a confirmed shoreline.
- The synthetic suite cannot estimate those errors on the Kuwari crops.

## Sensitivity design

For a later experiment, repeat the screen over a predeclared set:

- HH and HV upper bounds stepped by 1 dB, converted to linear power before the comparison. One decibel is larger than the 0.53 dB adjacent row-profile step recorded for the September 6 HHHH crop.
- The HV/HH gate on and off.
- `min_looks` at the values the experiment declares, including the value 2 used in the synthetic suite and a stricter value near the crop's typical look count. The September 6 crop mean of `numberOfLooks` is about 4.71. That mean is not a threshold.
- `min_patch_pixels` at 1, 4, and 9. At 10 m posting those counts label 1, 4, and 9 posted samples. They are not resolution claims. The published lake width is on the order of ten posted samples, and the published debris dam is smaller than that (`docs/science/limitations.md`).

A pixel is sweep-stable only when it is a candidate in every set and valid in every set. A pixel that flips is a threshold-edge observation. Report the counts of stable and edge pixels. Do not divide those counts into a confidence percentage. Algorithmic sensitivity is the flip under declared parameters. Scientific uncertainty also includes shadow, moisture, wind, calibration, and geolocation, which this sweep does not measure.

## Synthetic evidence

The suite `tests/scientific/test_water_candidate_synthetic.py` checks the behaviors listed in the acceptance criteria: a low-backscatter patch, wet-soil-like and vegetation-like and debris-like and extreme values, invalid masks, NoData, low looks, a same-grid GSLC rejection, small patches, a value just above the limit, the ratio gate, separate dB conversion, mismatched shapes, change classes, and a two-set sensitivity count. The run recorded with this mission is 11 synthetic tests plus the existing 15 catalogue tests, all passing. That result is a software check.
