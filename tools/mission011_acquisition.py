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


def main() -> None:
    import json
    from datetime import datetime, timezone

    raw = Path(__file__).resolve().parents[1] / "data" / "raw" / "mission011" / "copernicus_dem"
    files = [file_record(path) for path in sorted(raw.rglob("*")) if path.is_file()]
    for record in files:
        record["path"] = Path(record["path"]).relative_to(raw.parents[3]).as_posix()
    manifest = build_manifest(
        files,
        [
            {
                "name": "Copernicus_DSM_COG_10_N30_00_E079_00_DEM.tif",
                "width": 3600,
                "height": 3600,
                "dtype": "Float32",
                "area_or_point": "Point",
                "geotransform": [78.99986111111112, 0.0002777777777777778, 0.0, 31.000138888888888, 0.0, -0.0002777777777777778],
                "horizontal_crs": "EPSG:4326",
                "nodata": None,
                "valid_count": 12960000,
                "nodata_count": 0,
                "minimum": 626.0,
                "maximum": 7804.015625,
            },
            {
                "name": "Copernicus_DSM_COG_10_N29_00_E079_00_DEM.tif",
                "width": 3600,
                "height": 3600,
                "dtype": "Float32",
                "area_or_point": "Point",
                "geotransform": [78.99986111111112, 0.0002777777777777778, 0.0, 30.000138888888888, 0.0, -0.0002777777777777778],
                "horizontal_crs": "EPSG:4326",
                "nodata": None,
                "valid_count": 12960000,
                "nodata_count": 0,
                "minimum": 196.6738739013672,
                "maximum": 2765.322998046875,
            },
        ],
        {
            "path": "data/derived/mission011/glo30_buffered_window_elevation.tif",
            "width": 793,
            "height": 793,
            "sample_centers": {"west": 79.7, "east": 79.92, "north": 30.2, "south": 29.98},
            "shared_boundary_posting": False,
            "adjacent_center_spacing_deg": 1 / 3600,
        },
        {
            "opened": False,
            "blocker": "Earthdata range reads redirected repeatedly and ended at HTTP 302 with content type application/json. GDAL /vsicurl/ did not return an HDF5 signature. The complete products were not downloaded.",
            "range_bytes_requested": 1024,
            "hdf5_signature_received": False,
            "orbit_type_read": False,
        },
    )
    manifest["retrieval_timestamp_utc"] = "2026-11-14T18:38:43Z"
    manifest["written_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    destination = Path(__file__).resolve().parents[1] / "data" / "manifests" / "mission011_terrain_geometry_acquisition.json"
    destination.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("FILES", len(files))
    print("NISAR_OPENED", False)


if __name__ == "__main__":
    main()
