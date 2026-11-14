# Mission 012 — Authenticated partial access to the GCOV products

Earthaccess 0.19.0 opened both provisional GCOV products over HTTPS and read their metadata. Neither complete HDF5 file was stored. No slope, shadow, layover, or water product was made.

The record is `data/manifests/mission012_nisar_access.json`. The checker is `tools/mission012_nisar_access.py`.

Starting Git state: `main` and `origin/main` were `cc7d52ae452ea30a7519f4e6a0c411dbf81e1376`.

## Why the earlier read failed

The existing credential file is `C:\Users\pc\.netrc`. Python's `netrc` parser reads it. It has one `machine urs.earthdata.nasa.gov` entry, with a login and a password present. Earthaccess 0.19.0 on Windows looks for `C:\Users\pc\_netrc` unless the `NETRC` environment variable is set. The first login attempt failed with `LoginStrategyUnavailable` because that `_netrc` path does not exist. The credential file was not modified and was not copied. The process set `NETRC` to the existing `.netrc` path and called `earthaccess.login(strategy="netrc")` once. Authentication succeeded.

The earlier raw HTTP client had followed a chain of 302 and 301 redirects and ended on HTTP 302 with `application/json`. That was a client redirect failure, not evidence that the products lack an HDF5 payload.

## Access result

CMR returned exactly one granule for each catalogue concept, `G4308353703-ASF` on 6 September and `G4333767987-ASF` on 30 September. Each external HTTPS link is on `nisar.asf.earthdatacloud.nasa.gov` and its path ends with the expected `.h5` name.

A read of the first 8192 bytes of each product begins with the HDF5 signature `89 48 44 46 0d 0a 1a 0a` at offset 0. The metadata session then read 68,021 bytes from each stream, as counted by the file wrapper. That is the number of bytes returned by `read`, not a separate HTTP content-range counter. Both reads are far below the 64 MiB budget. No local HDF5 file was created.

GDAL was not used. Direct S3 was not attempted. The documented S3 credential endpoint is `https://nisar.asf.earthdatacloud.nasa.gov/s3credentials`, and direct S3 is limited to AWS `us-west-2`. This machine is not in that region.

## Metadata, both dates

The two products agree.

| Field | Value |
| --- | --- |
| `lookDirection` | Left |
| `orbitPassDirection` | Descending |
| `orbit/orbitType` | MOE |
| `orbit/interpMethod` | Hermite |
| `orbit/time` | 45 samples |
| `orbit/position` | 45 by 3, meters, WGS84 G1762 |
| `orbit/velocity` | 45 by 3 |
| `attitude/attitudeType` | Custom |
| `attitude/time` | 126 samples |
| `attitude/quaternions` | 126 by 4 |
| `attitude/eulerAngles` | 126 by 3 |
| `shadowMaskingApplied` | the string `False` |
| geometric-accuracy bias and standard deviation, x and y | scalar NaN |

`attitudeType` is the documented scalar at `/science/LSAR/GCOV/metadata/attitude/attitudeType`. The Product Format Document lists `FRP`, `NRP`, `PRP`, and `Custom`.

`demFiles` is not in the file. `demSource` identifies NISAR DEM version 1.2, based on Copernicus DEM 30 m release `2023_1`, collection `COP-DEM_GLO-30-DGED/2023_1`, referenced to the WGS84 ellipsoid. The DOI in that text is `10.5067/NIDEM-1`. The public geocells stored in Mission 011 are the 2022 open-data objects and their GeoTIFF header does not carry a vertical CRS. The processor text says its DEM is ellipsoid-referenced. Those are not the same statement, and this mission did not treat the local tiles as the processor input.

## Radar grid

Both products use the same coordinate axes. `xCoordinates` has 710 values from 296,250 m to 650,750 m. `yCoordinates` has 699 values from 3,221,250 m to 3,570,250 m. `heightAboveEllipsoid` has 21 values from −1,000 m to 9,000 m. Units are meters. On 6 September the steps are uniform: x increases by 500 m, y decreases by 500 m, and height increases by 500 m. The incidence, slant-range, line-of-sight, and elevation cubes have shape 21 by 699 by 710. Incidence is float32, degrees, with the documented valid range 0 to 90. The cube values were not read. This incidence remains the ellipsoid incidence at the target height, not a slope incidence.

## Filename comparison

The filename accuracy character is `N`. Section 2.2.4 maps that character to orbit ephemeris `NOE` and radar pointing `NRP`. The next character, `F`, is coverage. Both products have HDF5 `orbitType` `MOE` and `attitudeType` `Custom`. Orbit consistency is `mismatch`. Pointing consistency is `mismatch`. Neither mismatch is resolved, and neither is converted into a geolocation error.

## Tests

uv CPython 3.12.13: `python -m unittest tests.scientific.test_mission012_nisar_access` ran 5 tests. All passed. None were skipped.

OSGeo4W Python 3.12.16 ran the catalogue through Mission 012 modules: 128 tests. All passed. None were skipped.

## Recommendation

**GO** for using these metadata in a later geometry-model design. Both products were opened by partial HTTPS reads, and the required scalars and coordinate axes were read.

**NO-GO** for a shadow or layover model in this mission. The incidence cubes were not extracted, the processor DEM is the ellipsoid-referenced 2023_1 release rather than the local EGM2008 tiles, `shadowMaskingApplied` is the string `False`, and the filename still disagrees with both `orbitType` and `attitudeType`.
