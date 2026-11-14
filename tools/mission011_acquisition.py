"""Mission 011 DEM acquisition records and NISAR filename checks.

The remote reads live in the mission runner. These functions stay deterministic
and do not download data when imported.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

DISCOVERY_BBOX = [79.75, 30.03, 79.87, 30.15]
BUFFERED_BBOX = [79.70, 29.98, 79.92, 30.20]
GEOCELLS = ("Copernicus_DSM_10_N29_00_E079_00", "Copernicus_DSM_10_N30_00_E079_00")

FILENAME_ORBIT = {"P": "POE", "M": "MOE", "N": "NOE", "F": "FOE"}
FILENAME_POINTING = {"P": "PRP", "M": "PRP", "N": "NRP", "F": "FRP"}

GCOV_FIELDS = (
    "mission",
    "instrument_level",
    "processing_type",
    "product",
    "cycle",
    "track",
    "orbit_pass",
    "frame",
    "bandwidth_mode",
    "polarization",
    "source",
    "start",
    "end",
    "crid",
    "accuracy",
    "coverage",
    "location",
    "version",
)


def parse_gcov_filename(name: str) -> dict:
    """Parse a GCOV filename by the Product Format Document 1.2.1 field order.

    The accuracy character is one field. Section 2.2.4 pairs it with an orbit
    ephemeris and a radar-pointing product. The next character is coverage,
    not a pointing token.
    """
    stem = name[:-3] if name.endswith(".h5") else name
    parts = stem.split("_")
    if len(parts) != len(GCOV_FIELDS):
        raise ValueError(f"expected {len(GCOV_FIELDS)} filename fields, found {len(parts)}")
    fields = dict(zip(GCOV_FIELDS, parts))
    accuracy = fields["accuracy"]
    return {
        **fields,
        "expected_orbit_ephemeris": FILENAME_ORBIT.get(accuracy),
        "expected_radar_pointing": FILENAME_POINTING.get(accuracy),
        "coverage_is_not_pointing": True,
    }


def compare_orbit_and_pointing(filename: str, orbit_type: str, attitude_type: str | None) -> dict:
    parsed = parse_gcov_filename(filename)
    expected_orbit = parsed["expected_orbit_ephemeris"]
    expected_pointing = parsed["expected_radar_pointing"]
    orbit_status = "mismatch" if expected_orbit != orbit_type else "match"
    if attitude_type is None:
        pointing_status = "not_read"
    elif attitude_type == expected_pointing:
        pointing_status = "match"
    else:
        pointing_status = "mismatch"
    return {
        "filename": filename,
        "accuracy_token": parsed["accuracy"],
        "coverage_token": parsed["coverage"],
        "expected_orbit_ephemeris": expected_orbit,
        "observed_orbit_type": orbit_type,
        "orbit_consistency": orbit_status,
        "expected_radar_pointing": expected_pointing,
        "observed_attitude_type": attitude_type,
        "pointing_consistency": pointing_status,
        "resolved": False,
        "geolocation_error_inferred": False,
    }


def file_record(path: Path) -> dict:
    if not path.exists():
        return {"path": str(path), "present": False, "bytes": None, "sha256": None}
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(path), "present": True, "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def geocell_covers_bbox(lower_left_lat: int, lower_left_lon: int, bbox: list[float]) -> bool:
    west, south, east, north = bbox
    return lower_left_lon <= west and east <= lower_left_lon + 1 and lower_left_lat <= south and north <= lower_left_lat + 1


def buffered_window_geocells(bbox: list[float] = BUFFERED_BBOX) -> list[str]:
    west, south, east, north = bbox
    names = []
    import math

    lat0 = math.floor(south)
    while lat0 < north:
        lon0 = math.floor(west)
        while lon0 < east:
            ns = "N" if lat0 >= 0 else "S"
            ew = "E" if lon0 >= 0 else "W"
            names.append(f"Copernicus_DSM_10_{ns}{abs(lat0):02d}_00_{ew}{abs(lon0):03d}_00")
            lon0 += 1
        lat0 += 1
    return names


def vertical_reference_note() -> dict:
    return {
        "dem_vertical_datum": "EGM2008 orthometric height",
        "radar_grid_height": "heightAboveEllipsoid relative to the WGS84 ellipsoid",
        "transformation_applied": False,
        "required_model": "An EGM2008 geoid-undulation grid. Orthometric height plus geoid undulation equals ellipsoidal height when the undulation is the ellipsoid-minus-geoid separation.",
        "horizontal_crs_is_not_a_vertical_datum": True,
        "geometric_accuracy_does_not_resolve_the_vertical_datum": True,
    }


def compare_file_inventory(expected: list[dict], actual: list[dict]) -> dict:
    expected_by_path = {item["path"]: item for item in expected}
    actual_by_path = {item["path"]: item for item in actual}
    missing = sorted(set(expected_by_path) - set(actual_by_path))
    extra = sorted(set(actual_by_path) - set(expected_by_path))
    mismatches = []
    for path in sorted(set(expected_by_path) & set(actual_by_path)):
        fields = []
        if expected_by_path[path].get("bytes") != actual_by_path[path].get("bytes"):
            fields.append("bytes")
        if expected_by_path[path].get("sha256") != actual_by_path[path].get("sha256"):
            fields.append("sha256")
        if actual_by_path[path].get("present") is False:
            fields.append("present")
        if fields:
            mismatches.append({"path": path, "fields": fields})
    return {"missing": missing, "extra": extra, "mismatches": mismatches}


def compare_raster_metadata(expected: dict, actual: dict) -> list[str]:
    fields = ("width", "height", "bands", "dtype", "horizontal_crs", "nodata", "area_or_point")
    return [field for field in fields if expected.get(field) != actual.get(field)]


def sample_center_axes(geotransform, width: int, height: int) -> tuple[list[float], list[float]]:
    origin_x, pixel_x, _, origin_y, _, pixel_y = geotransform
    x_centers = [origin_x + (column + 0.5) * pixel_x for column in range(width)]
    y_centers = [origin_y + (row + 0.5) * pixel_y for row in range(height)]
    return x_centers, y_centers


def seam_between_grids(north_geotransform, north_width, north_height, south_geotransform, south_width, south_height) -> dict:
    _, north_y = sample_center_axes(north_geotransform, north_width, north_height)
    _, south_y = sample_center_axes(south_geotransform, south_width, south_height)
    spacing = abs(north_y[0] - north_y[1]) if len(north_y) > 1 else None
    shared = {round(value, 10) for value in north_y} & {round(value, 10) for value in south_y}
    return {
        "north_southernmost_center_deg": north_y[-1],
        "south_northernmost_center_deg": south_y[0],
        "center_separation_deg": north_y[-1] - south_y[0],
        "sample_spacing_deg": spacing,
        "shared_sample_center": bool(shared),
        "values_averaged": False,
        "values_interpolated": False,
    }


def ellipsoidal_height_m(orthometric_height_m: float, geoid_undulation_m: float) -> float:
    """Return h = H + N. N is the ellipsoid-minus-geoid separation. Not applied to a raster."""
    return orthometric_height_m + geoid_undulation_m


def vertical_statements_from_xml(text: str) -> dict:
    import re

    return {
        "gml_vertical_names": re.findall(r"<gml:name>([^<]*(?:EGM|geoid|Geoid)[^<]*)</gml:name>", text),
        "geoid_notes": re.findall(r'vertical:\s*"([^"]+)"', text),
        "vertical_datum_codes": re.findall(r"<tsxx:verticalDatumCode>([^<]+)</tsxx:verticalDatumCode>", text),
        "reconciled": False,
    }


NISAR_RECORD = {
    "opened": False,
    "blocker": "Earthdata range reads redirected repeatedly and ended at HTTP 302 with content type application/json. GDAL /vsicurl/ did not return an HDF5 signature. The complete products were not downloaded.",
    "range_bytes_requested": 1024,
    "hdf5_signature_received": False,
    "orbit_type_read": False,
    "geometry_datasets_read": False,
    "attitude_type_read": False,
    "dem_source_read": False,
    "radar_grid_spacing_read": False,
}
RECORDED_RETRIEVAL_TIMESTAMP_UTC = "2026-11-14T18:38:43Z"


def build_manifest(source_files: list[dict], dem_grids: list[dict], crop: dict, nisar: dict) -> dict:
    return {
        "mission": "011",
        "discovery_window": DISCOVERY_BBOX,
        "buffered_window": BUFFERED_BBOX,
        "dem_downloaded": True,
        "nisar_product_opened": nisar["opened"],
        "complete_hdf5_downloaded": False,
        **prohibited_outputs(),
        "copernicus_dem_files": source_files,
        "dem_grids": dem_grids,
        "crop": crop,
        "nisar": nisar,
        "vertical_reference": vertical_reference_note(),
    }


def prohibited_outputs() -> dict:
    return {
        "slope_or_aspect_created": False,
        "shadow_mask_created": False,
        "layover_mask_created": False,
        "terrain_correction_applied": False,
        "water_reclassified": False,
        "mission006_thresholds_changed": False,
        "area_calculated": False,
        "shoreline_calculated": False,
        "complete_hdf5_downloaded": False,
    }


def select_window(array, geotransform, west, south, east, north):
    x_centers, y_centers = sample_center_axes(geotransform, array.shape[1], array.shape[0])
    columns = [index for index, value in enumerate(x_centers) if west <= value <= east]
    rows = [index for index, value in enumerate(y_centers) if south <= value <= north]
    if not columns or not rows:
        return None
    selected = array[rows[0] : rows[-1] + 1, columns[0] : columns[-1] + 1]
    return selected, [x_centers[index] for index in columns], [y_centers[index] for index in rows]


def measure_geotiff(path: Path) -> dict:
    import os

    os.environ["GDAL_PAM_ENABLED"] = "NO"
    from osgeo import gdal

    gdal.SetConfigOption("GDAL_PAM_ENABLED", "NO")
    gdal.UseExceptions()
    dataset = gdal.Open(str(path), gdal.GA_ReadOnly)
    band = dataset.GetRasterBand(1)
    spatial = dataset.GetSpatialRef()
    values = band.ReadAsArray()
    nodata = band.GetNoDataValue()
    if nodata is None:
        valid = int(values.size)
        missing = 0
        finite = values
    else:
        missing = int((values == nodata).sum())
        valid = int(values.size - missing)
        finite = values[values != nodata]
    metadata = dataset.GetMetadata() or {}
    return {
        "name": path.name,
        "width": dataset.RasterXSize,
        "height": dataset.RasterYSize,
        "bands": dataset.RasterCount,
        "dtype": gdal.GetDataTypeName(band.DataType),
        "nodata": nodata,
        "horizontal_crs": f"EPSG:{spatial.GetAuthorityCode(None)}" if spatial is not None and spatial.GetAuthorityCode(None) else None,
        "geotransform": list(dataset.GetGeoTransform()),
        "area_or_point": metadata.get("AREA_OR_POINT"),
        "valid_count": valid,
        "nodata_count": missing,
        "minimum": None if valid == 0 else float(finite.min()),
        "maximum": None if valid == 0 else float(finite.max()),
        "values": values,
    }


def main() -> None:
    import json

    root = Path(__file__).resolve().parents[1]
    raw = root / "data" / "raw" / "mission011" / "copernicus_dem"
    files = []
    for path in sorted(raw.rglob("*")):
        if path.is_file():
            record = file_record(path)
            record["path"] = path.relative_to(root).as_posix()
            files.append(record)
    grids = []
    arrays = {}
    for path in sorted(raw.rglob("*.tif")):
        if "PREVIEW" in path.parts:
            continue
        measured = measure_geotiff(path)
        arrays[path.name] = measured.pop("values")
        grids.append(measured)
    north_name = "Copernicus_DSM_COG_10_N30_00_E079_00_DEM.tif"
    south_name = "Copernicus_DSM_COG_10_N29_00_E079_00_DEM.tif"
    north = next(item for item in grids if item["name"] == north_name)
    south = next(item for item in grids if item["name"] == south_name)
    seam = seam_between_grids(north["geotransform"], north["width"], north["height"], south["geotransform"], south["width"], south["height"])
    west, south_bound, east, north_bound = BUFFERED_BBOX
    north_window = select_window(arrays[north_name], north["geotransform"], west, south_bound, east, north_bound)
    south_window = select_window(arrays[south_name], south["geotransform"], west, south_bound, east, north_bound)
    stacked_rows = north_window[0].shape[0] + south_window[0].shape[0]
    stacked_cols = north_window[0].shape[1]
    import numpy as np

    recomputed = np.vstack([north_window[0], south_window[0]])
    crop_path = root / "data" / "derived" / "mission011" / "glo30_buffered_window_elevation.tif"
    crop_file = file_record(crop_path)
    crop_measured = measure_geotiff(crop_path) if crop_path.exists() else None
    stored_values = None if crop_measured is None else crop_measured.pop("values")
    values_match = stored_values is not None and stored_values.shape == recomputed.shape and bool(np.array_equal(stored_values, recomputed))
    crop = {
        "path": crop_path.relative_to(root).as_posix(),
        "present": crop_file["present"],
        "bytes": crop_file["bytes"],
        "sha256": crop_file["sha256"],
        "recomputed_width": stacked_cols,
        "recomputed_height": stacked_rows,
        "sample_centers": {
            "west": north_window[1][0],
            "east": north_window[1][-1],
            "north": north_window[2][0],
            "south": south_window[2][-1],
        },
        "matches_recomputed_shape": crop_measured is not None and crop_measured["width"] == stacked_cols and crop_measured["height"] == stacked_rows,
        "matches_recomputed_values": values_match,
        "shared_boundary_posting": seam["shared_sample_center"],
        "adjacent_center_spacing_deg": seam["center_separation_deg"],
        "source_values_altered": False,
    }
    xml_path = next(raw.rglob("Copernicus_DSM_10_N30_00_E079_00.xml"))
    statements = vertical_statements_from_xml(xml_path.read_text(encoding="utf-8"))
    destination = root / "data" / "manifests" / "mission011_terrain_geometry_acquisition.json"
    previous = json.loads(destination.read_text(encoding="utf-8")) if destination.exists() else None
    previous_files = previous.get("copernicus_dem_files", []) if previous else []
    inventory = compare_file_inventory(previous_files, files)
    manifest = build_manifest(files, grids, crop, NISAR_RECORD)
    manifest["retrieval_timestamp_utc"] = RECORDED_RETRIEVAL_TIMESTAMP_UTC
    manifest["downloaded_during_this_run"] = False
    manifest["record_source"] = "local files already stored by Mission 011"
    manifest["file_inventory_check"] = inventory
    manifest["seam"] = seam
    manifest["vertical_reference"]["xml_statements"] = statements
    manifest["vertical_reference"]["height_formula"] = "ellipsoidal height = orthometric height + geoid undulation, where undulation is ellipsoid minus geoid"
    manifest["vertical_reference"]["transformation_applied"] = False
    destination.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("FILES", len(files))
    print("CROP", crop["recomputed_width"], crop["recomputed_height"], crop["sha256"])
    print("SEAM_SHARED", seam["shared_sample_center"])
    print("DOWNLOADED_THIS_RUN", False)


if __name__ == "__main__":
    main()
