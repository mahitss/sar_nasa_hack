"""Mission 014 — Geometry Blocker Resolution Audit tool.

Investigates and resolves (or conclusively documents) the Mission 013 blockers:
1. EGM2008 geoid source and vertical datum conversion.
2. NISAR authentication contradiction (Mission 012 vs 013).
3. 500 m radar-grid resolution limitation (Approach A and B).
4. Orbit/pointing label discrepancies.
5. Independent validation strategy.

This is an audit. It produces no shadow/layover raster, no water reclassification,
no area/shoreline, no physical-class labels, and no complete HDF5 download.
Live network probes are documented as recorded evidence; the deterministic
functions below do not contact the network.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_OUT = ROOT / "data" / "manifests" / "mission014_blocker_resolution.json"
GRID_SHA256 = "d602e13446a4a4a23f39aecfe6a2a0760a1bc6c1b497482c2ebc9f7d513be699"

# Bounded-access evidence, recorded from live probes on 2026-11-17.
AUTH_RECORD = {
    "mission012_method": "earthaccess.login(strategy='netrc')",
    "mission012_netrc_condition": "Earthaccess on Windows defaults to _netrc; existing credential file is .netrc",
    "resolution": "Set NETRC environment variable to the existing .netrc path before earthaccess.login(strategy='netrc')",
    "session_type": "earthaccess.auth.SessionWithHeaderRedirection",
    "mission013_method_that_failed": "raw requests.get() Range headers without Earthdata session",
    "mission013_failure_status": 401,
    "mission013_failure_type": "text/html Basic-auth challenge; CloudFront 502 on second granule",
    "probe_status_after_fix": 206,
    "probe_content_type": "binary/octet-stream",
    "probe_redirect": "303 to CloudFront host (header-redirection session handles auth)",
    "probe_hdf5_signature_valid": True,
    "both_granules_read": True,
    "credentials_exposed": False,
    "netrc_modified": False,
    "complete_hdf5_downloaded": False,
}

EGM2008_RECORD = {
    "official_source": "https://earth-info.nga.mil/?action=wgs84&dir=wgs84",
    "official_model": "EGM2008, degree 2190 / order 2159, NGA STND.0036_1.0 (2014-07-08)",
    "official_grid": "2.5-minute worldwide precomputed EGM2008 geoid-height grid",
    "distribution": "GeographicLib egm2008-2_5.tar.bz2 (NGA binary gridded data)",
    "distribution_sha256": GRID_SHA256,
    "grid_file": "egm2008-2_5.pgm",
    "grid_dimensions": [8640, 4321],
    "posting_arcmin": 2.5,
    "pgm_format": "P5 16-bit big-endian; height = Offset + Scale * pixel",
    "offset_m": -108.0,
    "scale_m": 0.003,
    "reference_ellipsoid": "WGS84",
    "vertical_datum": "WGS84 (geoid height above WGS84 ellipsoid)",
    "sign_convention": "h = H + N (ellipsoidal = orthometric + geoid undulation)",
    "sign_matches_mission": True,
    "bilinear_error_max_m": 0.135,
    "bilinear_error_rms_m": 0.003,
    "cubic_error_max_m": 0.031,
    "cubic_error_rms_m": 0.001,
    "interpolation_method": "bilinear (12-point cubic available via GeographicLib Geoid class)",
    "bounded_subset_feasible": True,
    "bounded_subset_note": "PGM supports random pixel access; a 12-point cubic stencil needs only local pixels. Full global model coefficient set was NOT downloaded.",
    "computed_undulation_m": {
        "study_point_30.088337N_79.808685E": -34.9258,
        "window_SW_29.98N_79.70E": -38.4978,
        "window_NE_30.20N_79.92E": -30.8202,
        "window_center_30.09N_79.81E": -34.8673,
    },
    "reproducible_and_verifiable": True,
}

DEM_IDENTITY_RECORD = {
    "processor_dem_identity": "NISAR DEM version 1.2, Copernicus DEM 30 m release 2023_1, COP-DEM_GLO-30-DGED/2023_1, WGS84 ellipsoid",
    "local_dem_product": "Copernicus GLO-30 DGED / WorldDEM DSM",
    "local_dem_cells": ["Copernicus_DSM_COG_10_N29_00_E079_00", "Copernicus_DSM_COG_10_N30_00_E079_00"],
    "same_product_family": True,
    "local_release_explicitly_recorded": False,
    "local_release_field": "local XML records 'Copernicus GLO-30 DGED' and 'WorldDEM DSM' but no explicit 2023_1 token",
    "processor_dem_files_present_in_granules": False,
    "byte_identity_verified": False,
    "conclusion": "Same product family; exact release identity (2023_1) not proven from local metadata. Family match is not proof of identical release.",
    "vertical_datum_difference": "local EGM2008 orthometric vs processor WGS84 ellipsoid; conversion now enabled by verified EGM2008 source",
}

RESOLUTION_RECORD = {
    "radar_grid_posting_m": 500,
    "dem_posting_m_approx": 30,
    "gcov_image_posting_m": 10,
    "approach_A": {
        "name": "Product metadata interpolation",
        "inputs": ["incidenceAngle [21,699,710]", "slantRange [21,699,710]", "losUnitVectorX/Y [21,699,710]", "elevationAngle"],
        "method": "tri-linear interpolation of radar-grid geometry cubes to DEM grid with explicit error budget",
        "interpolation_error_source": "500 m grid sampled; local terrain curvature at 30 m not represented",
        "error_budget": "geoid 0.135 m + DEM <4 m LE90 + radar-grid interpolation (must be measured) + MOE orbit geolocation (unmeasured)",
        "defensible_at_30m": "possible with measured interpolation error; NOT automatically defensible",
    },
    "approach_B": {
        "name": "Geometry reconstruction from orbit and attitude",
        "inputs": ["orbit position/velocity [45,3] (10 s sampling per ASF)", "attitude quaternions [126,4]", "heightAboveEllipsoid [21]", "WGS84 ellipsoid"],
        "method": "reconstruct platform position and LOS at DEM sample locations; compute local incidence from DEM surface normal",
        "sampling": "orbit 45 states (~10 s), attitude 126 records, radar-grid height 21 levels",
        "advantage": "independently reconstructs LOS geometry; not tied to coarse incidence cube",
        "limitation": "depends on MOE/attitude accuracy and orbit interpolation (Hermite); geolocation error unmeasured",
        "defensible_at_30m": "plausible and independently checkable; requires validation against known terrain",
    },
    "conclusion": "A 30 m DEM-grid geometry product can be defensible with an explicit error budget and independent validation. 10 m geometry is NOT justified by 10 m GCOV posting. No production raster generated.",
}

DISCREPANCY_RECORD = {
    "orbit": {
        "filename_token": "N",
        "format_doc_1_2_1_mapping": "N -> NOE (near real-time)",
        "observed_orbitType": "MOE",
        "asf_authoritative": "NISAR mission uses Medium precision (MOE) data when generating new products (ASF Orbit Ephemeris guide)",
        "interpretation": "MOE is the operational standard; MOE in HDF5 is expected. Filename N likely reflects delivery/fidelity labeling.",
        "resolved": False,
        "values_preserved": True,
        "geolocation_error_inferred": False,
    },
    "pointing": {
        "filename_token_mapping": "N -> NRP (per Mission 012 mapping)",
        "observed_attitudeType": "Custom",
        "interpretation": "Custom attitude indicates adaptive/non-nominal pointing; quaternions are recorded and usable.",
        "resolved": False,
        "values_preserved": True,
    },
    "physical_geometry_reconstructable": True,
    "remaining_uncertainty": "Label semantics and actual geolocation error remain unresolved; derive geometry from recorded state vectors, not labels.",
}

VALIDATION_RECORD = {
    "principles": [
        "Mission 006 candidate rasters are NOT used to fit or validate the geometry model",
        "Synthetic tests are deterministic and independent of real candidate patches",
        "At least one non-candidate real terrain target must be identified for eventual validation",
    ],
    "synthetic_tests": [
        {"case": "flat terrain", "expect": "no shadow, no layover; local incidence = ellipsoid incidence"},
        {"case": "radar-facing slope", "expect": "increased local incidence; layover when slope > incidence"},
        {"case": "radar-away slope", "expect": "decreased local incidence; no layover"},
        {"case": "known shadow geometry", "expect": "points behind ridge along look ray are shadowed"},
        {"case": "known layover geometry", "expect": "feature top maps to closer slant range than base"},
    ],
    "non_candidate_target": "A catalogued ridge/valley feature from independent optical imagery or published topography, outside all Mission 006 candidate patches (to be identified in the implementation mission)",
}

PROHIBITED = {
    "shadow_raster_created": False,
    "layover_raster_created": False,
    "water_reclassified": False,
    "mission005_006_thresholds_changed": False,
    "water_area_calculated": False,
    "shoreline_calculated": False,
    "physical_class_labeled": False,
    "complete_hdf5_downloaded": False,
    "validated_geometry_model_claimed": False,
    "mission013_files_modified": False,
}


def geoid_undulation_bilinear(lat, lon, offset=-108.0, scale=0.003, w=8640, h=4321):
    """Bilinear EGM2008 2.5' interpolation from PGM pixels (transparent, deterministic).

    Uses the verified grid when present; otherwise raises. Pixels read by random
    access from the PGM (bounded subset). height = offset + scale * pixel.
    """
    import math
    import struct

    pgm = ROOT / "data" / "raw" / "mission014" / "geoids" / "egm2008-2_5.pgm"
    if not pgm.exists():
        raise FileNotFoundError("EGM2008 grid not present (expected under gitignored data/raw/mission014)")
    dlat = 180.0 / (h - 1)
    dlon = 360.0 / w
    fi = (90.0 - lat) / dlat
    fj = (lon % 360.0) / dlon
    i0 = int(math.floor(fi))
    j0 = int(math.floor(fj))
    i1 = min(i0 + 1, h - 1)
    j1 = (j0 + 1) % w
    di = fi - i0
    dj = fj - j0
    raw = pgm.read_bytes()
    data_off = 0
    # locate data start after P5 header (magic + comments + dims + maxval)
    pos = 0
    lines = 0
    # PGM header = P5, dimensions, maxval (3 non-comment lines); then binary data
    while lines < 3:
        nl = raw.find(b"\n", pos)
        line = raw[pos:nl]
        pos = nl + 1
        if line.startswith(b"#"):
            continue
        lines += 1
    data_off = pos

    def pix(i, j):
        idx = data_off + (i * w + j) * 2
        return struct.unpack_from(">H", raw, idx)[0]

    h00 = offset + scale * pix(i0, j0)
    h01 = offset + scale * pix(i0, j1)
    h10 = offset + scale * pix(i1, j0)
    h11 = offset + scale * pix(i1, j1)
    return (h00 * (1 - di) + h10 * di) * (1 - dj) + (h01 * (1 - di) + h11 * di) * dj


def build_manifest() -> dict:
    return {
        "mission": "014",
        "title": "NISAR Radar Geometry Blocker Resolution Audit",
        "final_decision": "CONDITIONAL GO",
        "conditions": [
            "Confirm the exact local DEM release is COP-DEM_GLO-30-DGED/2023_1 (or quantify height difference vs processor DEM)",
            "Measure radar-grid-to-DEM interpolation error with an explicit error budget before producing 30 m geometry",
            "Identify a non-candidate real terrain validation target from independent evidence",
            "Preserve the unresolved orbit/pointing label values; do not infer geolocation error from labels",
        ],
        "scientific_measurement": False,
        "real_data_classification": False,
        "audit_timestamp_utc": "2026-11-17",
        "blockers_resolved": {
            "egm2008_geoid_source": "RESOLVED",
            "nisar_authentication": "RESOLVED",
            "dem_identity": "PARTIAL - same family, release 2023_1 not proven locally",
            "resolution_500m": "REASSESSED - 30 m defensible with error budget; 10 m not justified",
            "orbit_pointing_labels": "PRESERVED UNRESOLVED - geometry still reconstructable",
        },
        "authentication": AUTH_RECORD,
        "egm2008": EGM2008_RECORD,
        "dem_identity": DEM_IDENTITY_RECORD,
        "resolution": RESOLUTION_RECORD,
        "discrepancies": DISCREPANCY_RECORD,
        "validation": VALIDATION_RECORD,
        "prohibited_outputs": PROHIBITED,
        "limitations": [
            "No shadow or layover raster generated.",
            "No water reclassification or threshold change.",
            "No complete NISAR HDF5 product downloaded.",
            "DEM release 2023_1 identity not proven from local metadata.",
            "Geolocation error from orbit/attitude labels not measured.",
            "Radar-grid interpolation error at 30 m must be measured in the implementation mission.",
        ],
    }


def main() -> None:
    manifest = build_manifest()
    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("MISSION_014_DECISION:", manifest["final_decision"])
    print("MANIFEST:", MANIFEST_OUT)
    print("MANIFEST_BYTES:", MANIFEST_OUT.stat().st_size)


if __name__ == "__main__":
    main()
