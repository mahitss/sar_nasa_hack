"""Mission 012 access checks. Live Earthdata calls stay outside these functions."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qsl, urlsplit, urlunsplit

HDF5_SIGNATURE = bytes([0x89, 0x48, 0x44, 0x46, 0x0D, 0x0A, 0x1A, 0x0A])
TRANSFER_BUDGET_BYTES = 64 * 1024 * 1024
SECRET_QUERY_KEYS = {
    "token",
    "access_token",
    "signature",
    "sig",
    "credential",
    "x-amz-signature",
    "x-amz-security-token",
    "x-amz-credential",
    "awsaccesskeyid",
}

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


def hdf5_signature_offset(blob: bytes) -> int | None:
    limit = min(len(blob), 8192)
    for offset in range(0, max(0, limit - 7)):
        if blob[offset : offset + 8] == HDF5_SIGNATURE:
            return offset
    return None


def classify_probe(status: int, content_type: str, body: bytes, content_range: str | None) -> dict:
    kind = (content_type or "").split(";")[0].strip().lower()
    if status == 200:
        return {"action": "close_without_reading_body", "hdf5_signature": False, "reason": "HTTP 200 is not a bounded partial response"}
    if status != 206:
        return {"action": "reject", "hdf5_signature": False, "reason": f"HTTP {status}"}
    if "json" in kind or "html" in kind:
        return {"action": "reject", "hdf5_signature": False, "reason": f"content type {kind}"}
    offset = hdf5_signature_offset(body)
    return {
        "action": "accept" if offset is not None else "reject",
        "hdf5_signature": offset is not None,
        "signature_offset": offset,
        "content_range": content_range,
        "bytes_received": len(body),
    }


def redact_url(url: str) -> str:
    parts = urlsplit(url)
    kept = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key.lower() not in SECRET_QUERY_KEYS]
    query = "&".join(f"{key}={value}" for key, value in kept)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, ""))


def redirect_summary(statuses: list[tuple[int, str]]) -> list[dict]:
    summary = []
    for status, url in statuses:
        parts = urlsplit(url)
        summary.append({"status": status, "host": parts.hostname, "query_removed": bool(parts.query)})
    return summary


def parse_gcov_filename(name: str) -> dict:
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
    }


def consistency(filename: str, orbit_type: str | None, attitude_type: str | None) -> dict:
    parsed = parse_gcov_filename(filename)
    if orbit_type is None:
        orbit_status = "not_read"
    elif orbit_type == parsed["expected_orbit_ephemeris"]:
        orbit_status = "match"
    else:
        orbit_status = "mismatch"
    if attitude_type is None:
        pointing_status = "not_read"
    elif attitude_type == parsed["expected_radar_pointing"]:
        pointing_status = "match"
    else:
        pointing_status = "mismatch"
    return {
        "expected_orbit_ephemeris": parsed["expected_orbit_ephemeris"],
        "observed_orbit_type": orbit_type,
        "orbit_consistency": orbit_status,
        "expected_radar_pointing": parsed["expected_radar_pointing"],
        "observed_attitude_type": attitude_type,
        "pointing_consistency": pointing_status,
        "resolved": False,
        "geolocation_error_inferred": False,
    }


def enforce_budget(already: int, incoming: int, limit: int = TRANSFER_BUDGET_BYTES) -> None:
    if already + incoming > limit:
        raise RuntimeError("transfer budget reached")


def recorded_inspection() -> dict:
    """Metadata read on 2026-11-15 through earthaccess 0.19.0 HTTPS streaming.

    Re-running this function does not contact the network.
    """
    geometry = {
        "x_count": 710,
        "y_count": 699,
        "height_count": 21,
        "x_minimum_m": 296250.0,
        "x_maximum_m": 650750.0,
        "y_minimum_m": 3221250.0,
        "y_maximum_m": 3570250.0,
        "height_minimum_m": -1000.0,
        "height_maximum_m": 9000.0,
        "x_step_m": 500.0,
        "y_step_m": -500.0,
        "height_step_m": 500.0,
        "uniform_steps_verified_on": "20260906",
        "incidence_shape": [21, 699, 710],
        "incidence_dtype": "float32",
        "incidence_units": "degrees",
        "incidence_valid_min": 0.0,
        "incidence_valid_max": 90.0,
        "cube_values_read": False,
    }
    common = {
        "look_direction": "Left",
        "orbit_pass_direction": "Descending",
        "orbit_type": "MOE",
        "orbit_interp_method": "Hermite",
        "attitude_type": "Custom",
        "attitude_type_path": "/science/LSAR/GCOV/metadata/attitude/attitudeType",
        "shadow_masking_applied": "False",
        "shadow_masking_dtype": "fixed-length string",
        "dem_files_present": False,
        "dem_source_identity": "NISAR DEM version 1.2, Copernicus DEM 30 m release 2023_1, COP-DEM_GLO-30-DGED/2023_1, referenced to the WGS84 ellipsoid",
        "dem_source_doi": "10.5067/NIDEM-1",
        "geometric_accuracy_bias_x": "NaN",
        "geometric_accuracy_bias_y": "NaN",
        "geometric_accuracy_standard_deviation_x": "NaN",
        "geometric_accuracy_standard_deviation_y": "NaN",
        "orbit_time_count": 45,
        "orbit_position_shape": [45, 3],
        "orbit_velocity_shape": [45, 3],
        "attitude_time_count": 126,
        "quaternion_shape": [126, 4],
        "euler_shape": [126, 3],
        "radar_grid": geometry,
        "wrapper_bytes_read": 68021,
        "signature_probe_bytes": 8192,
        "hdf5_signature_offset": 0,
    }
    return {
        "20260906": common,
        "20260930": dict(common),
    }


def build_manifest() -> dict:
    inspection = recorded_inspection()
    products = {}
    names = {
        "20260906": "NISAR_L2_PR_GCOV_030_005_D_073_4005_DHDH_A_20260906T132236_20260906T132311_P05023_N_F_J_001.h5",
        "20260930": "NISAR_L2_PR_GCOV_032_005_D_073_4005_DHDH_A_20260930T132236_20260930T132311_P05023_N_F_J_001.h5",
    }
    for date, metadata in inspection.items():
        products[date] = {
            "filename": names[date],
            "https_signature": True,
            "metadata_inspection": True,
            "complete_file_stored": False,
            **metadata,
            "consistency": consistency(names[date], metadata["orbit_type"], metadata["attitude_type"]),
        }
    return {
        "mission": "012",
        "earthaccess_version": "0.19.0",
        "authentication": {
            "method": "earthaccess.login(strategy='netrc')",
            "netrc_environment_variable_set": True,
            "windows_default_filename_checked": "_netrc",
            "existing_file_is_dot_netrc": True,
            "credential_file_modified": False,
            "succeeded": True,
        },
        "cmr_exact_granules": True,
        "gdal_fallback_attempted": False,
        "gdal_reason": "Earthaccess HTTPS streaming returned a valid HDF5 signature, so the GDAL fallback was not required.",
        "direct_s3_attempted": False,
        "products": products,
        **prohibited_outputs(),
    }


def prohibited_outputs() -> dict:
    return {
        "complete_hdf5_downloaded": False,
        "shadow_mask_created": False,
        "layover_mask_created": False,
        "slope_or_aspect_created": False,
        "water_reclassified": False,
        "area_calculated": False,
        "shoreline_calculated": False,
    }


def main() -> None:
    import json

    destination = Path(__file__).resolve().parents[1] / "data" / "manifests" / "mission012_nisar_access.json"
    destination.write_text(json.dumps(build_manifest(), indent=2) + "\n", encoding="utf-8")
    print("PRODUCTS", len(build_manifest()["products"]))
    print("HDF5_DOWNLOADED", False)


if __name__ == "__main__":
    main()
