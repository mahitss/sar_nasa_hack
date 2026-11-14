# Mission 011 — Terrain acquisition and NISAR geometry inspection

This mission stored the two Copernicus DEM GLO-30 geocells that cover the buffered discovery window and attempted to read the GCOV geometry metadata. It did not build a slope, shadow, or layover product, and it did not reclassify the Mission 006 candidates.

The record is `data/manifests/mission011_terrain_geometry_acquisition.json`. The checker is `tools/mission011_acquisition.py`. The source files are under `data/raw/mission011/copernicus_dem/`, which Git ignores. The elevation crop is `data/derived/mission011/glo30_buffered_window_elevation.tif`, also ignored.

Starting Git state: `main` and `origin/main` were `c3ea000d3675afa01d51fe17df64325c1652512c`.

## DEM acquisition

The objects were listed from the public Copernicus DEM 30 m bucket, `https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com/`. The non-COG prefix `Copernicus_DSM_10_N30_00_E079_00/` is empty. Each geocell is a 16-file COG package whose elevation file uses the handbook stem. Retrieval finished at 2026-11-14T18:38:43Z. Both packages include `INFO/eula_F.pdf`, and those two licence files have the same SHA-256, `32049914c37f14e7d53b48d13d74a49e77c030236e2acc7a0df426f9344feba2`. The stored package is 189,527,089 bytes.

| Geocell | Elevation file | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| `Copernicus_DSM_10_N30_00_E079_00` | `Copernicus_DSM_COG_10_N30_00_E079_00_DEM.tif` | 41,706,694 | `b24a393f1e1756a975b63df8ef81f9570a5b7622932d197149302a1b8e192ec1` |
| `Copernicus_DSM_10_N29_00_E079_00` | `Copernicus_DSM_COG_10_N29_00_E079_00_DEM.tif` | 43,740,536 | `bda5104881002b44ef0e5e0cd29110d208413db178d84d65fbb49f24a0229b1c` |

Quality layers in each `AUXFILES` directory, with the handbook meanings:

| Layer | Handbook meaning | N30 bytes | N29 bytes |
| --- | --- | ---: | ---: |
| EDM | Editing mask. 0 void, 1 not edited, 2 external infill, 3 interpolated, 4 smoothed | 1,363,363 | 775,699 |
| FLM | Filling mask. Edited and filled pixels, with the fill source coded | 1,597,994 | 780,953 |
| WBM | Water-body mask | 31,801 | 31,934 |
| HEM | Height-error standard deviation from interferometric coherence. Edited pixels are coded −32,767. This is not a systematic-error or unwrapping-error layer | 38,731,297 | 52,519,174 |
| ACM | Accuracy layer, KML | 670 | 672 |

The packages also contain the source KML, quicklooks, and the geocell XML. SHA-256 values for every stored file are in the manifest.

## Grid

Both elevation rasters, and their EDM, FLM, WBM, and HEM layers, are 3600 by 3600, one band, EPSG:4326, `AREA_OR_POINT=Point`. The pixel size is 1/3600 degree. The geotransform origin is the upper-left corner of the upper-left pixel, half a pixel outside the first sample. Sample centers therefore fall on integer arcseconds.

The northern geocell centers run from 31.0° N down to 30.0° N plus 1 arcsecond. The southern geocell centers run from 30.0° N down to 29.0° N plus 1 arcsecond. Longitude centers run from 79.0° E through 79.0° E plus 3599 arcseconds. The two geocells do not share a posting. Their nearest centers are one arcsecond apart. No boundary value was averaged or overwritten.

The elevation bands have no nodata value. All 12,960,000 samples in each geocell are finite. The northern elevations run from 626.0 m to 7804.015625 m. The southern elevations run from 196.6738739013672 m to 2765.322998046875 m. HEM uses nodata −32,767.

The GeoTIFF coordinate system is horizontal WGS 84 only. The geocell XML identifies the vertical CRS as EGM2008, `gml:id="ogp-crs-3855"`, and also contains the text `vertical: "WGS 84 Geoid EGM08"`. A separate `tsxx:verticalDatumCode` element says `WGS84-G1150`. The handbook Table 1 says the vertical datum is EGM2008, EPSG:3855. Those XML fields were not forced into one value. No height transformation was applied.

The buffered window, west 79.70, south 29.98, east 79.92, north 30.20, selects 793 by 793 sample centers: 720 rows from the northern geocell and 73 from the southern geocell. Rebuilding that stack from the source grids matches the stored crop value for value. The crop file is 2,131,504 bytes, SHA-256 `ee20119719b07c9207037c30c037c1e70942f185af1b828775a65c8e2599fbbf`. Its sample centers run from 79.70° E to 79.92° E and from 30.20° N to 29.98° N.

The northern geocell's southernmost center is 30.000277777777775° N. The southern geocell's northernmost center is 30.0° N. The separation is one arc-second sample spacing, 0.00027777777777515666°. There is no shared center, and the source values were not interpolated or averaged.

Mission 011.1 measured these grids, checksums, and the crop from the files on disk. It did not download anything. The retrieval timestamp remains 2026-11-14T18:38:43Z. The file inventory against the previous manifest has no missing, extra, or checksum-mismatched paths. The height relation, which was not applied, is ellipsoidal height = orthometric height + geoid undulation, with undulation defined as ellipsoid minus geoid.

## NISAR geometry

The catalogue URLs for the two P05023 GCOV granules were used. A request for bytes 0–1023 followed a chain of HTTP 302 and 301 redirects and ended on HTTP 302 with content type `application/json`. The HDF5 signature was not received. A GDAL `/vsicurl/` open, using the existing Earthdata netrc entry and a temporary cookie jar, raised `RuntimeError` and did not return `orbitType`. The cookie jar was deleted. No complete HDF5 file was stored, and no local copy of either granule was found.

Because the products were not opened, this mission does not confirm or revise the Mission 010.1 record. That record still says filename code `N` expects `NOE` and the previously inspected HDF5 `orbitType` was `MOE`, with `resolved` false. The filename parser used here keeps the accuracy character separate from the following coverage character: `N` implies orbit ephemeris `NOE` and radar pointing `NRP`, and the next character `F` is coverage, not pointing. That parse was not compared with an HDF5 value in this mission.

Radar-grid shape, spacing, incidence, line of sight, geometric-accuracy estimates, and `demSource` were not read. No posting is claimed.

## Vertical reference

Copernicus elevation is documented as EGM2008 orthometric height, with the XML conflict noted above. The NISAR dataset `heightAboveEllipsoid` is a radar-grid height above the WGS84 ellipsoid. Connecting them requires an EGM2008 geoid-undulation grid, where ellipsoidal height equals orthometric height plus the ellipsoid-minus-geoid separation. A horizontal CRS change does not do that. The product geometric-accuracy estimates would not resolve it either. No transformation was applied.

## What was not done

No slope, aspect, shadow mask, layover mask, terrain correction, water reclassification, area, or shoreline was produced. Mission 006 thresholds were not changed.

## Tests

`python -m unittest tests.scientific.test_mission011_acquisition` on uv CPython 3.12.13 ran 14 tests. All passed. None were skipped. The OSGeo4W Python 3.12.16 run of the catalogue through Mission 011 modules ran 123 tests. All passed. None were skipped. The second local manifest rebuild produced the same crop checksum and did not download data.

## Recommendation

**CONDITIONAL GO** for a later geometry-model design. The DEM geocells and their quality layers are on disk, and the buffered crop is 793 by 793 point samples with no shared boundary posting.

The blocker is Earthdata range access. A shadow or layover design stays **NO-GO** until a partial read of both GCOV files returns an HDF5 signature and the radar-grid axes, `orbitType`, `attitudeType`, `demSource`, and `shadowMaskingApplied` have been read from those files.
