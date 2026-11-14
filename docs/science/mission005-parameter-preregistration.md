# Mission 005 — Parameter preregistration proposal

This document proposes a parameter domain for a later water-candidate experiment. It does not classify the Kuwari pixels, and it does not select a threshold by looking at a candidate map.

The screen remains the Mission 004 rule: a pixel is a candidate only when it is valid and both HH and HV linear gamma0 are at or below the supplied limits, with an optional HV/HH ratio gate and a minimum connected-patch size. Limits are compared in linear power. Mission 005 changed `sensitivity()` so it returns `SensitivityResult`, with separate validity, raw-candidate, and filtered-candidate counts. An invalid pixel is not counted as a non-candidate.

## Proposed HH and HV limits

The dark tail of both dates is the relevant range for an upper-limit screen. The bulk of each crop sits near the median, about -5 dB in HH and -10 to -11 dB in HV. A limit at the median would accept about half of the valid samples. The proposal therefore stops at the 10th percentile, rounded outward to an integer decibel, and starts one integer decibel below the darker date's 0.1 percentile.

HH, both dates, 1 dB steps from -22 dB through -10 dB:

| dB | Linear gamma0 |
| ---: | ---: |
| -22 | 6.30957344e-03 |
| -21 | 7.94328235e-03 |
| -20 | 1.00000000e-02 |
| -19 | 1.25892541e-02 |
| -18 | 1.58489319e-02 |
| -17 | 1.99526231e-02 |
| -16 | 2.51188643e-02 |
| -15 | 3.16227766e-02 |
| -14 | 3.98107171e-02 |
| -13 | 5.01187234e-02 |
| -12 | 6.30957344e-02 |
| -11 | 7.94328235e-02 |
| -10 | 1.00000000e-01 |

HV, both dates, 1 dB steps from -28 dB through -15 dB:

| dB | Linear gamma0 |
| ---: | ---: |
| -28 | 1.58489319e-03 |
| -27 | 1.99526231e-03 |
| -26 | 2.51188643e-03 |
| -25 | 3.16227766e-03 |
| -24 | 3.98107171e-03 |
| -23 | 5.01187234e-03 |
| -22 | 6.30957344e-03 |
| -21 | 7.94328235e-03 |
| -20 | 1.00000000e-02 |
| -19 | 1.25892541e-02 |
| -18 | 1.58489319e-02 |
| -17 | 1.99526231e-02 |
| -16 | 2.51188643e-02 |
| -15 | 3.16227766e-02 |

Linear values are `10 ** (dB / 10)`, the same conversion as `db_to_linear` in `tools/water_candidate.py`.

The observed HH 0.1 percentiles are -21.21 dB and -21.28 dB. The observed HH 10th percentiles are -10.00 dB and -10.36 dB. The observed HV 0.1 percentiles are -26.46 dB and -27.10 dB. The observed HV 10th percentiles are -15.48 dB and -16.40 dB. Integer rounding outward puts those four percentiles inside the sets.

A product gate near 1e-4 linear power, about -40 dB, sits below the darkest finite HH sample in either crop (-34.52 dB and -32.12 dB). This audit does not adopt that gate.

## Ratio gate

The core sweep sets `max_hv_over_hh` to null, so the ratio gate is off.

Turning the gate on requires one positive finite ratio. This audit did not compute the joint HV/HH distribution, and a number taken from the synthetic fixture would not be a property of these crops. The on-state is reserved for an architect-supplied ratio. It is not part of the 1092-member core.

## Minimum looks

Two settings:

1. `min_looks = 0`. This admits every finite looks value. The parameter validator allows zero. It is the inclusive baseline.
2. `min_looks = 2`. The 25th percentile of valid `numberOfLooks` is 2.172 on both dates, and the 10th percentile is 0.812. The value 2 is the integer at or just below that 25th percentile. It is a sensitivity setting. It is not a claim that fewer than two looks are bad data, and it is not a confidence score.

## Patch size

`min_patch_pixels` of 1, 4, and 9. These are the sizes required for the later experiment. Four-connected components smaller than the chosen size are removed from the filtered label and retained in the raw label. Patch size 1 keeps the raw decision.

## Combination count

Core, ratio off:

`13 HH limits × 14 HV limits × 2 look settings × 3 patch sizes = 1092` parameter sets per date.

If the architect supplies one ratio and the sweep is repeated with the gate on, the count doubles to 2184 per date.

## Computational feasibility

The crops are 1171 by 1343, which is 1,572,653 pixels. A synthetic timing of `screen_detailed` on an 80 by 80 uniform array took 0.0116 seconds, about 551,000 pixels per second on this machine. Scaled to one crop, one parameter set is about 2.9 seconds. The 1092-member core is then about 53 minutes per date, and about 1.8 hours for both dates. Adding one ratio doubles that estimate.

This timing is an extrapolation from a uniform synthetic array. The connected-component cost depends on the candidate pattern, which was not measured on these crops. The estimate is unverified for the real rasters. The sweep was not run.

## What is data-derived, assumed, or awaiting approval

| Choice | Status |
| --- | --- |
| HH and HV brackets follow the observed 0.1 and 10th percentiles of these two crops | Data-derived |
| Same integer-dB set for both dates | Data-derived from the two crops together, so the later comparison stays in one domain |
| 1 dB spacing | Declared sensitivity step. It is wider than the mean-of-dB row step of about 0.53 dB. It is not derived by inspecting a candidate map |
| Outward rounding to integer dB, including -22 dB and -28 dB | Assumption, one step past the observed percentile |
| Ratio gate off in the core | Choice, because no joint ratio distribution was audited |
| A numeric ratio for the on-state | Requires architect approval. Not proposed here |
| `min_looks` of 0 and 2 | 0 is the inclusive baseline. 2 sits at the observed 25th percentile. Both need acceptance as the declared pair |
| Patch sizes 1, 4, and 9 | Declared by the mission, not estimated from a cluster |
| Whether the 10th percentile is too far into the bulk | Requires architect approval before the sweep runs |

## What this proposal does not claim

No limit in the tables is a water threshold. The later experiment, if approved, still has to report validity and candidate-stability classes, keep raw and filtered labels distinct, avoid resampling the GSLC mask, and leave area and shoreline uncomputed until a separate approved mission.
