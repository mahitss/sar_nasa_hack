"""Mission 015 — NISAR radar geometry prototype and numerical validation.

Prototype only. Evaluates two independent approaches for reconstructing local
geometry at ~30 m DEM sample locations and documents a numerical error budget.

No production shadow/layover raster. No water reclassification, no area, no
shoreline, no physical-class labels. No Mission 005/006 modification.

Live NISAR geometry values are read from a compact recorded window under
gitignored data/raw/mission015/. All functions here are pure and deterministic.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW_PATH = ROOT / "data" / "raw" / "mission015" / "nisar_geometry_window_20260906.json"
GEOID_PGM = ROOT / "data" / "raw" / "mission014" / "geoids" / "egm2008-2_5.pgm"
DEM_CROP = ROOT / "data" / "derived" / "mission011" / "glo30_buffered_window_elevation.tif"

# WGS84 ellipsoid
A_EARTH = 6378137.0
F_EARTH = 1.0 / 298.257223563
E2 = F_EARTH * (2.0 - F_EARTH)

# Radar grid parameters (from recorded product axes)
RADAR_X0, RADAR_DX = 296250.0, 500.0
RADAR_Y0, RADAR_DY = 3570250.0, -500.0

EGM_OFFSET, EGM_SCALE = -108.0, 0.003
EGM_W, EGM_H = 8640, 4321


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_window() -> dict:
    if not WINDOW_PATH.exists():
        raise FileNotFoundError("NISAR geometry window not present")
    return json.loads(WINDOW_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Geoid and DEM height conversion
# ---------------------------------------------------------------------------

def geoid_undulation(lat: float, lon: float) -> float:
    """Bilinear EGM2008 2.5' undulation N (m) from the verified PGM grid."""
    import struct

    if not GEOID_PGM.exists():
        raise FileNotFoundError("EGM2008 grid not present")
    raw = GEOID_PGM.read_bytes()
    pos = 0
    lines = 0
    while lines < 3:
        nl = raw.find(b"\n", pos)
        line = raw[pos:nl]
        pos = nl + 1
        if line.startswith(b"#"):
            continue
        lines += 1
    data_off = pos
    dlat = 180.0 / (EGM_H - 1)
    dlon = 360.0 / EGM_W
    fi = (90.0 - lat) / dlat
    fj = (lon % 360.0) / dlon
    i0 = int(math.floor(fi))
    j0 = int(math.floor(fj))
    i1 = min(i0 + 1, EGM_H - 1)
    j1 = (j0 + 1) % EGM_W
    di, dj = fi - i0, fj - j0

    def pix(i, j):
        idx = data_off + (i * EGM_W + j) * 2
        return struct.unpack_from(">H", raw, idx)[0]

    h00 = EGM_OFFSET + EGM_SCALE * pix(i0, j0)
    h01 = EGM_OFFSET + EGM_SCALE * pix(i0, j1)
    h10 = EGM_OFFSET + EGM_SCALE * pix(i1, j0)
    h11 = EGM_OFFSET + EGM_SCALE * pix(i1, j1)
    return (h00 * (1 - di) + h10 * di) * (1 - dj) + (h01 * (1 - di) + h11 * di) * dj


def orthometric_to_ellipsoidal(orthometric_h: float, lat: float, lon: float) -> tuple[float, float]:
    """h = H + N. Returns (ellipsoidal_height, geoid_undulation)."""
    n = geoid_undulation(lat, lon)
    return orthometric_h + n, n


def dem_sample_height(lat: float, lon: float) -> float | None:
    """Read orthometric DEM elevation at lat/lon from the Mission 011 crop."""
    try:
        import rasterio
    except ImportError:
        return None
    if not DEM_CROP.exists():
        return None
    with rasterio.open(DEM_CROP) as ds:
        row, col = ds.index(lon, lat)
        if row < 0 or row >= ds.height or col < 0 or col >= ds.width:
            return None
        val = ds.read(1)[row, col]
        if not math.isfinite(val):
            return None
        return float(val)


# ---------------------------------------------------------------------------
# Coordinate transforms (WGS84)
# ---------------------------------------------------------------------------

def geodetic_to_ecef(lat: float, lon: float, h: float) -> tuple[float, float, float]:
    """Geodetic (lat, lon in degrees, h ellipsoidal meters) to ECEF (m)."""
    lat_r, lon_r = math.radians(lat), math.radians(lon)
    sin_lat, cos_lat = math.sin(lat_r), math.cos(lat_r)
    sin_lon, cos_lon = math.sin(lon_r), math.cos(lon_r)
    n = A_EARTH / math.sqrt(1.0 - E2 * sin_lat * sin_lat)
    x = (n + h) * cos_lat * cos_lon
    y = (n + h) * cos_lat * sin_lon
    z = (n * (1.0 - E2) + h) * sin_lat
    return x, y, z


def enu_basis(lat: float, lon: float) -> tuple[tuple, tuple, tuple]:
    """Local East, North, Up unit vectors in ECEF."""
    lat_r, lon_r = math.radians(lat), math.radians(lon)
    sin_lat, cos_lat = math.sin(lat_r), math.cos(lat_r)
    sin_lon, cos_lon = math.sin(lon_r), math.cos(lon_r)
    east = (-sin_lon, cos_lon, 0.0)
    north = (-sin_lat * cos_lon, -sin_lat * sin_lon, cos_lat)
    up = (cos_lat * cos_lon, cos_lat * sin_lon, sin_lat)
    return east, north, up


def dot(a, b) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def sub(a, b) -> tuple:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def norm(a) -> float:
    return math.sqrt(dot(a, a))


def unit(a) -> tuple:
    n = norm(a)
    return (a[0] / n, a[1] / n, a[2] / n)


# ---------------------------------------------------------------------------
# Interpolation
# ---------------------------------------------------------------------------

def bilinear_2d(arr: list, x: float, y: float) -> float | None:
    """Bilinear interpolation into a 2D array indexed [row][col] at float (x=col, y=row)."""
    rows, cols = len(arr), len(arr[0])
    c0 = int(math.floor(x))
    r0 = int(math.floor(y))
    c1, r1 = min(c0 + 1, cols - 1), min(r0 + 1, rows - 1)
    if c0 < 0 or c0 >= cols or r0 < 0 or r0 >= rows:
        return None
    vals = [arr[r0][c0], arr[r0][c1], arr[r1][c0], arr[r1][c1]]
    if any((v is None) or (isinstance(v, float) and not math.isfinite(v)) for v in vals):
        return None
    dx, dy = x - c0, y - r0
    top = vals[0] * (1 - dx) + vals[1] * dx
    bot = vals[2] * (1 - dx) + vals[3] * dx
    return top * (1 - dy) + bot * dy


def trilinear_3d(arr: list, h: float, y: float, x: float) -> float | None:
    """Trilinear interpolation into cube [h][y][x]."""
    d0 = int(math.floor(h))
    if d0 < 0 or d0 + 1 >= len(arr):
        return None
    v00 = bilinear_2d(arr[d0], x, y)
    v10 = bilinear_2d(arr[d0 + 1], x, y)
    if v00 is None or v10 is None:
        return None
    dh = h - d0
    return v00 * (1 - dh) + v10 * dh


def lerp(a: float, b: float, t: float) -> float:
    return a * (1 - t) + b * t


def interpolate_orbit(times: list, vectors: list, t: float) -> tuple | None:
    """Linear interpolation of orbit state vector (position or velocity) at time t."""
    if t < times[0] or t > times[-1]:
        return None
    for i in range(len(times) - 1):
        if times[i] <= t <= times[i + 1]:
            frac = (t - times[i]) / (times[i + 1] - times[i])
            v0, v1 = vectors[i], vectors[i + 1]
            return tuple(lerp(v0[k], v1[k], frac) for k in range(3))
    return None


def slerp(q0: list, q1: list, t: float) -> list:
    """Spherical linear interpolation of two quaternions [w,x,y,z]."""
    dotq = sum(q0[k] * q1[k] for k in range(4))
    if dotq < 0.0:
        q1 = [-v for v in q1]
        dotq = -dotq
    dotq = max(-1.0, min(1.0, dotq))
    if dotq > 0.9995:
        return [lerp(q0[k], q1[k], t) for k in range(4)]
    theta0 = math.acos(dotq)
    theta = theta0 * t
    sin_theta0 = math.sin(theta0)
    s0 = math.sin(theta0 - theta) / sin_theta0
    s1 = math.sin(theta) / sin_theta0
    return [s0 * q0[k] + s1 * q1[k] for k in range(4)]


def interpolate_quaternion(times: list, quats: list, t: float) -> list | None:
    """Slerp quaternion record at time t."""
    if t < times[0] or t > times[-1]:
        return None
    for i in range(len(times) - 1):
        if times[i] <= t <= times[i + 1]:
            frac = (t - times[i]) / (times[i + 1] - times[i])
            return slerp(quats[i], quats[i + 1], frac)
    return None


# ---------------------------------------------------------------------------
# Geometry reconstruction
# ---------------------------------------------------------------------------

def incidence_from_los(los_ecef: tuple, lat: float, lon: float) -> float:
    """Incidence angle (deg) between LOS (target->sensor) and local ellipsoid normal."""
    _, _, up = enu_basis(lat, lon)
    cos_inc = dot(unit(los_ecef), up)
    cos_inc = max(-1.0, min(1.0, abs(cos_inc)))
    return math.degrees(math.acos(cos_inc))


def approach_a_value(data: dict, field: str, h_idx: float, y_idx: float, x_idx: float) -> float | None:
    """Approach A: interpolate a product radar-grid cube at GLOBAL (h,y,x) indices.

    The recorded window is a local slice; global indices are shifted by the
    window's recorded lower bounds before interpolation.
    """
    w = data["window_indices"]
    lh = h_idx - w["h"][0]
    ly = y_idx - w["y"][0]
    lx = x_idx - w["x"][0]
    # The window holds h in [h0, h1) as local rows 0..(h1-h0-1)
    return trilinear_3d(data[field], lh, ly, lx)


def approach_a_incidence(data: dict, h_idx: float, y_idx: float, x_idx: float) -> float | None:
    """Approach A: interpolate product incidence cube at radar-grid (h,y,x) indices."""
    return approach_a_value(data, "incidenceAngle", h_idx, y_idx, x_idx)


def approach_b_incidence(data: dict, lat: float, lon: float, h_ellipsoidal: float, t: float) -> dict | None:
    """Approach B: reconstruct LOS from interpolated orbit position and local normal."""
    pos = interpolate_orbit(data["orbit_time"], data["orbit_position"], t)
    if pos is None:
        return None
    target_ecef = geodetic_to_ecef(lat, lon, h_ellipsoidal)
    los = sub(pos, target_ecef)
    slant = norm(los)
    inc = incidence_from_los(los, lat, lon)
    quat = interpolate_quaternion(data["attitude_time"], data["attitude_quaternions"], t)
    return {
        "sensor_ecef": pos,
        "target_ecef": target_ecef,
        "los_unit": unit(los),
        "slant_range_m": slant,
        "incidence_deg": inc,
        "quaternion": quat,
    }


def radar_indices_from_utm(easting: float, northing: float) -> tuple[float, float]:
    """Continuous radar-grid (x, y) indices from UTM easting/northing (m)."""
    x = (easting - RADAR_X0) / RADAR_DX
    y = (RADAR_Y0 - northing) / (-RADAR_DY)
    return x, y


# ---------------------------------------------------------------------------
# Error budget and manifest
# ---------------------------------------------------------------------------

def error_budget() -> dict:
    return {
        "dem_elevation_error_m": {"value": 4.0, "type": "LE90 absolute, Copernicus GLO-30 (Mission 010)", "note": "relative <2 m where slope <=20%"},
        "geoid_interpolation_error_m": {"value": 0.135, "type": "max bilinear EGM2008 2.5'", "note": "cubic max 0.031 m"},
        "radar_grid_interpolation_error_m": {"value": None, "type": "must be measured", "note": "500 m posting sampled to 30 m; no new physical information"},
        "orbit_interpolation_error_m": {"value": None, "type": "unmeasured", "note": "45 states ~10 s; MOE geolocation not measured"},
        "attitude_interpolation_error_m": {"value": None, "type": "unmeasured", "note": "126 quaternion records; Custom attitude type"},
        "coordinate_transform_error_m": {"value": 0.001, "type": "double-precision ECEF transform", "note": "numerical only; excludes datum differences"},
        "combined_uncertainty": "NOT a simple sum; components are correlated and several unmeasured. Report separately; quantify only after measuring radar-grid/orbit/attitude errors.",
    }


def approach_comparison(data: dict | None = None) -> dict:
    """Compare Approach A and B at common real sample locations within the recorded window."""
    if data is None:
        data = load_window()
    try:
        from pyproj import Transformer
    except ImportError:
        return {"status": "pyproj unavailable; comparison not computed"}
    tr = Transformer.from_crs("EPSG:32644", "EPSG:4326", always_xy=True)
    heights = data["heightAboveEllipsoid"]
    orbit_t = sum(data["orbit_time"]) / len(data["orbit_time"])
    samples = []
    for xi in range(171, 187, 2):
        for yi in range(475, 491, 2):
            easting = RADAR_X0 + xi * RADAR_DX
            northing = RADAR_Y0 + yi * RADAR_DY
            lon, lat = tr.transform(easting, northing)
            H = dem_sample_height(lat, lon)
            if H is None:
                continue
            h_ell, N = orthometric_to_ellipsoidal(H, lat, lon)
            hi = (h_ell - heights[0]) / (heights[1] - heights[0])
            if hi >= 6.8:  # stay inside recorded window with margin
                continue
            b = approach_b_incidence(data, lat, lon, h_ell, orbit_t)
            a = approach_a_incidence(data, hi, yi, xi)
            if b is not None and a is not None:
                samples.append({
                    "radar_index": [xi, yi],
                    "latlon": [round(lat, 6), round(lon, 6)],
                    "dem_orthometric_m": round(H, 3),
                    "geoid_N_m": round(N, 3),
                    "ellipsoidal_h_m": round(h_ell, 3),
                    "A_incidence_deg": round(a, 4),
                    "B_incidence_deg": round(b["incidence_deg"], 4),
                    "incidence_diff_deg": round(a - b["incidence_deg"], 4),
                    "A_slant_range_m": None,
                    "B_slant_range_m": round(b["slant_range_m"], 1),
                })
    if not samples:
        return {"status": "no common samples inside recorded window"}
    diffs = sorted(abs(s["incidence_diff_deg"]) for s in samples)
    return {
        "status": "computed",
        "sample_count": len(samples),
        "incidence_abs_diff_deg": {
            "minimum": round(diffs[0], 4),
            "maximum": round(diffs[-1], 4),
            "median": round(diffs[len(diffs) // 2], 4),
            "mean": round(sum(diffs) / len(diffs), 4),
        },
        "samples": samples,
    }


def build_manifest() -> dict:
    data = load_window()
    return {
        "mission": "015",
        "title": "NISAR Geometry Prototype & Numerical Validation",
        "final_decision": "CONDITIONAL GO",
        "scientific_measurement": False,
        "production_classification_product": False,
        "source_provenance": {
            "nisar_granule": data["granule"],
            "nisar_access": "earthaccess netrc authenticated bounded range reads",
            "dem": "Mission 011 Copernicus GLO-30 crop (EPSG:4326, 793x793)",
            "geoid": "Mission 014 NGA EGM2008 2.5' grid (SHA-256 verified)",
            "dem_vs_processor_release": "same family; exact 2023_1 release not proven (Mission 014 PARTIAL)",
        },
        "geometry_window": {
            "indices": data["window_indices"],
            "native_radar_grid": {"x_count": len(data["xCoordinates"]), "y_count": len(data["yCoordinates"]), "height_count": len(data["heightAboveEllipsoid"]), "spacing_m": 500},
            "orbit_records": len(data["orbit_time"]),
            "attitude_records": len(data["attitude_time"]),
            "incidence_observed_deg": [min(min(r) for r in data["incidenceAngle"]), max(max(r) for r in data["incidenceAngle"])],
        },
        "height_conversion": {"convention": "h = H + N", "geoid_grid_verified": True, "method": "bilinear EGM2008 2.5'"},
        "approach_A": {"name": "Product metadata interpolation", "method": "trilinear interpolation of radar-grid cube to DEM sample locations"},
        "approach_B": {"name": "Orbit and attitude reconstruction", "method": "linear orbit interpolation + slerp attitude + ECEF LOS reconstruction"},
        "approach_comparison": approach_comparison(data),
        "error_budget": error_budget(),
        "validation": {
            "synthetic_cases": ["flat", "radar-facing", "radar-away", "shadow", "layover", "height conversion", "geoid interpolation", "orbit interpolation", "quaternion interpolation", "invalid input"],
            "independent_terrain_target": "BLOCKED - no independently validated non-candidate target selected in this mission",
        },
        "prohibited_outputs": {
            "shadow_mask_created": False,
            "layover_mask_created": False,
            "water_reclassified": False,
            "candidate_threshold_changed": False,
            "water_area_calculated": False,
            "shoreline_calculated": False,
            "physical_class_labeled": False,
            "mission005_006_modified": False,
        },
        "conditions": [
            "Measure radar-grid-to-DEM interpolation error with an explicit error budget",
            "Quantify MOE orbit and Custom attitude interpolation error",
            "Select an independent non-candidate real terrain validation target",
            "Confirm local DEM release identity (2023_1) or quantify height differences",
        ],
    }


def main() -> None:
    out = ROOT / "data" / "manifests" / "mission015_geometry_validation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build_manifest(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("MISSION_015_DECISION: CONDITIONAL GO")
    print("MANIFEST:", out, out.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
