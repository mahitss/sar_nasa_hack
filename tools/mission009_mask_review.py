"""Mission 009 quality-mask review.

Reads Sentinel-2 scene classification and cloud probability, and can decode
Landsat Collection 2 QA_PIXEL bits. It does not read reflectance, classify
water, or change the Mission 006 screen.
"""

from __future__ import annotations

import hashlib
import json
import math
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "mission009"
DERIVED_DIR = ROOT / "data" / "derived" / "mission009"
MANIFEST_PATH = ROOT / "data" / "manifests" / "mission009_optical_mask_review.json"

DISCOVERY_BBOX = [79.75, 30.03, 79.87, 30.15]
NISAR_20260930 = "2026-09-30T13:22:36Z"
LANDSAT_MAX_BYTES = 25 * 1024 * 1024

# S2-PDGS-CS-DI-PSD, issue 15.1, date 05/12/2025, Table 68.
# Class 6 keeps the specification label. It is not a water validation.
SCL_CLASSES = {
    0: "NO_DATA",
    1: "SATURATED_OR_DEFECTIVE",
    2: "CAST_SHADOWS",
    3: "CLOUD_SHADOWS",
    4: "VEGETATION",
    5: "NOT_VEGETATED",
    6: "WATER",
    7: "UNCLASSIFIED",
    8: "CLOUD_MEDIUM_PROBABILITY",
    9: "CLOUD_HIGH_PROBABILITY",
    10: "THIN_CIRRUS",
    11: "SNOW_OR_ICE",
}
SCL_INVALID = {0, 1}
SCL_CLOUD = {8, 9}
SCL_CIRRUS = {10}
SCL_CLOUD_OR_CIRRUS = SCL_CLOUD | SCL_CIRRUS
SCL_CLOUD_SHADOW = {3}
SCL_CAST_SHADOW = {2}
SCL_SNOW = {11}

# LSDS-1619 version 6.0, Table 6-2. Bit 7 is recorded and is not a water claim.
QA_BITS = {
    "fill": 0,
    "dilated_cloud": 1,
    "cirrus": 2,
    "cloud": 3,
    "cloud_shadow": 4,
    "snow": 5,
    "clear": 6,
    "water": 7,
}
QA_CLOUD_CONFIDENCE = {0: "none", 1: "low", 2: "medium", 3: "high"}
QA_OTHER_CONFIDENCE = {0: "none", 1: "low", 2: "reserved", 3: "high"}

SCL_URL = "https://e84-earth-search-sentinel-data.s3.us-west-2.amazonaws.com/sentinel-2-c1-l2a/44/R/LU/2026/10/S2B_T44RLU_20261002T052420_L2A/SCL.tif"
CLD_URL = "https://e84-earth-search-sentinel-data.s3.us-west-2.amazonaws.com/sentinel-2-c1-l2a/44/R/LU/2026/10/S2B_T44RLU_20261002T052420_L2A/CLD_20m.tif"
QA_URL = "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2026/145/039/LC08_L2SP_145039_20261001_20261009_02_T1/LC08_L2SP_145039_20261001_20261009_02_T1_QA_PIXEL.TIF"
EXPECTED_BYTES = {"SCL.tif": 1869617, "CLD_20m.tif": 1660814}


def percentile(values, percent: float) -> float | None:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * percent / 100
    low = math.floor(rank)
    high = min(low + 1, len(ordered) - 1)
    weight = rank - low
    return ordered[low] * (1 - weight) + ordered[high] * weight


def scl_label(value: int) -> str:
    return SCL_CLASSES.get(int(value), "UNSPECIFIED")


def summarize_scl(values) -> dict:
    counts = {label: 0 for label in SCL_CLASSES.values()}
    unspecified = {}
    total = 0
    for value in values:
        total += 1
        label = scl_label(value)
        if label == "UNSPECIFIED":
            unspecified[str(int(value))] = unspecified.get(str(int(value)), 0) + 1
        else:
            counts[label] += 1
    invalid = counts["NO_DATA"] + counts["SATURATED_OR_DEFECTIVE"]
    cloud = counts["CLOUD_MEDIUM_PROBABILITY"] + counts["CLOUD_HIGH_PROBABILITY"]
    cirrus = counts["THIN_CIRRUS"]
    other = (
        counts["VEGETATION"]
        + counts["NOT_VEGETATED"]
        + counts["WATER"]
        + counts["UNCLASSIFIED"]
        + sum(unspecified.values())
    )

    def percent(count):
        return None if total == 0 else 100 * count / total

    return {
        "pixel_count": total,
        "class_counts": counts,
        "unspecified_counts": unspecified,
        "invalid_nodata_or_defective": invalid,
        "cast_shadow": counts["CAST_SHADOWS"],
        "cloud_shadow": counts["CLOUD_SHADOWS"],
        "cloud": cloud,
        "thin_cirrus": cirrus,
        "cloud_or_cirrus": cloud + cirrus,
        "snow_or_ice": counts["SNOW_OR_ICE"],
        "other_recorded_classes": other,
        "percent_of_window_pixels": {
            "invalid_nodata_or_defective": percent(invalid),
            "cast_shadow": percent(counts["CAST_SHADOWS"]),
            "cloud_shadow": percent(counts["CLOUD_SHADOWS"]),
            "cloud_or_cirrus": percent(cloud + cirrus),
            "snow_or_ice": percent(counts["SNOW_OR_ICE"]),
            "other_recorded_classes": percent(other),
        },
        "water_class_is_validation": False,
    }


def cld_summary(values) -> dict:
    samples = [float(value) for value in values]
    if not samples:
        return {"pixel_count": 0}
    histogram = {}
    for value in samples:
        bin_start = int(math.floor(value / 10) * 10)
        key = f"{bin_start}_{bin_start + 9}"
        histogram[key] = histogram.get(key, 0) + 1
    return {
        "pixel_count": len(samples),
        "minimum": min(samples),
        "maximum": max(samples),
        "median": percentile(samples, 50),
        "percentile_5": percentile(samples, 5),
        "percentile_25": percentile(samples, 25),
        "percentile_75": percentile(samples, 75),
        "percentile_95": percentile(samples, 95),
        "percentile_99": percentile(samples, 99),
        "percentile_method": "inclusive linear rank (n-1)*p/100",
        "histogram_width_10": histogram,
        "numeric_unit": "stored sample value; PSD 15.1 names this a cloud probability map and the retrieved section does not state a percent encoding",
    }


def scl_cld_overlap(scl_values, cld_values) -> dict:
    if len(scl_values) != len(cld_values):
        raise ValueError("SCL and CLD windows differ in length")
    cloud_positive = cloud_zero = other_positive = other_zero = 0
    by_class = {}
    for scl_value, cld_value in zip(scl_values, cld_values):
        label = scl_label(scl_value)
        bucket = by_class.setdefault(label, [])
        bucket.append(float(cld_value))
        cloudy = int(scl_value) in SCL_CLOUD_OR_CIRRUS
        positive = float(cld_value) > 0
        if cloudy and positive:
            cloud_positive += 1
        elif cloudy:
            cloud_zero += 1
        elif positive:
            other_positive += 1
        else:
            other_zero += 1
    return {
        "scl_cloud_or_cirrus_and_cld_above_zero": cloud_positive,
        "scl_cloud_or_cirrus_and_cld_zero": cloud_zero,
        "other_scl_and_cld_above_zero": other_positive,
        "other_scl_and_cld_zero": other_zero,
        "cld_above_zero_is_not_a_tuned_threshold": True,
        "cld_median_by_scl_class": {label: percentile(samples, 50) for label, samples in sorted(by_class.items())},
    }


def decode_qa_pixel(value: int) -> dict:
    pixel = int(value)
    cloud_confidence = (pixel >> 8) & 0b11
    shadow_confidence = (pixel >> 10) & 0b11
    snow_confidence = (pixel >> 12) & 0b11
    cirrus_confidence = (pixel >> 14) & 0b11
    return {
        "fill": bool(pixel & (1 << QA_BITS["fill"])),
        "dilated_cloud": bool(pixel & (1 << QA_BITS["dilated_cloud"])),
        "cirrus": bool(pixel & (1 << QA_BITS["cirrus"])),
        "cloud": bool(pixel & (1 << QA_BITS["cloud"])),
        "cloud_shadow": bool(pixel & (1 << QA_BITS["cloud_shadow"])),
        "snow": bool(pixel & (1 << QA_BITS["snow"])),
        "clear": bool(pixel & (1 << QA_BITS["clear"])),
        "water": bool(pixel & (1 << QA_BITS["water"])),
        "cloud_confidence": QA_CLOUD_CONFIDENCE[cloud_confidence],
        "cloud_shadow_confidence": QA_OTHER_CONFIDENCE[shadow_confidence],
        "snow_confidence": QA_OTHER_CONFIDENCE[snow_confidence],
        "cirrus_confidence": QA_OTHER_CONFIDENCE[cirrus_confidence],
        "water_bit_is_validation": False,
    }


def summarize_qa(values) -> dict:
    total = 0
    fill = 0
    flags = {name: 0 for name in ("dilated_cloud", "cirrus", "cloud", "cloud_shadow", "snow", "clear", "water")}
    union = 0
    not_one_flag_and_not_clear = 0
    confidence = {
        "cloud_confidence": {},
        "cloud_shadow_confidence": {},
        "snow_confidence": {},
        "cirrus_confidence": {},
    }
    for value in values:
        total += 1
        decoded = decode_qa_pixel(value)
        if decoded["fill"]:
            fill += 1
            continue
        for name in flags:
            if decoded[name]:
                flags[name] += 1
        obstructed = decoded["dilated_cloud"] or decoded["cirrus"] or decoded["cloud"] or decoded["cloud_shadow"]
        if obstructed:
            union += 1
        if not obstructed and not decoded["clear"]:
            not_one_flag_and_not_clear += 1
        for key in confidence:
            confidence[key][decoded[key]] = confidence[key].get(decoded[key], 0) + 1
    observed = total - fill

    def percent(count, denominator):
        return None if denominator == 0 else 100 * count / denominator

    return {
        "pixel_count": total,
        "fill": fill,
        "observed": observed,
        "flags_among_observed": flags,
        "cloud_shadow_cirrus_or_dilated_union": union,
        "observed_without_those_flags_and_without_clear_bit": not_one_flag_and_not_clear,
        "clear_bit_count_among_observed": flags["clear"],
        "percent_of_all_pixels": {
            "fill": percent(fill, total),
            "union": percent(union, total),
        },
        "percent_of_observed_pixels": {name: percent(count, observed) for name, count in flags.items()}
        | {"union": percent(union, observed)},
        "confidence_among_observed": confidence,
        "absence_of_one_cloud_flag_is_not_clear": True,
        "water_bit_is_validation": False,
    }


def native_pixel_size(geotransform) -> tuple[float, float]:
    if geotransform[2] != 0 or geotransform[4] != 0:
        raise ValueError("rotated geotransform is not handled")
    return abs(float(geotransform[1])), abs(float(geotransform[5]))


def reject_cross_sensor_resample(size_a: float, size_b: float) -> None:
    if abs(size_a - size_b) > 1e-6:
        raise ValueError("native resolutions differ; resampling is not allowed")


def centers_inside_bbox(geotransform, rows: int, cols: int, west: float, south: float, east: float, north: float):
    selected = []
    for row in range(rows):
        for col in range(cols):
            x = geotransform[0] + (col + 0.5) * geotransform[1] + (row + 0.5) * geotransform[2]
            y = geotransform[3] + (col + 0.5) * geotransform[4] + (row + 0.5) * geotransform[5]
            if west <= x <= east and south <= y <= north:
                selected.append((row, col))
    return selected


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _head(url: str) -> dict:
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return {
                "status": response.status,
                "url": response.geturl(),
                "content_length": response.headers.get("Content-Length"),
                "content_type": response.headers.get("Content-Type"),
                "content_range": response.headers.get("Content-Range"),
                "redirected": response.geturl() != url,
            }
    except Exception as exc:
        return {"status": None, "url": url, "error_type": type(exc).__name__, "error": str(exc)[:300], "redirected": False}


def _download(url: str, path: Path, expected_bytes: int) -> dict:
    request = urllib.request.Request(url)
    with urllib.request.urlopen(request, timeout=120) as response:
        content_type = response.headers.get("Content-Type", "")
        payload = response.read()
        status = response.status
        final_url = response.geturl()
    if len(payload) != expected_bytes:
        raise RuntimeError(f"{path.name} is {len(payload)} bytes, catalogue size is {expected_bytes}")
    if "tiff" not in content_type.lower():
        raise RuntimeError(f"{path.name} content type is {content_type}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {"status": status, "content_type": content_type, "bytes": len(payload), "final_url": final_url, "sha256": _sha256(path)}


def _open_raster(path: Path) -> dict:
    import os
    from osgeo import gdal, osr

    os.environ["GDAL_PAM_ENABLED"] = "NO"
    gdal.SetConfigOption("GDAL_PAM_ENABLED", "NO")
    gdal.UseExceptions()
    dataset = gdal.Open(str(path), gdal.GA_ReadOnly)
    band = dataset.GetRasterBand(1)
    spatial = dataset.GetSpatialRef()
    authority = spatial.GetAuthorityCode(None) if spatial is not None else None
    return {
        "dataset": dataset,
        "width": dataset.RasterXSize,
        "height": dataset.RasterYSize,
        "geotransform": tuple(dataset.GetGeoTransform()),
        "crs": f"EPSG:{authority}" if authority else None,
        "data_type": gdal.GetDataTypeName(band.DataType),
        "nodata": band.GetNoDataValue(),
        "osr": osr,
        "gdal": gdal,
    }


def _projected_ring(osr_module, source_crs: str):
    source = osr_module.SpatialReference()
    source.ImportFromEPSG(4326)
    source.SetAxisMappingStrategy(osr_module.OAMS_TRADITIONAL_GIS_ORDER)
    target = osr_module.SpatialReference()
    target.SetFromUserInput(source_crs)
    target.SetAxisMappingStrategy(osr_module.OAMS_TRADITIONAL_GIS_ORDER)
    transform = osr_module.CoordinateTransformation(source, target)
    west, south, east, north = DISCOVERY_BBOX
    steps = 32
    ring = []
    for index in range(steps):
        ring.append((west + (east - west) * index / steps, north))
    for index in range(steps):
        ring.append((east, north + (south - north) * index / steps))
    for index in range(steps):
        ring.append((east + (west - east) * index / steps, south))
    for index in range(steps):
        ring.append((west, south + (north - south) * index / steps))
    ring.append(ring[0])
    return [transform.TransformPoint(lon, lat)[:2] for lon, lat in ring]


def _point_in_ring(x: float, y: float, ring) -> bool:
    inside = False
    previous = len(ring) - 1
    for index, (xi, yi) in enumerate(ring):
        xj, yj = ring[previous]
        if (yi > y) != (yj > y):
            crossing = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < crossing:
                inside = not inside
        previous = index
    return inside


def _window_values(raster: dict):
    import numpy as np

    geotransform = raster["geotransform"]
    native_pixel_size(geotransform)
    ring = _projected_ring(raster["osr"], raster["crs"])
    columns = []
    rows = []
    for x, y in ring:
        columns.append((x - geotransform[0]) / geotransform[1])
        rows.append((y - geotransform[3]) / geotransform[5])
    row0 = max(0, math.floor(min(rows)))
    row1 = min(raster["height"], math.ceil(max(rows)))
    col0 = max(0, math.floor(min(columns)))
    col1 = min(raster["width"], math.ceil(max(columns)))
    array = raster["dataset"].GetRasterBand(1).ReadAsArray(col0, row0, col1 - col0, row1 - row0)
    selected = []
    for row in range(array.shape[0]):
        for col in range(array.shape[1]):
            x = geotransform[0] + (col0 + col + 0.5) * geotransform[1]
            y = geotransform[3] + (row0 + row + 0.5) * geotransform[5]
            if _point_in_ring(x, y, ring):
                selected.append(array[row, col])
    corners_inside = all(0 <= (x - geotransform[0]) / geotransform[1] <= raster["width"] and 0 <= (y - geotransform[3]) / geotransform[5] <= raster["height"] for x, y in ring[::32])
    pixel_width, pixel_height = native_pixel_size(geotransform)
    return {
        "values": np.asarray(selected),
        "read_window": {"row_off": row0, "rows": row1 - row0, "col_off": col0, "cols": col1 - col0},
        "corners_inside_raster": corners_inside,
        "pixel_width_m": pixel_width,
        "pixel_height_m": pixel_height,
        "selected_pixel_footprint_m2": len(selected) * pixel_width * pixel_height,
    }


def _raster_record(path: Path) -> dict:
    raster = _open_raster(path)
    window = _window_values(raster)
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
        "width": raster["width"],
        "height": raster["height"],
        "crs": raster["crs"],
        "geotransform": list(raster["geotransform"]),
        "data_type": raster["data_type"],
        "nodata": raster["nodata"],
        "window": {key: value for key, value in window.items() if key != "values"},
        "values": window["values"],
    }


def landsat_access_decision(head: dict) -> dict:
    length = head.get("content_length")
    response_bytes = int(length) if length not in (None, "") else None
    content_type = (head.get("content_type") or "").lower()
    tiff = "tiff" in content_type and not head.get("redirected")
    size = response_bytes if tiff else None
    reasons = []
    if head.get("error"):
        reasons.append(head["error"])
    if head.get("redirected"):
        reasons.append("the response left the LandsatLook object URL")
    if "tiff" not in content_type:
        reasons.append("the response is not a TIFF")
    if size is None:
        reasons.append("QA_PIXEL object size is unknown")
    elif size > LANDSAT_MAX_BYTES:
        reasons.append("object size exceeds 25 MB")
    return {
        "download": tiff and size is not None and size <= LANDSAT_MAX_BYTES,
        "qa_pixel_size_bytes": size,
        "response_body_bytes": None if tiff else response_bytes,
        "reasons": reasons,
        "head": head,
    }


def build_manifest(sentinel: dict, landsat: dict, timestamp: str) -> dict:
    return {
        "mission": "009",
        "review_timestamp_utc": timestamp,
        "discovery_window": {"crs": "EPSG:4326", "bbox": DISCOVERY_BBOX, "role": "catalogue discovery window, not a lake boundary"},
        "same_date_ground_truth": False,
        "reflectance_downloaded": False,
        "water_classified": False,
        "area_calculated": False,
        "shoreline_calculated": False,
        "mission006_thresholds_changed": False,
        "candidate_patches_projected": False,
        "sentinel2": sentinel,
        "landsat": landsat,
        "specifications": {
            "sentinel2_scl": "S2-PDGS-CS-DI-PSD issue 15.1, 05/12/2025, Table 68",
            "sentinel2_cld": "S2-PDGS-CS-DI-PSD issue 15.1, section 3.13.3.3, MSK_CLDPRB cloud probability map",
            "landsat_qa_pixel": "LSDS-1619 version 6.0, Table 6-2",
        },
    }


def main() -> None:
    import sys

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    scl_path = RAW_DIR / "SCL.tif"
    cld_path = RAW_DIR / "CLD_20m.tif"
    scl_download = _download(SCL_URL, scl_path, EXPECTED_BYTES["SCL.tif"])
    cld_download = _download(CLD_URL, cld_path, EXPECTED_BYTES["CLD_20m.tif"])
    scl = _raster_record(scl_path)
    cld = _raster_record(cld_path)
    reject_cross_sensor_resample(scl["window"]["pixel_width_m"], cld["window"]["pixel_width_m"])
    if scl["values"].shape != cld["values"].shape:
        raise RuntimeError("SCL and CLD discovery-window samples differ")
    scl_stats = summarize_scl(scl["values"].tolist())
    cld_stats = cld_summary(cld["values"].tolist())
    overlap = scl_cld_overlap(scl["values"].tolist(), cld["values"].tolist())
    sentinel = {
        "product": "S2B_MSIL2A_20261002T051649_N0513_R062_T44RLU_20261002T091142",
        "item_id": "S2B_T44RLU_20261002T052420_L2A",
        "collection": "sentinel-2-c1-l2a",
        "processing_level": "L2A",
        "processing_baseline": "05.13",
        "acquisition_datetime_utc": "2026-10-02T05:30:31.932000Z",
        "hours_after_nisar_20260930": (datetime.fromisoformat("2026-10-02T05:30:31.932000+00:00") - datetime.fromisoformat("2026-09-30T13:22:36+00:00")).total_seconds() / 3600,
        "downloads": {
            "SCL.tif": {**scl_download, "url": SCL_URL, "catalogue_bytes": EXPECTED_BYTES["SCL.tif"]},
            "CLD_20m.tif": {**cld_download, "url": CLD_URL, "catalogue_bytes": EXPECTED_BYTES["CLD_20m.tif"]},
        },
        "grids": {
            "SCL.tif": {key: scl[key] for key in ("path", "sha256", "bytes", "width", "height", "crs", "geotransform", "data_type", "nodata", "window")},
            "CLD_20m.tif": {key: cld[key] for key in ("path", "sha256", "bytes", "width", "height", "crs", "geotransform", "data_type", "nodata", "window")},
        },
        "scl": scl_stats,
        "cld": cld_stats,
        "overlap": overlap,
        "mask_coverage_m2_is_not_water_area": True,
    }
    head = _head(QA_URL)
    decision = landsat_access_decision(head)
    landsat = {
        "product": "LC08_L2SP_145039_20261001_20261009_02_T1_SR",
        "collection": "landsat-c2l2-sr",
        "acquisition_datetime_utc": "2026-10-01T05:12:17.380114Z",
        "hours_after_nisar_20260930": (datetime.fromisoformat("2026-10-01T05:12:17.380114+00:00") - datetime.fromisoformat("2026-09-30T13:22:36+00:00")).total_seconds() / 3600,
        "qa_pixel_url": QA_URL,
        "downloaded": False,
        "access_decision": decision,
        "statistics": None,
    }
    manifest = build_manifest(sentinel, landsat, timestamp)
    manifest["software"] = {"python": sys.version.split()[0]}
    try:
        from osgeo import gdal

        manifest["software"]["gdal"] = gdal.__version__
    except Exception:
        pass
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("SCL_PIXELS", scl_stats["pixel_count"])
    print("CLOUD_OR_CIRRUS_PERCENT", scl_stats["percent_of_window_pixels"]["cloud_or_cirrus"])
    print("LANDSAT_DOWNLOAD", decision["download"])
    print("LANDSAT_REASONS", "; ".join(decision["reasons"]))


if __name__ == "__main__":
    main()
