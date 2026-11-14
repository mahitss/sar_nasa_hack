"""Mission 010 terrain and radar-geometry feasibility.

Records source specifications and crop-size estimates. It does not download
a DEM, open a NISAR product, or run a shadow model.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data" / "manifests" / "mission010_terrain_geometry.json"

DISCOVERY_BBOX = [79.75, 30.03, 79.87, 30.15]
PLANNING_BUFFER_DEG = 0.05
GLO30_SPACING_ARCSEC = 1.0
GLO30_BYTES_PER_POSTING = 4

GSLC_VALID_SAMPLES_MASK = "/science/LSAR/GSLC/grids/frequencyA/mask"
GCOV_VALID_SAMPLES_MASK = "/science/LSAR/GCOV/grids/frequencyA/mask"

# Product Format Document 1.2.1 uses SSAR in the tables. Section 2.5.1 says the
# same paths apply to LSAR when SSAR is replaced by LSAR.
GEOMETRY_DATASETS = (
    "/science/LSAR/identification/lookDirection",
    "/science/LSAR/identification/orbitPassDirection",
    "/science/LSAR/GCOV/metadata/orbit/orbitType",
    "/science/LSAR/GCOV/metadata/orbit/time",
    "/science/LSAR/GCOV/metadata/orbit/interpMethod",
    "/science/LSAR/GCOV/metadata/orbit/position",
    "/science/LSAR/GCOV/metadata/orbit/velocity",
    "/science/LSAR/GCOV/metadata/attitude/time",
    "/science/LSAR/GCOV/metadata/attitude/quaternions",
    "/science/LSAR/GCOV/metadata/attitude/eulerAngles",
    "/science/LSAR/GCOV/metadata/ceosAnalysisReadyData/geometricAccuracy/bias/x",
    "/science/LSAR/GCOV/metadata/ceosAnalysisReadyData/geometricAccuracy/bias/y",
    "/science/LSAR/GCOV/metadata/ceosAnalysisReadyData/geometricAccuracy/standardDeviation/x",
    "/science/LSAR/GCOV/metadata/ceosAnalysisReadyData/geometricAccuracy/standardDeviation/y",
    "/science/LSAR/GCOV/metadata/processingInformation/inputs/demSource",
    "/science/LSAR/GCOV/metadata/processingInformation/inputs/demFiles",
    "/science/LSAR/GCOV/metadata/radarGrid/xCoordinates",
    "/science/LSAR/GCOV/metadata/radarGrid/yCoordinates",
    "/science/LSAR/GCOV/metadata/radarGrid/heightAboveEllipsoid",
    "/science/LSAR/GCOV/metadata/radarGrid/incidenceAngle",
    "/science/LSAR/GCOV/metadata/radarGrid/slantRange",
    "/science/LSAR/GCOV/metadata/radarGrid/losUnitVectorX",
    "/science/LSAR/GCOV/metadata/radarGrid/losUnitVectorY",
    "/science/LSAR/GCOV/metadata/radarGrid/elevationAngle",
    "/science/LSAR/GCOV/metadata/processingInformation/parameters/shadowMaskingApplied",
    "/science/LSAR/GSLC/metadata/radarGrid/incidenceAngle",
    "/science/LSAR/GSLC/metadata/radarGrid/slantRange",
    "/science/LSAR/GSLC/metadata/radarGrid/losUnitVectorX",
    "/science/LSAR/GSLC/metadata/radarGrid/losUnitVectorY",
)

FILENAME_ORBIT_EPHEMERIS = {"P": "POE", "M": "MOE", "N": "NOE", "F": "FOE"}


def geocells_for_bbox(west: float, south: float, east: float, north: float) -> list[tuple[int, int]]:
    if east <= west or north <= south:
        raise ValueError("bbox is empty")
    cells = []
    lat = math.floor(south)
    while lat < north:
        lon = math.floor(west)
        while lon < east:
            cells.append((lat, lon))
            lon += 1
        lat += 1
    return cells


def buffered_bbox(bbox: list[float], buffer_deg: float) -> list[float]:
    if buffer_deg < 0:
        raise ValueError("buffer must be zero or positive")
    west, south, east, north = bbox
    return [west - buffer_deg, south - buffer_deg, east + buffer_deg, north + buffer_deg]


def arcsec_postings(span_deg: float, spacing_arcsec: float = GLO30_SPACING_ARCSEC) -> int:
    if span_deg <= 0 or spacing_arcsec <= 0:
        raise ValueError("span and spacing must be positive")
    return int(round(span_deg * 3600 / spacing_arcsec)) + 1


def uncompressed_bytes(x_postings: int, y_postings: int, bytes_per_posting: int = GLO30_BYTES_PER_POSTING) -> int:
    return x_postings * y_postings * bytes_per_posting


def dged_stem(lat: int, lon: int) -> str:
    ns = "N" if lat >= 0 else "S"
    ew = "E" if lon >= 0 else "W"
    return f"Copernicus_DSM_10_{ns}{abs(lat):02d}_00_{ew}{abs(lon):03d}_00"


def nasadem_zip_name(lat: int, lon: int) -> str:
    ns = "n" if lat >= 0 else "s"
    ew = "e" if lon >= 0 else "w"
    return f"NASADEM_HGT_{ns}{abs(lat):02d}{ew}{abs(lon):03d}.zip"


def approximate_ground_posting_m(latitude_deg: float, spacing_arcsec: float = GLO30_SPACING_ARCSEC) -> dict:
    """Approximate ground spacing. This is not a surveyed posting."""
    lat_m = 111132 / 3600 * spacing_arcsec
    lon_m = 111320 * math.cos(math.radians(latitude_deg)) / 3600 * spacing_arcsec
    return {"north_south_m": lat_m, "east_west_m": lon_m, "latitude_deg": latitude_deg}


def orbit_labels_remain_unresolved(filename_code: str, orbit_type: str) -> dict:
    """Compare the filename ephemeris token with the HDF5 orbitType value.

    Section 2.2.4 maps filename code N to Near real-time Orbit Ephemeris (NOE).
    The same section also pairs N with Near real-time Radar Pointing (NRP).
    The HDF5 orbitType field is FOE, NOE, MOE, POE, or Custom. A disagreement
    is a cross-field inconsistency. It is not resolved here.
    """
    expected = FILENAME_ORBIT_EPHEMERIS.get(filename_code)
    if expected is None:
        consistency = "unknown"
        reason = "The filename code is not one of P, M, N, or F, so no expected ephemeris was assigned."
    elif expected == orbit_type:
        consistency = "match"
        reason = (
            "The filename ephemeris token and the HDF5 orbitType value use the same ephemeris name. "
            "That agreement has not been verified against the product file."
        )
    else:
        consistency = "mismatch"
        reason = (
            "Both fields describe orbit-ephemeris provenance, but the values disagree. "
            f"Product Format Document 1.2.1 section 2.2.4 maps filename code {filename_code} to {expected}. "
            f"The observed HDF5 orbitType value is {orbit_type}. "
            "The original values are unchanged and still require verification against the product metadata and provider guidance."
        )
    return {
        "filename_fidelity_code": filename_code,
        "filename_expected_orbit_ephemeris": expected,
        "observed_orbit_type": orbit_type,
        "internal_orbit_type": orbit_type,
        "consistency": consistency,
        "resolved": False,
        "verified_against_product_file": False,
        "reason": reason,
    }


def geometry_role(dataset_path: str) -> str:
    if dataset_path in {GSLC_VALID_SAMPLES_MASK, GCOV_VALID_SAMPLES_MASK}:
        return "valid-samples subswath mask, not a terrain, shadow, or layover mask"
    if dataset_path.endswith("shadowMaskingApplied"):
        return "scalar processing flag, not a per-pixel shadow mask"
    if dataset_path.endswith("incidenceAngle"):
        return "ellipsoid incidence cube at target height, not local slope incidence and not the 10 m image grid"
    if dataset_path.endswith(("lookDirection", "orbitPassDirection")):
        return "scene-level label, not a per-pixel incidence angle"
    if dataset_path.endswith("orbitType"):
        return "HDF5 orbit-ephemeris label. Filename code N expects NOE. An observed MOE value is a mismatch and is not resolved"
    if dataset_path.endswith("orbit/time"):
        return "time tags for the orbit position and velocity records, not read from these granules"
    if dataset_path.endswith("interpMethod"):
        return "orbit interpolation method, Hermite or Legendre in the format document, not read from these granules"
    if "orbit/position" in dataset_path or dataset_path.endswith("velocity"):
        return "orbit state vector in the WGS84 G1762 frame, not a per-pixel geometry raster"
    if dataset_path.endswith("attitude/time"):
        return "time tags for the attitude records, not read from these granules"
    if dataset_path.endswith("quaternions"):
        return "attitude quaternions, not read from these granules"
    if dataset_path.endswith("eulerAngles"):
        return "attitude Euler angles in degrees, not read from these granules"
    if "geometricAccuracy" in dataset_path:
        return "product-provided localization estimate in meters, not independent surveyed ground truth and not read from these granules"
    if dataset_path.endswith("demSource"):
        return "processor description of the DEM used to make the product, not inspected in these granules"
    if dataset_path.endswith("demFiles"):
        return "list of DEM files named by the processor, not inspected in these granules"
    if dataset_path.endswith("radarGrid/xCoordinates"):
        return "east coordinates of the radar-grid cube axis. The posting was not read"
    if dataset_path.endswith("radarGrid/yCoordinates"):
        return "north coordinates of the radar-grid cube axis. The posting was not read"
    if dataset_path.endswith("heightAboveEllipsoid"):
        return "heights above the WGS84 ellipsoid for the radar-grid height axis, not a DEM and not read"
    if "losUnitVector" in dataset_path or dataset_path.endswith(("slantRange", "elevationAngle")):
        return "radar-grid geometry cube, not the 10 m GCOV image grid"
    return "unclassified"


def crop_plan(bbox: list[float] | None = None, buffer_deg: float = PLANNING_BUFFER_DEG) -> dict:
    bbox = DISCOVERY_BBOX if bbox is None else bbox
    buffered = buffered_bbox(bbox, buffer_deg)
    cells = geocells_for_bbox(*buffered)
    span_x = buffered[2] - buffered[0]
    span_y = buffered[3] - buffered[1]
    postings = arcsec_postings(span_x), arcsec_postings(span_y)
    return {
        "discovery_bbox": bbox,
        "planning_buffer_deg": buffer_deg,
        "buffered_bbox": buffered,
        "geocells_lower_left": [{"latitude": lat, "longitude": lon, "dged_stem": dged_stem(lat, lon), "nasadem_zip": nasadem_zip_name(lat, lon)} for lat, lon in cells],
        "crop_postings": {"east_west": postings[0], "north_south": postings[1]},
        "uncompressed_elevation_bytes": uncompressed_bytes(*postings),
        "full_geocell_uncompressed_elevation_bytes": uncompressed_bytes(3601, 3601),
        "bytes_are_uncompressed_float32_elevation_only": True,
        "compressed_object_size": "not measured; no DEM object was requested",
        "downloaded": False,
    }


def build_manifest() -> dict:
    plan = crop_plan()
    return {
        "mission": "010",
        "discovery_window": {"crs": "EPSG:4326", "bbox": DISCOVERY_BBOX, "role": "catalogue discovery window, not a lake boundary"},
        "dem_downloaded": False,
        "nisar_product_downloaded": False,
        "nisar_product_opened": False,
        "terrain_model_run": False,
        "shadow_or_layover_mask_created": False,
        "mission006_thresholds_changed": False,
        "candidate_patches_used_as_geometry_truth": False,
        "gslc_mask_used_as_terrain": False,
        "copernicus_dem": {
            "dataset_id": "COP-DEM_GLO-30-DGED",
            "product_level": "DSM",
            "handbook": "geo1988-copernicusdem-spe-002, version 6.1, 09 October 2026",
            "provider": "Copernicus DEM, edited WorldDEM DSM distributed through the Copernicus Data Space",
            "horizontal_crs": "WGS84-G1150, EPSG:4326",
            "vertical_datum": "EGM2008, EPSG:3855",
            "vertical_unit": "meters",
            "grid_spacing": "1.0 arc second",
            "delivery_unit": "1 degree by 1 degree",
            "data_type": "32-bit float GeoTIFF in the DGED profile",
            "stated_accuracy": {
                "absolute_vertical": "< 4 m LE90",
                "relative_vertical": "< 2 m LE90 where slope is at most 20 percent; < 4 m LE90 where slope is greater than 20 percent, within a 1 degree cell",
                "absolute_horizontal": "< 6 m CE90",
            },
            "access_url": "https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM",
            "handbook_url": "https://dataspace.copernicus.eu/sites/default/files/media/files/2026-10/geo1988-copernicusdem-spe-002_producthandbook_i6.1.pdf",
        },
        "nasadem": {
            "dataset_id": "NASADEM_HGT.001",
            "user_guide": "NASADEM User Guide V1.3, January 2025",
            "horizontal_crs": "WGS84",
            "vertical_datum": "EGM96 geoid for the merged integer hgt product",
            "grid_spacing": "1 arc second",
            "data_type": "2-byte signed integer heights",
            "acquisition_period": "SRTM 2000-02-11 to 2000-02-21, later reprocessed and void-filled",
            "collection_extent": "about 56 S to 60 N",
            "interchangeable_with_copernicus_dem": False,
            "access_url": "https://www.earthdata.nasa.gov/data/catalog/lpcloud-nasadem-hgt-001",
            "user_guide_url": "https://lpdaac.usgs.gov/documents/2237/NASADEM_User_Guide_V13.pdf",
        },
        "cartodem": {
            "provider": "NRSC / ISRO",
            "open_default": False,
            "access": "Bhuvan login, with a stated limit of 10 DEM tiles per day",
            "posting": "30 m or coarser described as a free download; finer than 30 m and the 10 m posting have separate clearance rules",
            "vertical_datum": "not established from the pages retrieved in this mission",
            "licence_limits": "single-user licence, no redistribution, and no internet hosting of the original product",
            "access_url": "https://bhuvan-app3.nrsc.gov.in/data/download/help/source/html/steps_to_download_data.htm",
        },
        "crop_plan": plan,
        "approximate_glo30_ground_posting_m": approximate_ground_posting_m(30.09),
        "nisar_geometry": {
            "product_format": "NISAR L and S Band Level-1 and Level-2 Data Product Format Document, version 1.2.1",
            "paths_are_lsar_forms_of_the_ssar_tables": True,
            "datasets": [{"path": path, "role": geometry_role(path)} for path in GEOMETRY_DATASETS],
            "not_terrain_masks": [GSLC_VALID_SAMPLES_MASK, GCOV_VALID_SAMPLES_MASK],
            "present_in_mission003_crops": [
                "/science/LSAR/GCOV/grids/frequencyA/HHHH",
                "/science/LSAR/GCOV/grids/frequencyA/HVHV",
                "/science/LSAR/GCOV/grids/frequencyA/numberOfLooks",
                GCOV_VALID_SAMPLES_MASK,
                GSLC_VALID_SAMPLES_MASK,
            ],
            "orbit_labels": orbit_labels_remain_unresolved("N", "MOE"),
            "source_hdf5_opened_in_this_mission": False,
        },
        "missing_inputs": [
            "A Copernicus DEM elevation array for the buffered window",
            "The GCOV radarGrid incidence, slant-range, line-of-sight, and coordinate-axis datasets from the source HDF5",
            "The scalar shadowMaskingApplied flag from the source HDF5",
            "The product geometric-accuracy estimates and the processing DEM source and file list",
            "A resolution of the filename N versus HDF5 orbitType MOE mismatch after the product file is checked",
            "An independent non-water target for a later geometry test",
        ],
        "validation_requirements": [
            "A reference target that is not a Mission 006 candidate patch",
            "Published sensor metadata for look direction, orbit pass, and the radar-grid cubes",
            "A DEM whose vertical datum and posting are stated",
            "A test that a known radar-facing slope and a known radar-away slope receive different geometry labels",
            "No fitting of a shadow rule to the candidate rasters",
        ],
    }


def main() -> None:
    MANIFEST_PATH.write_text(json.dumps(build_manifest(), indent=2) + "\n", encoding="utf-8")
    plan = crop_plan()
    print("GEOCELLS", len(plan["geocells_lower_left"]))
    print("CROP_BYTES", plan["uncompressed_elevation_bytes"])
    print("DOWNLOADED", False)


if __name__ == "__main__":
    main()
