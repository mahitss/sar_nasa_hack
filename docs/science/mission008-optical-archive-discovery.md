# Mission 008 — Sentinel-2 and Landsat archive discovery

This mission records which optical scenes intersect the RIVET discovery window on or near the two NISAR dates. It does not download imagery, classify water, calculate area or a shoreline, or change the Mission 006 screen.

The machine-readable record is `data/manifests/mission008_optical_catalogue.json`. The query tool is `tools/mission008_catalogue.py`. Tests are `tests/scientific/test_mission008_catalogue.py`.

Query time: 2026-11-14T16:41:40Z. Interpreter: CPython 3.12.13.

Starting Git state: `main` and `origin/main` were `68eb95b2d36dc1d74e1f2eb06b149a2ae8ed1f9b`, the Mission 007 commit. The working tree was clean. Mission 007 files were not modified.

## Search window

WGS84 discovery bbox, west 79.75, south 30.03, east 79.87, north 30.15. This is a catalogue window, not a lake boundary. Mission 007 row and column coordinates were not converted to longitude and latitude.

The published landslide location 30.084–30.087 N, 79.79–79.80 E is literature context from the Ghoke paper already cited in Mission 007. It is not a surveyed corner of a candidate patch.

NISAR acquisition times used for the hour offset are 2026-09-06T13:22:36Z and 2026-09-30T13:22:36Z. A scene on another calendar day is nearby evidence. It is not same-date ground truth. No scene in this mission is ground truth.

## Catalogues

Live collection lists were read before the searches.

| Catalogue | Root | STAC version | Collections searched |
| --- | --- | --- | --- |
| Element84 Earth Search | `https://earth-search.aws.element84.com/v1/` | 1.0.0 | `sentinel-2-l2a`, `sentinel-2-c1-l2a`, `sentinel-2-pre-c1-l2a`, and `sentinel-2-l1c` as a separate fallback |
| Copernicus Data Space | `https://stac.dataspace.copernicus.eu/v1/` | 1.0.0 | `sentinel-2-l2a` and `sentinel-2-l1c` |
| USGS LandsatLook | `https://landsatlook.usgs.gov/stac-server/` | 1.1.0 | `landsat-c2l2-sr` |

The Copernicus `/collections` list is paginated: the first page returned 10 of 428 collections and did not include Sentinel-2. `sentinel-2-l2a` and `sentinel-2-l1c` were then opened by collection URL. Both returned HTTP 200. The L2A collection text describes a global Collection 1 surface-reflectance product. That is the collection that was searched. An India scene was not assumed in advance.

`sentinel-2-pre-c1-l2a` is the Element84 collection for processing baseline below 05.00. `sentinel-2-c1-l2a` is Collection 1 Level-2A. `sentinel-2-l2a` is the global Level-2A collection. Level-1C was queried only as Level-1C.

Sentinel-2 fallback windows are five days on either side of each NISAR date. Landsat fallback windows are eight days. Exact-date queries were separate from those windows. Twenty-eight queries ran. None failed. Element84 and USGS reported `numberMatched`, and each next page was followed until it was empty. Copernicus did not report `numberMatched`; those responses had no remaining next link.

## Sentinel-2 exact dates

No Level-2A item, and no Level-1C item, intersects the window on 2026-09-06 or 2026-09-30 in Element84 or Copernicus. `sentinel-2-pre-c1-l2a` also returned nothing in the five-day windows.

## Sentinel-2 nearby dates

Four Level-2A acquisitions intersect the window. Each footprint covers the whole discovery window on a planar longitude/latitude clip. That coverage is of the catalogue window, not of a Mission 007 candidate patch. Scene-wide cloud is not cloud inside the window. The scene-classification rasters were not read.

Element84 `sentinel-2-l2a` and `sentinel-2-c1-l2a` return the same SAFE product URI, the same sensing time, and the same scene cloud for each acquisition. They are two collection views of one product. Copernicus uses the SAFE name as the item id and timestamps the datatake start, about fourteen minutes earlier than the Element84 item `datetime`. The day offset is the same.

| NISAR date | Offset | Element84 datetime | Copernicus datetime | Platform | SAFE product | Baseline | Scene cloud |
| --- | ---: | --- | --- | --- | --- | --- | ---: |
| 2026-09-06 | −4 days, −104 h | 2026-09-02T05:30:29.471Z | 2026-09-02T05:16:49.024Z | Sentinel-2B | `S2B_MSIL2A_20260902T051649_N0512_R062_T44RLU_20260902T090945` | 05.12 | 98.95% |
| 2026-09-06 | +1 day, +16.1 h | 2026-09-07T05:30:29.933Z | 2026-09-07T05:16:51.025Z | Sentinel-2C | `S2C_MSIL2A_20260907T051651_N0512_R062_T44RLU_20260907T101554` | 05.12 | 99.71% |
| 2026-09-30 | −3 days, −80 h | 2026-09-27T05:30:33.207Z | 2026-09-27T05:16:51.025Z | Sentinel-2C | `S2C_MSIL2A_20260927T051651_N0513_R062_T44RLU_20260927T101817` | 05.13 | 99.33% |
| 2026-09-30 | +2 days, +40.1 h | 2026-10-02T05:30:31.932Z | 2026-10-02T05:16:49.024Z | Sentinel-2B | `S2B_MSIL2A_20261002T051649_N0513_R062_T44RLU_20261002T091142` | 05.13 | 8.01% |

MGRS tile on every item: `MGRS-44RLU` (zone 44, band R, square LU). Product type `S2MSI2A`. Instrument MSI. Copernicus `processing:level` is L2. The item CRS recorded for the Collection 1 record is EPSG:32644. Reflectance assets are 10 m, 20 m, and 60 m. Level-2A cloud-mask assets are present and were not downloaded: Element84 `scl` and `cloud`; Copernicus `SCL_20m`, `SCL_60m`, `CLD_20m`, and `CLD_60m`.

The same four dates exist as Level-1C, with different scene-cloud values (92.23%, 97.44%, 85.89%, and 5.47%). Those items have no scene-classification asset in the catalogue response. Level-1C is top-of-atmosphere reflectance. It would need atmospheric correction before use as a surface-reflectance source. It is not reported here as Level-2A.

## Landsat exact dates

`landsat-c2l2-sr` returned no Landsat 8 or Landsat 9 Collection 2 Level-2 surface-reflectance scene on 2026-09-06 or 2026-09-30. Surface temperature and Level-1 products were not used as substitutes.

## Landsat nearby dates

Four Collection 2 Level-2 surface-reflectance scenes intersect the window. Each footprint covers the whole discovery window on the same planar clip. Path 145, row 39, from the item properties. Optical band `eo:bands` ground sample distance is 30 m. `qa_pixel` and `qa_aerosol` are present. Their file sizes are not in the STAC response. Scene cloud and land cloud are equal in each item. Local cloud inside the discovery window was not read.

| NISAR date | Offset | Datetime | Product | Platform | Tier | Scene cloud |
| --- | ---: | --- | --- | --- | --- | ---: |
| 2026-09-06 | −7 days, −176.2 h | 2026-08-30T05:12:05.154Z | `LC08_L2SP_145039_20260830_20260910_02_T1_SR` | Landsat 8, OLI and TIRS | T1 | 81.6% |
| 2026-09-06 | +1 day, +15.8 h | 2026-09-07T05:12:13.418Z | `LC09_L2SP_145039_20260907_20260908_02_T2_SR` | Landsat 9, OLI and TIRS | T2 | 81.9% |
| 2026-09-30 | −7 days, −176.2 h | 2026-09-23T05:12:18.182Z | `LC09_L2SP_145039_20260923_20260924_02_T1_SR` | Landsat 9, OLI and TIRS | T1 | 11.31% |
| 2026-09-30 | +1 day, +15.8 h | 2026-10-01T05:12:17.380Z | `LC08_L2SP_145039_20261001_20261009_02_T1_SR` | Landsat 8, OLI and TIRS | T1 | 4.82% |

`landsat:correction` on these items is `L2SP`. The collection searched is `landsat-c2l2-sr`. The 7 September Landsat 9 scene is collection category T2.

## Download sizes

Nothing was downloaded. Sizes below are catalogue `file:size` values.

Copernicus full SAFE archives for the four Level-2A products are 822,923,990 bytes (2 September), 751,226,484 bytes (7 September), 809,763,020 bytes (27 September), and 1,234,746,948 bytes (2 October). The 2 October `SCL_20m` asset is 1,541,060 bytes and `CLD_20m` is 1,561,721 bytes. A single 10 m band on that product is about 128–135 MB.

Element84 `sentinel-2-c1-l2a` lists a file size on every asset. The sum of those sizes, counting bands, masks, and metadata together, is about 0.90–1.70 GB per product. The `sentinel-2-l2a` assets in this response did not include `file:size`. Landsat asset sizes were not in the response.

## What is still missing

No optical scene exists in these catalogues on either NISAR date. Scene cloud above 80% describes the 2 September, 7 September, and 27 September Sentinel-2 Level-2A products and both Landsat scenes beside 6 September. Those percentages do not prove that every pixel in the discovery window is cloudy, because the masks were not read. The 2 October Sentinel-2 scene at 8.01% and the 1 October Landsat scene at 4.82% are the only low scene-cloud neighbours, and both are after 30 September.

## Tests

`tests/scientific/test_mission008_catalogue.py` ran 9 tests on CPython 3.12.13. All passed. They check that exact and nearby dates stay distinct, Level-1C is not labeled Level-2A, the live collection ids are the ones queried, footprint overlap is 100%, 50%, or none for synthetic polygons, pagination is incomplete when a next link is left unfollowed, and the manifest flags keep imagery, water labels, area, and threshold changes off.

## Recommended next mission

Do not treat any scene above as validation of the Mission 006 candidates.

A later mission can inspect cloud only, and only for the two low scene-cloud neighbours of 30 September: Sentinel-2 Level-2A `S2B_MSIL2A_20261002T051649_N0513_R062_T44RLU_20261002T091142` and Landsat `LC08_L2SP_145039_20261001_20261009_02_T1_SR`. The Sentinel-2 scene-classification asset at 20 m is about 1.5 MB. Landsat `qa_pixel` has no size in the catalogue, so that file needs a size before any download. The 6 September neighbours stay out of an appearance review until a mask shows whether the window itself is clear.

That mission still must not calculate a water index, an area, or a shoreline, and it must not retune the 1092-set screen.
