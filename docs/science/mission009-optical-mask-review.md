# Mission 009 — Optical cloud and shadow mask review

This mission reads quality masks for two acquisitions after the 30 September 2026 NISAR pass. It does not download reflectance, calculate a water index, classify water, or change the Mission 006 screen. Neither observation is same-date ground truth.

The record is `data/manifests/mission009_optical_mask_review.json`. The runner is `tools/mission009_mask_review.py`. Tests are `tests/scientific/test_mission009_mask_review.py`.

Review time: 2026-11-14T18:04:43Z. OSGeo4W Python 3.12.16 and GDAL 3.13.3.

Starting Git state: `main` and `origin/main` were `980f42030c17b2f72dea5b91c3a779393dd5e0c6`. The tree was clean. Mission 007 and Mission 008 files were not modified.

## Assets

Sentinel-2B Level-2A, processing baseline 05.13, item `S2B_T44RLU_20261002T052420_L2A`, SAFE product `S2B_MSIL2A_20261002T051649_N0513_R062_T44RLU_20261002T091142`. Element84 item datetime 2026-10-02T05:30:31.932Z, which is 40.13 hours after 2026-09-30T13:22:36Z.

HTTP `Content-Length` matched the Mission 008 catalogue before download:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `data/raw/mission009/SCL.tif` | 1,869,617 | `a2f03f7ef2c8c0da9f6073af3ec0bafd714b21c6b868a660144f5c7c9c4ae8c7` |
| `data/raw/mission009/CLD_20m.tif` | 1,660,814 | `347c287b93e228e894223f2f3f41e9db0a6260b4b986f4e139e64c980dd86946` |

Both responses were `image/tiff`. No SAFE archive and no reflectance band was requested.

Landsat 8 Collection 2 Level-2 product `LC08_L2SP_145039_20261001_20261009_02_T1_SR` was not downloaded. A HEAD request to the `QA_PIXEL` URL returned HTTP 302 to the USGS EROS login page. The followed response was `text/html` of 33,066 bytes. That length is the login page, not the GeoTIFF. A one-byte range request without following the redirect also returned HTTP 302 and `Content-Length: 0`, with no `Content-Range`. The object size is unknown, so the 25 MB rule could not be evaluated. `QA_AEROSOL` and the reflective bands were not requested.

The Landsat acquisition time remains 2026-10-01T05:12:17.380Z, 15.83 hours after the 30 September NISAR pass. No Landsat pixel statistics are reported.

## Specifications

Sentinel-2 scene classes are Table 68 of S2-PDGS-CS-DI-PSD, issue 15.1, dated 05/12/2025:

| Value | Label |
| ---: | --- |
| 0 | NO_DATA |
| 1 | SATURATED_OR_DEFECTIVE |
| 2 | CAST_SHADOWS |
| 3 | CLOUD_SHADOWS |
| 4 | VEGETATION |
| 5 | NOT_VEGETATED |
| 6 | WATER |
| 7 | UNCLASSIFIED |
| 8 | CLOUD_MEDIUM_PROBABILITY |
| 9 | CLOUD_HIGH_PROBABILITY |
| 10 | THIN_CIRRUS |
| 11 | SNOW / ICE |

Class 6 keeps that label. It is not a water measurement for this mission. PSD 15.1 section 3.13.3.3 names `MSK_CLDPRB` a cloud probability map. The retrieved section does not state a percent encoding. The statistics below are stored sample values. The observed samples are integers from 0 through 100.

Landsat bit definitions, recorded for the decoder and not applied to a downloaded file, are LSDS-1619 version 6.0, Table 6-2. Bit 0 is fill. Bit 1 is dilated cloud. Bit 2 is high-confidence cirrus. Bit 3 is high-confidence cloud. Bit 4 is high-confidence cloud shadow. Bit 5 is high-confidence snow. Bit 6 is clear, meaning the cloud and dilated-cloud bits are unset. Bit 7 is the water bit and is not a water claim. Bits 8–9 are cloud confidence: none, low, medium, high. Bits 10–11, 12–13, and 14–15 are cloud-shadow, snow/ice, and cirrus confidence: none, low, reserved, high.

## Discovery window

The window is WGS84 west 79.75, south 30.03, east 79.87, north 30.15. Both Sentinel-2 masks are EPSG:32644, 5490 by 5490, geotransform `(300000, 20, 0, 3400020, 0, -20)`, Byte, 20 m. The GeoTIFF nodata value is 0, which is also SCL class 0. The densified window polygon lies inside both rasters.

Pixels were selected when their centers fall inside that polygon. The sensors were not resampled onto each other. Selected footprint area is 384,510 pixels times 400 m², which is 153,804,000 m². That figure is mask coverage, not a lake area. Mission 007 row and column coordinates were not projected.

## Sentinel-2 scene classification

All 384,510 window pixels have a specified class. SCL classes are mutually exclusive.

| Class | Pixels | Percent of window pixels |
| --- | ---: | ---: |
| NO_DATA | 0 | 0 |
| SATURATED_OR_DEFECTIVE | 0 | 0 |
| CAST_SHADOWS | 4,164 | 1.083 |
| CLOUD_SHADOWS | 34,462 | 8.963 |
| VEGETATION | 271,355 | 70.571 |
| NOT_VEGETATED | 5,706 | 1.484 |
| WATER label | 19 | 0.0049 |
| UNCLASSIFIED | 1,212 | 0.315 |
| CLOUD_MEDIUM_PROBABILITY | 24,536 | 6.382 |
| CLOUD_HIGH_PROBABILITY | 42,974 | 11.176 |
| THIN_CIRRUS | 0 | 0 |
| SNOW_OR_ICE | 82 | 0.021 |

Cloud plus cirrus is 67,510 pixels, 17.557%. Cloud shadow is separate. Together with cloud and cirrus, those three classes are 101,972 pixels, 26.520%. Cast shadow is a different class in the specification and adds 4,164 pixels. The other recorded classes, including the 19 pixels labeled water, are 278,292 pixels, 72.376%.

The Mission 008 scene-wide cloud value for this product was 8.01%. The discovery window is cloudier than that scene-wide figure. Scene-wide cloud still does not describe this window.

## Cloud probability

Stored `CLD_20m` values on the same 384,510 pixels: minimum 0, maximum 100, median 0, 5th and 25th and 75th percentiles 0, 95th and 99th percentiles 100. The percentile method is the inclusive linear rank `(n-1)*p/100`.

| Stored values | Pixels |
| --- | ---: |
| 0–9 | 333,031 |
| 10–19 | 1,609 |
| 20–29 | 1,380 |
| 30–39 | 1,252 |
| 40–49 | 1,164 |
| 50–59 | 1,064 |
| 60–69 | 962 |
| 70–79 | 1,033 |
| 80–89 | 965 |
| 90–99 | 939 |
| 100 | 41,111 |

A stored value above zero is not a tuned cloud decision. Of the 67,510 SCL cloud or cirrus pixels, 53,611 have a cloud-probability sample above zero and 13,899 have sample 0. The median sample is 100 inside high-probability cloud and 0 inside medium-probability cloud. Of the remaining SCL pixels, 1,680 have a sample above zero and 315,320 have sample 0. The two masks agree that much of the window has a zero stored probability, and they disagree on the medium-probability class.

## Tests

On OSGeo4W Python 3.12.16, the catalogue, synthetic water-candidate, hardened, distribution, sweep, Mission 007, Mission 008, and Mission 009 suites ran 103 tests. All passed. None were skipped. The Mission 009 tests cover SCL labels, documented QA_PIXEL values 1 and 22280, simultaneous cloud flags counted once in a union, fill exclusion, confidence bits, separate 20 m and 30 m center selections, deterministic statistics, and refusal of the USGS login response.

## Limitations

These masks describe 2 October at 05:30 UTC. They do not describe the NISAR acquisition 40.13 hours earlier. The Landsat mask from 15.83 hours after that acquisition was not readable. Class 6 and QA bit 7 are not water detections. Cast shadow is not cloud shadow. A zero cloud-probability sample is not proof of a clear view of the ground, and absence of one Landsat cloud bit would not be called clear. No candidate patch was compared with these pixels.

## Recommended next mission

Do not open a reflectance or water-index mission on these scenes. The discovery window on 2 October is not cloud-free: 17.557% of its SCL pixels are cloud and 8.963% are cloud shadow. The 6 September NISAR date still has no low scene-cloud optical neighbour in Mission 008.

A Landsat QA read remains blocked until an authenticated request returns the `QA_PIXEL` object itself, with a TIFF content type and a size at or below 25 MB. That step still would not validate the NISAR candidates.
