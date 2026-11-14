# Scientific limitations

These limits apply to the first vertical slice. They are not implementation defects. They are properties of the data and of the claims RIVET is allowed to make.

## Maturity and comparability

- Group D40 is provisional CRID P05023. ASF describes provisional products as calibrated and validated only at a limited set of sites.
- Validated products in the same window use CRID P05036. ASF warns against casually combining different composite release IDs. RIVET does not.
- Mission 000 did not find a second validated scene with the same track, frame, bandwidth, and polarization inside 8 July 2026–14 November 2026. A validated-only time series is not available for that window.
- Track 5 alternates 40 MHz HH+HV with 20 MHz HH+HV+VH+VV. Those modes are different groups. The user guide posts 40 MHz Frequency-A GCOV at 10 m and 20 MHz GCOV at 20 m.
- Ascending track 127 is a separate geometry. It can corroborate. It cannot be subtracted from a descending scene as if both were the same measurement.
- Orbit type on the inspected granules was `MOE`. The geolocation error of that orbit for this valley was not measured.

## What a 10 m water candidate can and cannot show

The published October 2024 lake was on the order of 1,130 m by 100 m. At 10 m posting, the width is on the order of ten pixels. A change of tens of metres is the scale the first measurement may discuss. The published debris dam, on the order of 60 m by 58 m and 40 m high, is not a structure this GCOV product can resolve.

The GSLC mask for water, shadow, and layover is a mission layer. It is an input to quality control, not ground truth.

## SAR conditions in this valley

- Steep terrain produces layover and radar shadow. Parts of the landslide body will be missing or displaced in radar geometry. Optical imagery remains the published source for scarp mapping.
- The Group D40 dates fall in and just after the monsoon. Wet debris, soil moisture, and wind-roughened water change backscatter without a shoreline change.
- Vegetation on the valley side and debris on the water margin can hide or imitate open water.
- A dark-pixel rule without the mask and without review is not a measurement this project will accept.
- Temporal decorrelation, 80 m posting, and mixed-bandwidth pairs are why GUNW is excluded. The published Sentinel-1 SBAS study already reported poor coherence here. NISAR deformation is not assumed to be better.
- GOFF is documented primarily for the cryosphere, posted at 80 m, and distributed with offset outliers left in. It is excluded.

## Models and prior numbers

Published figures for lake volume, MOI, HDSI, breach velocity, and inundation depth come from other authors and other methods. RIVET may cite them. RIVET may not repeat them as its own observations. The 2026 HEC-RAS scenario is a model, and its authors state that it cannot currently be validated.

No accuracy percentage, confidence interval, or skill score is claimed for a RIVET measurement until one is computed and reviewed.

## Coverage is not the bounding box

CMR bounding-box hits include track 55 and track 106, whose provisional footprints did not contain the coordinate used in Mission 000 (30.088337°N, 79.808685°E, from a secondary SANDRP article). Only point-in-polygon membership qualifies a scene for a comparability group. A small error in that coordinate does not change the large track 5 and track 127 frames. It could matter at the edge of track 106, which is why track 106 stays out.

## Data that this repository does not have

- No HDF5 or GeoTIFF has been downloaded.
- S-band granule ids for this point were not retrieved. Bhoonidhi requires an account. Joint-observation metadata on the L-band GCOV files is not proof that a usable S-band raster is inside the ASF HDF5.
- ISRO CartoDEM and Cartosat scenes used by the 2026 paper are not an open default dataset for this repo.
- Public 30 m DEMs can provide slope context later. They cannot reproduce the published lake volume.
