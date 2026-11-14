# Mission 005 — Distribution audit

This audit describes the existing September 6 and September 30, 2026 NISAR GCOV crops. It does not classify water, estimate area, or draw a shoreline.

The machine-readable record is `data/manifests/mission005_distribution_audit.json`. The script is `tools/distribution_audit.py`. Statistics below are the analysis sample: a GCOV mask code greater than 0 and not 255, and a finite value. For power layers the value must also be positive. On these crops that sample is the same set as all finite pixels.

## Provenance

Comparability group D40: CRID P05023, track 5, frame 73, descending, Frequency A 40 MHz, HH+HV.

| Date | Product | Granule |
| --- | --- | --- |
| 2026-09-06 | GCOV | `NISAR_L2_PR_GCOV_030_005_D_073_4005_DHDH_A_20260906T132236_20260906T132311_P05023_N_F_J_001` |
| 2026-09-30 | GCOV | `NISAR_L2_PR_GCOV_032_005_D_073_4005_DHDH_A_20260930T132236_20260930T132311_P05023_N_F_J_001` |
| 2026-09-06 | GSLC | `NISAR_L2_PR_GSLC_030_005_D_073_4005_DHDH_A_20260906T132236_20260906T132311_P05023_N_F_J_002` |
| 2026-09-30 | GSLC | `NISAR_L2_PR_GSLC_032_005_D_073_4005_DHDH_A_20260930T132236_20260930T132311_P05023_N_F_J_001` |

The filename fidelity code is `N`. The internal `orbitType` is `MOE`. Those two labels stay unresolved and are not treated as the same fact.

## Checksums

Every source crop matched the SHA-256 recorded in the Mission 003 manifests, before the read and again after it. `GDAL_PAM_ENABLED` was set to `NO` and the datasets were opened read-only. The pre-existing sidecar `20260906_gcov_frequencyA_HHHH.tif.aux.xml` was already present from Mission 003 and is not part of the TIFF checksum.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `20260906_gcov_frequencyA_HHHH.tif` | 4126088 | `4bb8d2751b70c8215004a9c60b8735998f669421791653691a3a82a388ef527b` |
| `20260906_gcov_frequencyA_HVHV.tif` | 4116191 | `0ea1e7dcb3ab8e9e7af62e34c1b45d919a0254e7d3dee273addeb97a87f530b7` |
| `20260906_gcov_frequencyA_numberOfLooks.tif` | 4959182 | `ebf8924c8af37ce4e10afef7f2bb8e719df4cf1847b883a69e25651f4b635e31` |
| `20260906_gcov_frequencyA_mask.tif` | 14888 | `618cbd541b1543b861ad998c7d38b071c2ccab75e258fabf08d720b777ab2c73` |
| `20260930_gcov_frequencyA_HHHH.tif` | 4129382 | `c0255a6e14d762a6a65c0de30976d4f943d750094ea1cee1c1c12b80147cc943` |
| `20260930_gcov_frequencyA_HVHV.tif` | 4118103 | `6b7176835dd986ab3d98aab7c884b863d0ab34b341857476fcc95dcc8bacb411` |
| `20260930_gcov_frequencyA_numberOfLooks.tif` | 4959222 | `f55607d8c027c06db6868e589bf0847483957e4266ce3a4b022027f505048f2d` |
| `20260930_gcov_frequencyA_mask.tif` | 14863 | `66ea8174f50f05086e2a5dbd6718a3f36984dc656e6fe0f90a9583730ec05d89` |
| `20260906_gslc_mask.tif` | 35071 | `4e6cb7a293439e9de43704a580ac71c8a0da6010215e21adbb1fc63a0616da27` |
| `20260930_gslc_mask.tif` | 35071 | `4e6cb7a293439e9de43704a580ac71c8a0da6010215e21adbb1fc63a0616da27` |

The two GSLC crops share one digest because both are the constant value 1 on the same grid and compression. That equality is not a change measurement.

## Grid comparability

All eight GCOV layers, both dates, share EPSG:32644, 1171 by 1343 pixels, and geotransform `(379470, 10, 0, 3336070, 0, -10)`. Posting is 10 m. Power and `numberOfLooks` are Float32. The GCOV mask is Byte with NoData 255.

Both GSLC masks stay on their native grid: EPSG:32644, 2341 by 2685, geotransform `(379470, 5, 0, 3336070, 0, -5)`, posting 5 m. They were not resampled and were not applied to GCOV pixels.

## Mask codes

GCOV mask frequencies:

| Date | Code 0 | Code 1 | Other codes |
| --- | ---: | ---: | --- |
| 2026-09-06 | 4611 | 1568042 | none |
| 2026-09-30 | 4599 | 1568054 | none |

Code 0 is the documented invalid or partially focused sample. Code 1 is a valid subswath number. These crops contain no code 255. No code outside 0–255 appeared. The codes are not water, shadow, or layover classes.

GSLC mask frequencies, native 5 m grid: both dates are code 1 on all 6,285,585 pixels.

## Sample counts

Each GCOV layer has 1,572,653 pixels.

| Layer | Finite | NoData | Valid mask | Positive finite |
| --- | ---: | ---: | ---: | ---: |
| 2026-09-06 HHHH, HVHV, and looks | 1568042 | 4611 | 1568042 | 1568042 |
| 2026-09-30 HHHH, HVHV, and looks | 1568054 | 4599 | 1568054 | 1568054 |

The NoData count equals the mask code 0 count. Every valid-mask pixel is finite and, for the power layers, positive.

Invalid samples are spread through the window. On September 6 they occupy 779 rows and 617 columns, rows 2–1187 and columns 17–1169. On September 30 they occupy 778 rows and 614 columns, rows 1–1187 and columns 17–1169.

## Power distributions

Percentiles use the inclusive linear rank `(n-1) * p / 100`. Standard deviation uses the population divisor `n`. Decibels are `10*log10` of positive linear power.

### September 6 HHHH

Linear: minimum 0.0003533773124217987, maximum 37714.5, mean 2.361770415919772, population standard deviation 94.07237245534981.

| Percentile | Linear power | dB of that power |
| ---: | ---: | ---: |
| 0.1 | 0.0075698035955429075 | -21.2091538893909 |
| 1 | 0.026340258121490476 | -15.793799735900356 |
| 5 | 0.06698613166809082 | -11.740151012333786 |
| 10 | 0.09988975524902344 | -10.004790509829071 |
| 25 | 0.175140380859375 | -7.566137102127596 |
| 50 | 0.30483245849609375 | -5.159387912851302 |
| 75 | 0.5224761962890625 | -2.819334909696317 |
| 90 | 0.8882057189941417 | -0.5148643481206041 |
| 95 | 1.313507080078125 | 1.1843241806656881 |
| 99 | 3.8544366455078176 | 5.859609116536999 |
| 99.9 | 77.76036816428541 | 18.907572985196843 |

The dB sample itself has minimum -34.51761336567536, maximum 45.76508354430848, mean -5.1697649513369806, and population standard deviation 4.194680384799551. The busiest 2 dB histogram bins are -6 to -4 (355383), -8 to -6 (298355), and -4 to -2 (289741).

### September 6 HVHV

Linear: minimum 0.000124320387840271, maximum 4851.8125, mean 0.5997237393322307, population standard deviation 20.42437513537145.

| Percentile | Linear power | dB |
| ---: | ---: | ---: |
| 0.1 | 0.002261678218841553 | -26.45569184528584 |
| 1 | 0.00754673957824707 | -21.222406365283184 |
| 5 | 0.01877623796463013 | -17.263914192930255 |
| 10 | 0.02828383445739746 | -15.484617133050559 |
| 25 | 0.05110025405883789 | -12.915769406465575 |
| 50 | 0.09138822555541992 | -10.391097551004243 |
| 75 | 0.15692520141601562 | -8.043073052529534 |
| 90 | 0.2570343017578125 | -5.9000891530656006 |
| 95 | 0.35832939147949183 | -4.457175679651457 |
| 99 | 0.8843550109863294 | -0.533733590277279 |
| 99.9 | 21.401414794960942 | 13.304420760240069 |

dB sample: minimum -39.05457643679689, maximum 36.859040090558736, mean -10.521656802879923, population standard deviation 4.152724589122983. Busiest 2 dB bins: -12 to -10 (333576), -10 to -8 (329316), -14 to -12 (247678).

### September 30 HHHH

Linear: minimum 0.0006141439080238342, maximum 21008.25, mean 2.234916078810628, population standard deviation 90.31322754010014.

| Percentile | Linear power | dB |
| ---: | ---: | ---: |
| 0.1 | 0.00745191925764084 | -21.277318667722138 |
| 1 | 0.025293869972229002 | -15.969847185153174 |
| 5 | 0.06243784427642823 | -12.04552099767105 |
| 10 | 0.09199934005737306 | -10.36215287990532 |
| 25 | 0.16077852249145508 | -7.937719667029183 |
| 50 | 0.28166961669921875 | -5.502599972155927 |
| 75 | 0.487548828125 | -3.1198188309707175 |
| 90 | 0.8472976684570312 | -0.719639886570127 |
| 95 | 1.2935386657714822 | 1.1177941493994172 |
| 99 | 4.0108642578125 | 6.032379641305978 |
| 99.9 | 72.57415039065472 | 18.60781888996425 |

dB sample: minimum -32.117298517616526, maximum 43.22389876918217, mean -5.469482017610706, population standard deviation 4.25462435845577. Busiest 2 dB bins: -6 to -4 (347805), -8 to -6 (312325), -4 to -2 (265313).

### September 30 HVHV

Linear: minimum 0.0002370830625295639, maximum 3790.15625, mean 0.5007473065427528, population standard deviation 17.449988623998816.

| Percentile | Linear power | dB |
| ---: | ---: | ---: |
| 0.1 | 0.001950862392783165 | -27.09773363190702 |
| 1 | 0.006390308737754822 | -21.944781591196005 |
| 5 | 0.015353202819824219 | -18.138010128980767 |
| 10 | 0.022893977165222172 | -16.40278754693 |
| 25 | 0.041774868965148926 | -13.790849036852858 |
| 50 | 0.0765848159790039 | -11.158573268451855 |
| 75 | 0.13298988342285156 | -8.761813946775552 |
| 90 | 0.21716060638427725 | -6.632189543242694 |
| 95 | 0.3008575439453125 | -5.216390941848086 |
| 99 | 0.7327619934082001 | -1.3503706570942484 |
| 99.9 | 16.475571289063282 | 12.168404816947069 |

dB sample: minimum -36.250994713811394, maximum 35.78657114219797, mean -11.315528822446323, population standard deviation 4.188487443575985. Busiest 2 dB bins: -12 to -10 (334669), -10 to -8 (296877), -14 to -12 (278522).

The linear-power log10 histograms are in the manifest. They are one-decade bins of positive finite power.

## numberOfLooks

This layer is an adaptive multi-looking count. It is not a confidence or accuracy score. Both dates have the same finite and valid-mask counts as the power layers.

| | September 6 | September 30 |
| --- | ---: | ---: |
| Minimum | 4.670321462896254e-09 | 1.9322280664368918e-08 |
| Maximum | 16.38661766052246 | 16.39520835876465 |
| Mean | 4.7064618999785 | 4.706471470000759 |
| Population standard deviation | 2.805295041587006 | 2.805238259037348 |
| 0.1 | 0.02566987563110888 | 0.02541486277617514 |
| 1 | 0.10299076400697231 | 0.10291423007845879 |
| 5 | 0.39819024950265886 | 0.3981386303901672 |
| 10 | 0.811684536933899 | 0.8115961492061615 |
| 25 | 2.1719542145729065 | 2.1720492839813232 |
| 50 | 4.90416693687439 | 4.904300212860107 |
| 75 | 6.978619933128357 | 6.97856879234314 |
| 90 | 8.362034606933594 | 8.361954975128175 |
| 95 | 9.069948768615722 | 9.069505739212033 |
| 99 | 10.331761169433594 | 10.330946464538574 |
| 99.9 | 11.236777140617384 | 11.236072216987619 |

## Spatial profiles

Two profile definitions are stored, and they answer different questions.

The mean of per-pixel dB is the typical radiometric level of a row or column. For September 6 HHHH its row means span -6.143288638814741 dB to -3.806058615186032 dB. The largest adjacent step is 0.5343827302838235 dB between rows 777 and 778. The column means span -6.559736605101065 dB to -4.04968645295337 dB, and the largest adjacent step is 0.47461017066077904 dB. Those figures match the Mission 003 diagnostic profile for this crop. September 30 HHHH row means span -6.432060194308854 dB to -3.9875812031271023 dB, with a largest step of 0.5043270075627575 dB. September 6 HVHV largest row step is 0.5546906509132103 dB. September 30 HVHV largest row step is 0.5565401608866836 dB. Column steps for the cross-polar layers stay below 0.49 dB. A step above 1 dB does not appear in these mean-of-dB profiles.

The dB difference of successive linear-power means is dominated by the extreme tail. September 6 HHHH reaches 16.950253210152606 dB at row index 777 and -10.273477901721831 dB at column index 675. September 30 HHHH reaches 16.154822217649965 dB at the same row index and -9.911074892280036 dB at the same column index. HVHV linear-mean steps also exceed 8 dB. `numberOfLooks` stays in native units: the largest adjacent row step on either date is about 0.092 looks, and the largest column step is about 0.163 looks.

## Extreme returns

Pixels at or above 10000 linear power:

| Date | Layer | Count | Row span | Column span |
| --- | --- | ---: | --- | --- |
| 2026-09-06 | HHHH | 14 | 449–782 | 611–663 |
| 2026-09-30 | HHHH | 21 | 455–783 | 621–673 |
| both | HVHV | 0 | — | — |

One September 6 neighbourhood, 5 by 5, centered at row 449 column 611, has center 10646.375, neighbourhood minimum 0.4856452941894531, and maximum 15545.5. One September 30 neighbourhood, centered at row 455 column 621, has center 20681.25, minimum 511.52734375, and maximum 20681.25. The full neighbourhood list is in the manifest. These locations are not labeled as debris, RFI, or any other physical class.

The 99.9 percentile set contains 1569 pixels on each power layer. Its bounding box covers most of the raster, so that set is not a compact cluster. The `>= 10000` subset is the localized part of the tail.

## Run record

The audit ran at 2026-11-14T14:25:15Z. The interpreter was Python 3.12.16 with GDAL 3.13.3. `real_data_classification` is false. `gcov_grid_comparable` is true. Every recorded source checksum matched before and after the read.

The manifest's `output_sha256` is `ee9530f5d00ccec70d7222734fb59da17c52da3d89bc6e9342fb857b7d609d30`. That digest is the SHA-256 of the UTF-8 `json.dumps` of the object before `output_sha256` was added, with `indent` 2 and `sort_keys` true. The SHA-256 of the written file, including that field, is `b4a440790a0e2b35430a2f9e56ff78a4bd650802cb6afb462940b8375c365b90` (802991 bytes).

## Statistics configuration

- Percentile: inclusive linear rank `(n-1) * percent / 100`.
- Standard deviation: population divisor `n`.
- dB: `10*log10` of positive finite power.
- dB histogram width: 2. Linear log10 histogram width: 1.
- Software versions and the output digest are in the JSON manifest.

## Limitations

No water-candidate screen was run. No boundary or area was calculated. The GSLC masks were not resampled. `numberOfLooks` is not confidence. Mask codes are not thematic classes. Filename code `N` and `orbitType` `MOE` remain unresolved.
