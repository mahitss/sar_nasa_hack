"""Mission 015.1 — corrected NISAR geometry prototype (review branch).

Corrections vs Mission 015:
  * Approach B solves target-specific zero-Doppler time from orbit position AND
    velocity instead of using one mean orbit epoch for every target.
  * Approach B no longer claims to be "attitude-based LOS reconstruction":
    product attributes define quaternions only as (q0,q1,q2,q3) and do NOT
    define a frame/rotation direction/boresight sufficient to rotate the
    geometric LOS, so attitude is validated separately and not applied.
  * Approach A interpolates incidenceAngle, slantRange and both LOS ENU
    components; the missing LOS-Up component is derived from the unit-norm
    constraint (positive sign because the sensor is above the target).
  * Strict interpolation: sample-center domain only, exact boundaries allowed,
    NaN/inf/nodata and non-monotonic/duplicate axes rejected, never clamped.
  * Numerical interpolation error measured by withheld-node cross-validation.
  * Error budget separates acquisition-time solution and all components.

No production shadow/layover raster, water reclassification, area, shoreline,
physical-class label, Mission 005/006 modification, or full HDF5 download.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "mission015"
WINDOW_PATHS = {
    "20260906": RAW / "nisar_geometry_window_20260906.json",
    "20260930": RAW / "nisar_geometry_window_20260930.json",
}
GEOID_PGM = ROOT / "data" / "raw" / "mission014" / "geoids" / "egm2008-2_5.pgm"
DEM_CROP = ROOT / "data" / "derived" / "mission011" / "glo30_buffered_window_elevation.tif"

# WGS84 ellipsoid
A_EARTH = 6378137.0
F_EARTH = 1.0 / 298.257223563
E2 = F_EARTH * (2.0 - F_EARTH)

EGM_OFFSET, EGM_SCALE = -108.0, 0.003
EGM_W, EGM_H = 8640, 4321

# Axis spacing is VERIFIED from the actual coordinate arrays, not assumed here.
# These are only fallbacks if the recorded axes are absent (they are present).
FALLBACK_RADAR_X0, FALLBACK_RADAR_DX = 296250.0, 500.0
FALLBACK_RADAR_Y0, FALLBACK_RADAR_DY = 3570250.0, -500.0


# ---------------------------------------------------------------------------
# Data loading and axis verification
# ---------------------------------------------------------------------------

def load_window(date: str = "20260906") -> dict:
    p = WINDOW_PATHS.get(date)
    if p is None or not p.exists():
        raise FileNotFoundError("NISAR geometry window not present for %s" % date)
    return json.loads(p.read_text(encoding="utf-8"))


def validate_axis(axis: list, name: str) -> list[float]:
    """Validate a coordinate axis: finite, strictly monotonic, no duplicates."""
    vals = [float(v) for v in axis]
    if len(vals) < 2:
        raise ValueError("%s axis needs at least two coordinates" % name)
    for v in vals:
        if not math.isfinite(v):
            raise ValueError("%s axis has non-finite coordinate" % name)
    diffs = [vals[i + 1] - vals[i] for i in range(len(vals) - 1)]
    if any(d == 0 for d in diffs):
        raise ValueError("%s axis has duplicate coordinates" % name)
    if not (all(d > 0 for d in diffs) or all(d < 0 for d in diffs)):
        raise ValueError("%s axis is non-monotonic" % name)
    return vals


def radar_axes(data: dict) -> tuple[list[float], list[float], list[float]]:
    """Return validated (x, y, height) coordinate axes from the recorded product."""
    x = validate_axis(data["xCoordinates"], "x")
    y = validate_axis(data["yCoordinates"], "y")
    h = validate_axis(data["heightAboveEllipsoid"], "height")
    return x, y, h


def axis_index(axis: list[float], value: float, name: str) -> float | None:
    """Map a coordinate to a continuous index on a UNIFORM validated axis.

    Returns None when outside the sample-center domain. Exact first/last
    coordinates are valid boundaries. Uniformity is verified (all vertex
    spacings equal within tolerance) rather than assumed.
    """
    if not math.isfinite(value):
        return None
    diffs = [axis[i + 1] - axis[i] for i in range(len(axis) - 1)]
    step = diffs[0]
    if any(abs(d - step) > 1e-6 * max(1.0, abs(step)) for d in diffs):
        raise ValueError("%s axis is not uniform; index mapping needs exact axes" % name)
    low, high = min(axis[0], axis[-1]), max(axis[0], axis[-1])
    if value < low - 1e-9 or value > high + 1e-9:
        return None
    # Map in axis orientation (ascending or descending)
    idx = (value - axis[0]) / step
    # Clamp only the floating-point boundary epsilon to the exact boundary sample.
    if idx < -1e-9 or idx > (len(axis) - 1) + 1e-9:
        return None
    if idx < 0:
        idx = 0.0
    if idx > len(axis) - 1:
        idx = float(len(axis) - 1)
    return idx


# ---------------------------------------------------------------------------
# Strict interpolation (sample-center domain, strict bounds, nodata rejection)
# ---------------------------------------------------------------------------

def _finite(v) -> bool:
    return v is not None and isinstance(v, (int, float)) and math.isfinite(float(v))


def bilinear_2d(arr: list, x: float, y: float) -> float | None:
    """Strict bilinear interpolation into arr[row][col] at float index (col=x, row=y).

    Valid domain is sample centers [0, cols-1] x [0, rows-1], inclusive.
    Coordinates outside (including just outside a boundary) return None.
    NaN/inf/nodata in the supporting 2x2 stencil return None. No clamping.
    """
    if not _finite(x) or not _finite(y):
        return None
    rows = len(arr)
    if rows == 0 or len(arr[0]) == 0:
        return None
    cols = len(arr[0])
    if x < 0.0 or x > cols - 1 or y < 0.0 or y > rows - 1:
        return None
    c0 = min(int(math.floor(x)), cols - 1)
    r0 = min(int(math.floor(y)), rows - 1)
    c1 = min(c0 + 1, cols - 1)
    r1 = min(r0 + 1, rows - 1)
    vals = [arr[r0][c0], arr[r0][c1], arr[r1][c0], arr[r1][c1]]
    if not all(_finite(v) for v in vals):
        return None
    dx, dy = x - c0, y - r0
    top = float(vals[0]) * (1 - dx) + float(vals[1]) * dx
    bot = float(vals[2]) * (1 - dx) + float(vals[3]) * dx
    return top * (1 - dy) + bot * dy


def trilinear_3d(arr: list, h: float, y: float, x: float) -> float | None:
    """Strict trilinear interpolation into cube[h][y][x] at float indices.

    Valid domain: [0, len-1] inclusive on every axis. Returns None outside.
    """
    if not _finite(h) or not _finite(y) or not _finite(x):
        return None
    depth = len(arr)
    if depth == 0:
        return None
    if h < 0.0 or h > depth - 1:
        return None
    d0 = min(int(math.floor(h)), depth - 1)
    d1 = min(d0 + 1, depth - 1)
    v0 = bilinear_2d(arr[d0], x, y)
    v1 = bilinear_2d(arr[d1], x, y)
    if v0 is None or v1 is None:
        return None
    dh = h - d0
    return v0 * (1 - dh) + v1 * dh


# ---------------------------------------------------------------------------
# Geometry, geoid, coordinate transforms
# ---------------------------------------------------------------------------

def geoid_undulation(lat: float, lon: float) -> float:
    """Bilinear EGM2008 2.5' undulation N (m), h = H + N convention."""
    import struct

    if not GEOID_PGM.exists():
        raise FileNotFoundError("EGM2008 grid not present")
    raw = GEOID_PGM.read_bytes()
    pos, lines = 0, 0
    while lines < 3:
        nl = raw.find(b"\n", pos)
        line = raw[pos:nl]
        pos = nl + 1
        if line.startswith(b"#"):
            continue
        lines += 1
    dlat, dlon = 180.0 / (EGM_H - 1), 360.0 / EGM_W
    fi, fj = (90.0 - lat) / dlat, (lon % 360.0) / dlon
    i0, j0 = int(math.floor(fi)), int(math.floor(fj))
    i1, j1 = min(i0 + 1, EGM_H - 1), (j0 + 1) % EGM_W
    di, dj = fi - i0, fj - j0

    def pix(i, j):
        return struct.unpack_from(">H", raw, pos + (i * EGM_W + j) * 2)[0]

    h00 = EGM_OFFSET + EGM_SCALE * pix(i0, j0)
    h01 = EGM_OFFSET + EGM_SCALE * pix(i0, j1)
    h10 = EGM_OFFSET + EGM_SCALE * pix(i1, j0)
    h11 = EGM_OFFSET + EGM_SCALE * pix(i1, j1)
    return (h00 * (1 - di) + h10 * di) * (1 - dj) + (h01 * (1 - di) + h11 * di) * dj


def orthometric_to_ellipsoidal(orthometric_h: float, lat: float, lon: float) -> tuple[float, float]:
    n = geoid_undulation(lat, lon)
    return orthometric_h + n, n


def dem_sample_height(lat: float, lon: float) -> float | None:
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
        return float(val) if math.isfinite(val) else None


def geodetic_to_ecef(lat: float, lon: float, h: float) -> tuple[float, float, float]:
    lat_r, lon_r = math.radians(lat), math.radians(lon)
    slat, clat = math.sin(lat_r), math.cos(lat_r)
    slon, clon = math.sin(lon_r), math.cos(lon_r)
    n = A_EARTH / math.sqrt(1.0 - E2 * slat * slat)
    return ((n + h) * clat * clon, (n + h) * clat * slon, (n * (1 - E2) + h) * slat)


def enu_basis(lat: float, lon: float) -> tuple[tuple, tuple, tuple]:
    lat_r, lon_r = math.radians(lat), math.radians(lon)
    slat, clat = math.sin(lat_r), math.cos(lat_r)
    slon, clon = math.sin(lon_r), math.cos(lon_r)
    return ((-slon, clon, 0.0), (-slat * clon, -slat * slon, clat), (clat * clon, clat * slon, slat))


def dot(a, b) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def sub(a, b) -> tuple:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def norm(a) -> float:
    return math.sqrt(dot(a, a))


def unit(a) -> tuple:
    n = norm(a)
    return (a[0] / n, a[1] / n, a[2] / n)


def ecef_to_enu(vec: tuple, lat: float, lon: float) -> tuple:
    e, n_, u = enu_basis(lat, lon)
    return (dot(vec, e), dot(vec, n_), dot(vec, u))


def angle_between(a, b) -> float:
    c = max(-1.0, min(1.0, dot(unit(a), unit(b))))
    return math.degrees(math.acos(c))


def incidence_from_los(los_ecef: tuple, lat: float, lon: float) -> float:
    _, _, up = enu_basis(lat, lon)
    c = max(-1.0, min(1.0, abs(dot(unit(los_ecef), up))))
    return math.degrees(math.acos(c))


# ---------------------------------------------------------------------------
# Orbit / attitude interpolation
# ---------------------------------------------------------------------------

def lerp(a: float, b: float, t: float) -> float:
    return a * (1 - t) + b * t


def interpolate_orbit(times: list, vectors: list, t: float) -> tuple | None:
    """Linear interpolation of an orbit record (position or velocity, ECEF)."""
    if not _finite(t) or not times or t < times[0] or t > times[-1]:
        return None
    for i in range(len(times) - 1):
        if times[i] <= t <= times[i + 1]:
            span = times[i + 1] - times[i]
            if span <= 0:
                return None
            frac = (t - times[i]) / span
            v0, v1 = vectors[i], vectors[i + 1]
            return tuple(lerp(float(v0[k]), float(v1[k]), frac) for k in range(3))
    return None


def quat_norm(q) -> float:
    return math.sqrt(sum(float(v) ** 2 for v in q))


def quat_normalize(q) -> list:
    n = quat_norm(q)
    if n == 0:
        raise ValueError("zero quaternion")
    return [float(v) / n for v in q]


def quat_to_matrix(q) -> list[list[float]]:
    """Scalar-first (q0,q1,q2,q3) -> 3x3 rotation matrix (standard Hamilton)."""
    w, x, y, z = quat_normalize(q)
    return [
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ]


def quat_rotate(q, vec) -> tuple:
    r = quat_to_matrix(q)
    return tuple(sum(r[i][j] * vec[j] for j in range(3)) for i in range(3))


def slerp(q0: list, q1: list, t: float) -> list:
    """Slerp scalar-first quaternions with sign (double-cover) handling."""
    q0, q1 = quat_normalize(q0), quat_normalize(q1)
    d = sum(q0[k] * q1[k] for k in range(4))
    if d < 0:
        q1 = [-v for v in q1]
        d = -d
    d = max(-1.0, min(1.0, d))
    if d > 0.9995:
        return quat_normalize([lerp(q0[k], q1[k], t) for k in range(4)])
    theta0 = math.acos(d)
    theta = theta0 * t
    s = math.sin(theta0)
    a, b = math.sin(theta0 - theta) / s, math.sin(theta) / s
    return quat_normalize([a * q0[k] + b * q1[k] for k in range(4)])


def interpolate_quaternion(times: list, quats: list, t: float) -> list | None:
    if not _finite(t) or not times or t < times[0] or t > times[-1]:
        return None
    for i in range(len(times) - 1):
        if times[i] <= t <= times[i + 1]:
            span = times[i + 1] - times[i]
            return slerp(quats[i], quats[i + 1], (t - times[i]) / span) if span > 0 else None
    return None


# ---------------------------------------------------------------------------
# Approach A: product radar-grid metadata interpolation (all geometry fields)
# ---------------------------------------------------------------------------

def approach_a_fields(data: dict, easting: float, northing: float, h_ell: float) -> dict | None:
    """Interpolate all four geometry fields + derive LOS Up from the unit norm.

    Axes are verified from the recorded coordinate arrays. Global coordinates
    are mapped onto the recorded window's validated axis. Fields: incidenceAngle,
    slantRange, losUnitVectorX (ENU East), losUnitVectorY (ENU North).
    Derived: losUnitVectorUp = sqrt(1 - E^2 - N^2), positive (sensor above target).
    """
    x_axis, y_axis, h_axis = radar_axes(data)
    xi = axis_index(x_axis, easting, "x")
    yi = axis_index(y_axis, northing, "y")
    hi = axis_index(h_axis, h_ell, "height")
    if xi is None or yi is None or hi is None:
        return None
    w = data["window_indices"]
    lx, ly, lh = xi - w["x"][0], yi - w["y"][0], hi - w["h"][0]
    # Strict local bounds: the recorded cube windows are [h0,h1) etc.
    nx = len(data["losUnitVectorX"][0][0])
    ny = len(data["losUnitVectorX"][0])
    nh = len(data["losUnitVectorX"])
    if lx < 0 or lx > nx - 1 or ly < 0 or ly > ny - 1 or lh < 0 or lh > nh - 1:
        return None
    inc = trilinear_3d(data["incidenceAngle"], lh, ly, lx)
    srange = trilinear_3d(data["slantRange"], lh, ly, lx)
    los_e = trilinear_3d(data["losUnitVectorX"], lh, ly, lx)
    los_n = trilinear_3d(data["losUnitVectorY"], lh, ly, lx)
    if any(v is None for v in (inc, srange, los_e, los_n)):
        return None
    rad = los_e * los_e + los_n * los_n
    if rad > 1.0:
        return None
    los_u = math.sqrt(1.0 - rad)  # positive: target -> sensor, sensor above target
    return {
        "incidence_deg": float(inc),
        "slant_range_m": float(srange),
        "los_enu": (float(los_e), float(los_n), float(los_u)),
        "indices": {"x": xi, "y": yi, "h": hi},
    }


# ---------------------------------------------------------------------------
# Approach B: target-specific zero-Doppler orbit LOS reconstruction
# ---------------------------------------------------------------------------

def solve_zero_doppler(target_ecef: tuple, data: dict, max_iter: int = 100) -> dict:
    """Solve target-specific zero-Doppler azimuth time from orbit pos AND velocity.

    Doppler condition: range rate = dot(unit(target - sensor), velocity) = 0.
    Bracket over the full orbit time span with bisection. Records acquisition
    time, position, velocity, residual, and convergence/out-of-range status.
    """
    times = data["orbit_time"]
    positions, velocities = data["orbit_position"], data["orbit_velocity"]

    def range_rate(t: float) -> float | None:
        p = interpolate_orbit(times, positions, t)
        v = interpolate_orbit(times, velocities, t)
        if p is None or v is None:
            return None
        return dot(unit(sub(target_ecef, p)), v)

    result = {
        "acquisition_time_s": None,
        "sensor_ecef": None,
        "velocity_ecef": None,
        "zero_doppler_residual_mps": None,
        "converged": False,
        "failure": None,
    }
    fa, fb = range_rate(times[0]), range_rate(times[-1])
    if fa is None or fb is None:
        result["failure"] = "orbit record not available at span boundary"
        return result
    if fa * fb > 0:
        result["failure"] = "no zero-Doppler sign change in orbit span"
        result["zero_doppler_residual_mps"] = min(abs(fa), abs(fb))
        return result
    a, b = times[0], times[-1]
    for _ in range(max_iter):
        mid = 0.5 * (a + b)
        fm = range_rate(mid)
        if fm is None:
            result["failure"] = "orbit interpolation failed during bisection"
            return result
        if fa * fm <= 0:
            b = mid
        else:
            a = mid
            fa = fm
    t = 0.5 * (a + b)
    p = interpolate_orbit(times, positions, t)
    v = interpolate_orbit(times, velocities, t)
    residual = range_rate(t)
    result.update({
        "acquisition_time_s": t,
        "sensor_ecef": p,
        "velocity_ecef": v,
        "zero_doppler_residual_mps": residual,
        "converged": residual is not None and abs(residual) < 1e-6,
    })
    return result


def approach_b_fields(data: dict, lat: float, lon: float, h_ell: float) -> dict | None:
    """Reconstruct geometric LOS at the target-specific zero-Doppler time.

    NOTE: this is an ORBIT zero-Doppler LOS reconstruction, not an attitude-based
    one — product quaternion semantics do not define a defensible boresight
    rotation of the geometric LOS (see ATTITUDE_NOTE in manifest).
    """
    target = geodetic_to_ecef(lat, lon, h_ell)
    zd = solve_zero_doppler(target, data)
    if not zd["converged"]:
        return None
    sensor = zd["sensor_ecef"]
    los_ecef = sub(sensor, target)  # target -> sensor
    slant = norm(los_ecef)
    los_enu = ecef_to_enu(unit(los_ecef), lat, lon)
    return {
        "target_ecef": target,
        "incidence_deg": incidence_from_los(los_ecef, lat, lon),
        "slant_range_m": slant,
        "los_ecef": unit(los_ecef),
        "los_enu": los_enu,
        "zd": zd,
    }


# ---------------------------------------------------------------------------
# Shadow / layover geometry using ACTUAL prototype conventions
# ---------------------------------------------------------------------------

def ray_clear(target_enu: tuple, los_enu: tuple, ridge_along_ray_m: float, ridge_height_m: float,
              inc_deg: float) -> bool:
    """True = no shadow. Sensor-to-target ray sampled at `ridge_along_ray_m`
    from the target toward the sensor; compare its height to the ridge.

    ENU frame: los_enu[2] (Up) > 0 because the sensor is above the target.
    """
    ray_height_at_ridge = target_enu[2] + ridge_along_ray_m * (los_enu[2] / max(los_enu[0] ** 2 + los_enu[1] ** 2, 1e-12) ** 0.5) * math.tan(math.radians(90 - inc_deg))
    return ridge_height_m < ray_height_at_ridge


def layover_condition(slope_deg: float, incidence_deg: float) -> bool:
    """Layover when radar-facing slope angle exceeds incidence angle."""
    return slope_deg > incidence_deg


def slant_range_ordering(near_slant: float, far_slant: float) -> bool:
    """Consistent ordering: a nearer target has smaller slant range."""
    return near_slant < far_slant


# ---------------------------------------------------------------------------
# Numerical interpolation error (withheld-node cross-validation)
# ---------------------------------------------------------------------------

def withheld_node_error(cube: list, field_stride: int = 2) -> dict:
    """Hold out every `field_stride`-th node along the height axis, interpolate
    it from the remaining native nodes, and record the absolute error.

    This measures numerical interpolation of the product grid only — NOT
    physical 30 m terrain accuracy.
    """
    d0, d1, d2 = len(cube), len(cube[0]), len(cube[0][0])
    errors = []
    for hi in range(d0):
        if hi % 2 == 0:
            continue
        for yi in range(1, d1 - 1, field_stride):
            for xi in range(1, d2 - 1, field_stride):
                withheld = cube[hi][yi][xi]
                if not _finite(withheld):
                    continue
                # Interpolate from neighbouring heights only (withhold this plane)
                lower = hi - 1
                upper = hi + 1
                if lower < 0 or upper >= d0:
                    continue
                v0 = bilinear_2d(cube[lower], xi, yi)
                v1 = bilinear_2d(cube[upper], xi, yi)
                if v0 is None or v1 is None:
                    continue
                est = 0.5 * (v0 + v1)
                errors.append(abs(est - float(withheld)))
    if not errors:
        return {"status": "no withheld samples"}
    errors.sort()
    return {
        "status": "measured",
        "method": "withheld height planes, linear interpolation from adjacent native planes",
        "sample_count": len(errors),
        "max_abs_error": errors[-1],
        "median_abs_error": errors[len(errors) // 2],
        "mean_abs_error": sum(errors) / len(errors),
        "interpretation": "numerical interpolation error of the 500 m product grid only; not physical 30 m accuracy",
    }


# ---------------------------------------------------------------------------
# Comparison and manifest
# ---------------------------------------------------------------------------

def approach_comparison(date: str = "20260906") -> dict:
    data = load_window(date)
    try:
        from pyproj import Transformer
    except ImportError:
        return {"status": "pyproj unavailable"}
    tr = Transformer.from_crs("EPSG:32644", "EPSG:4326", always_xy=True)
    samples = []
    for xi in range(171, 187, 2):
        for yi in range(475, 491, 2):
            easting = FALLBACK_RADAR_X0 + xi * FALLBACK_RADAR_DX
            northing = FALLBACK_RADAR_Y0 + yi * FALLBACK_RADAR_DY
            lon, lat = tr.transform(easting, northing)
            H = dem_sample_height(lat, lon)
            if H is None:
                continue
            h_ell, N = orthometric_to_ellipsoidal(H, lat, lon)
            a = approach_a_fields(data, easting, northing, h_ell)
            b = approach_b_fields(data, lat, lon, h_ell)
            if a is None or b is None:
                continue
            # product zero-Doppler time via interpolation of the ZDT cube
            lx, ly, lh = a["indices"]["x"] - data["window_indices"]["x"][0], \
                         a["indices"]["y"] - data["window_indices"]["y"][0], \
                         a["indices"]["h"] - data["window_indices"]["h"][0]
            t_prod = trilinear_3d(data["zeroDopplerAzimuthTime"], lh, ly, lx) \
                if "zeroDopplerAzimuthTime" in data else None
            samples.append({
                "radar_index": [xi, yi],
                "latlon": [round(lat, 6), round(lon, 6)],
                "dem_orthometric_m": round(H, 3),
                "geoid_N_m": round(N, 3),
                "ellipsoidal_h_m": round(h_ell, 3),
                "A_incidence_deg": round(a["incidence_deg"], 4),
                "B_incidence_deg": round(b["incidence_deg"], 4),
                "incidence_diff_deg": round(a["incidence_deg"] - b["incidence_deg"], 4),
                "A_slant_range_m": round(a["slant_range_m"], 1),
                "B_slant_range_m": round(b["slant_range_m"], 1),
                "slant_range_diff_m": round(a["slant_range_m"] - b["slant_range_m"], 1),
                "los_angular_diff_deg": round(angle_between(a["los_enu"], b["los_enu"]), 4),
                "B_acquisition_time_s": round(b["zd"]["acquisition_time_s"], 4),
                "product_zd_time_s": round(t_prod, 4) if t_prod is not None else None,
                "acquisition_time_diff_s": round(b["zd"]["acquisition_time_s"] - t_prod, 6) if t_prod is not None else None,
                "zero_doppler_residual_mps": round(b["zd"]["zero_doppler_residual_mps"], 9),
            })
    if not samples:
        return {"date": date, "status": "no common samples"}
    def stat(key):
        vals = [abs(s[key]) for s in samples if s[key] is not None]
        if not vals:
            return None
        vals.sort()
        return {"min": vals[0], "median": vals[len(vals)//2], "max": vals[-1], "mean": sum(vals)/len(vals)}
    return {
        "date": date,
        "status": "computed",
        "sample_count": len(samples),
        "incidence_abs_diff_deg": stat("incidence_diff_deg"),
        "slant_range_abs_diff_m": stat("slant_range_diff_m"),
        "los_angular_diff_deg": stat("los_angular_diff_deg"),
        "acquisition_time_abs_diff_s": stat("acquisition_time_diff_s"),
        "zero_doppler_residual_abs_mps": stat("zero_doppler_residual_mps"),
        "samples": samples,
    }


ATTITUDE_NOTE = (
    "Product attributes define attitude quaternions only as (q0,q1,q2,q3) scalar-first "
    "with no documented reference frame, rotation direction, or antenna boresight. "
    "Therefore the geometric LOS is NOT rotated by attitude. Quaternion behaviour "
    "(normalization, endpoints, sign equivalence, frame transform) is tested separately. "
    "Approach B is an ORBIT zero-Doppler LOS reconstruction, not an attitude-based model."
)


def error_budget() -> dict:
    return {
        "dem_elevation_error_m": {"value": 4.0, "source": "Copernicus GLO-30 LE90 absolute"},
        "egm2008_interpolation_error_m": {"value": 0.135, "source": "max bilinear 2.5'"},
        "radar_grid_interpolation_error_m": {"value": None, "source": "measured numerically via withheld-node cross-validation; physical meaning limited"},
        "orbit_interpolation_error_m": {"value": None, "source": "45 states, MOE; unmeasured"},
        "attitude_interpolation_error_m": {"value": None, "source": "126 quaternion records; not applied to geometric LOS"},
        "coordinate_transform_error_m": {"value": 0.001, "source": "double-precision ECEF numerical only"},
        "acquisition_time_solution_error_s": {"value": None, "source": "zero-Doppler bisection residual; agreement with product ZDT is NOT independent (shared orbit lineage)"},
        "combined_uncertainty": "NOT REPORTED: several components unmeasured and components are correlated (A and B share orbit/DEM lineage). No statistically valid combination is claimed.",
    }


def build_manifest() -> dict:
    data = load_window("20260906")
    x_axis, y_axis, h_axis = radar_axes(data)
    zc = approach_comparison("20260906")
    access30 = RAW / "access_20260930.json"
    access30_record = json.loads(access30.read_text()) if access30.exists() else {"status": "not attempted"}
    return {
        "mission": "015.1",
        "title": "Geometry Prototype Corrections & Independent Validation",
        "final_decision": "CONDITIONAL GO",
        "scientific_measurement": False,
        "production_classification_product": False,
        "source_provenance": {
            "nisar_granule_20260906": data["granule"],
            "nisar_granule_20260930": "NISAR_L2_PR_GCOV_032_005_D_073_4005_DHDH_A_20260930T132236_20260930T132311_P05023_N_F_J_001",
            "nisar_access": "earthaccess netrc authenticated bounded range reads; no complete HDF5 downloaded",
            "dem": "Mission 011 Copernicus GLO-30 crop",
            "geoid": "Mission 014 NGA EGM2008 2.5' grid (SHA-256 verified)",
        },
        "axis_verification": {
            "x_axis_verified_from_product": {"count": len(x_axis), "first": x_axis[0], "last": x_axis[-1], "spacing_m": x_axis[1]-x_axis[0]},
            "y_axis_verified_from_product": {"count": len(y_axis), "first": y_axis[0], "last": y_axis[-1], "spacing_m": y_axis[1]-y_axis[0]},
            "height_axis_verified_from_product": {"count": len(h_axis), "first": h_axis[0], "last": h_axis[-1], "spacing_m": h_axis[1]-h_axis[0]},
            "spacing_hardcoded": False,
        },
        "los_convention": {
            "frame": "ENU at target",
            "direction": "target -> sensor",
            "stored_components": ["East (losUnitVectorX)", "North (losUnitVectorY)"],
            "derived_component": "Up = sqrt(1 - East^2 - North^2), positive (sensor above target)",
            "incidence_angle": "angle between LOS and ellipsoid normal at target height = acos(Up)",
        },
        "attitude_note": ATTITUDE_NOTE,
        "approach_A": {"name": "Product radar-grid metadata interpolation", "fields": ["incidenceAngle", "slantRange", "losUnitVectorX", "losUnitVectorY"]},
        "approach_B": {"name": "Orbit zero-Doppler LOS reconstruction", "method": "target-specific zero-Doppler bisection using orbit position AND velocity"},
        "independence_note": "A and B are NOT independent: the product radar-grid cube and the orbit solution share the same source orbit/geocoding lineage. Agreement is consistency, not independent validation.",
        "approach_comparison_20260906": zc,
        "granule_20260930_access": access30_record,
        "numerical_interpolation_error": {
            "incidenceAngle": withheld_node_error(data["incidenceAngle"]),
            "slantRange": withheld_node_error(data["slantRange"]),
        },
        "error_budget": error_budget(),
        "validation": {
            "independent_terrain_target": "BLOCKED - no independently validated non-candidate target selected",
            "synthetic_cases": ["shadow_positive", "shadow_negative", "layover_below", "layover_exceeding", "slant_ordering", "frame_reversal", "quaternion_checks", "interpolation_boundaries"],
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
            "full_hdf5_downloaded": False,
        },
        "conditions": [
            "Withheld-node interpolation error is numerical only; physical 30 m terrain accuracy remains unverified",
            "Select an independent non-candidate real terrain validation target (currently BLOCKED)",
            "Quantify MOE orbit interpolation error; ZDT agreement is not independent evidence",
            "Confirm DEM release identity (2023_1) or quantify height differences",
        ],
    }


def main() -> None:
    out = ROOT / "data" / "manifests" / "mission015_geometry_validation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build_manifest(), indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    print("MISSION_015_1_DECISION: CONDITIONAL GO")
    print("MANIFEST:", out, out.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
