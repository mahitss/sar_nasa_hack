"""Distribution audit for the Mission 003 GCOV crops.

This module summarises existing rasters. It does not classify water, resample
the GSLC mask, or modify source files.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
PERCENTILES = (0.1, 1, 5, 10, 25, 50, 75, 90, 95, 99, 99.9)

GCOV_LAYERS = ("HHHH", "HVHV", "numberOfLooks", "mask")
DATES = ("20260906", "20260930")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percentile(sorted_values: Sequence[float], percent: float) -> float | None:
    """Inclusive linear percentile. Rank is (n - 1) * percent / 100."""

    if not sorted_values:
        return None
    if not 0 <= percent <= 100:
        raise ValueError("percent must be between 0 and 100")
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    rank = (len(sorted_values) - 1) * (percent / 100.0)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return float(sorted_values[low])
    weight = rank - low
    return float(sorted_values[low] * (1.0 - weight) + sorted_values[high] * weight)


def population_std(values: Sequence[float], mean: float) -> float | None:
    count = len(values)
    if count == 0:
        return None
    return math.sqrt(sum((value - mean) ** 2 for value in values) / count)


def summarize(values: Iterable[float]) -> dict:
    """Summarise a finite sample. The caller decides which pixels qualify."""

    sample = [float(value) for value in values]
    sample.sort()
    count = len(sample)
    if count == 0:
        return {
            "count": 0,
            "minimum": None,
            "maximum": None,
            "mean": None,
            "population_std": None,
            "percentiles": {str(item): None for item in PERCENTILES},
        }
    total = math.fsum(sample)
    mean = total / count
    return {
        "count": count,
        "minimum": sample[0],
        "maximum": sample[-1],
        "mean": mean,
        "population_std": population_std(sample, mean),
        "percentiles": {str(item): percentile(sample, item) for item in PERCENTILES},
    }


def db_histogram(values: Sequence[float], width: float = 2.0) -> list[dict]:
    """Histogram 10*log10(value) for finite positive powers."""

    if width <= 0:
        raise ValueError("histogram width must be positive")
    decibels = [10.0 * math.log10(value) for value in values if math.isfinite(value) and value > 0]
    if not decibels:
        return []
    lowest = math.floor(min(decibels) / width) * width
    highest = math.ceil(max(decibels) / width) * width
    if highest == lowest:
        highest += width
    bins = []
    edge = lowest
    while edge < highest - 1e-9:
        bins.append({"lower_db": edge, "upper_db": edge + width, "count": 0})
        edge += width
    for value in decibels:
        index = int((value - lowest) / width)
        if index == len(bins):
            index -= 1
        bins[index]["count"] += 1
    return bins


def log10_histogram(values: Sequence[float], width: float = 1.0) -> list[dict]:
    """Histogram log10(linear power) in declared-width bins."""

    if width <= 0:
        raise ValueError("histogram width must be positive")
    logs = [math.log10(value) for value in values if math.isfinite(value) and value > 0]
    if not logs:
        return []
    lowest = math.floor(min(logs) / width) * width
    highest = math.ceil(max(logs) / width) * width
    if highest == lowest:
        highest += width
    bins = []
    edge = lowest
    while edge < highest - 1e-12:
        bins.append({"lower_log10": edge, "upper_log10": edge + width, "count": 0})
        edge += width
    for value in logs:
        index = int((value - lowest) / width)
        if index == len(bins):
            index -= 1
        bins[index]["count"] += 1
    return bins


def mask_frequencies(codes: Iterable[int]) -> dict[str, int]:
    counts = Counter(int(code) for code in codes)
    return {str(code): counts[code] for code in sorted(counts)}


def is_valid_subswath(code: int) -> bool:
    return code > 0 and code != 255


def axis_means(rows: Sequence[Sequence[float]], valid: Sequence[Sequence[bool]]) -> list[float | None]:
    means: list[float | None] = []
    for row_values, row_valid in zip(rows, valid):
        selected = [float(value) for value, keep in zip(row_values, row_valid) if keep and math.isfinite(value)]
        means.append(math.fsum(selected) / len(selected) if selected else None)
    return means


def axis_db_means(rows: Sequence[Sequence[float]], valid: Sequence[Sequence[bool]]) -> list[float | None]:
    """Mean of per-pixel 10*log10(power) along one axis. Already in dB."""

    means: list[float | None] = []
    for row_values, row_valid in zip(rows, valid):
        selected = [
            10.0 * math.log10(float(value))
            for value, keep in zip(row_values, row_valid)
            if keep and math.isfinite(value) and value > 0
        ]
        means.append(math.fsum(selected) / len(selected) if selected else None)
    return means


def adjacent_steps(means: Sequence[float | None], as_db: bool) -> dict:
    """Differences between successive finite axis means.

    Power means are converted with 10*log10 before subtraction. A missing mean
    breaks the step rather than being treated as zero.
    """

    steps = []
    largest = None
    for index in range(len(means) - 1):
        left = means[index]
        right = means[index + 1]
        if left is None or right is None or left <= 0 or right <= 0:
            continue
        if as_db:
            delta = 10.0 * math.log10(right) - 10.0 * math.log10(left)
        else:
            delta = right - left
        steps.append(delta)
        if largest is None or abs(delta) > abs(largest["delta"]):
            largest = {"index": index, "delta": delta}
    return {
        "step_count": len(steps),
        "largest_absolute_step": largest,
        "maximum_step": max(steps) if steps else None,
        "minimum_step": min(steps) if steps else None,
        "definition": (
            "10*log10 of successive linear means"
            if as_db
            else "difference of successive means in native units"
        ),
    }


def adjacent_differences(means: Sequence[float | None]) -> dict:
    """Subtract successive values that are already in the reported unit."""

    steps = []
    largest = None
    for index in range(len(means) - 1):
        left = means[index]
        right = means[index + 1]
        if left is None or right is None:
            continue
        delta = right - left
        steps.append(delta)
        if largest is None or abs(delta) > abs(largest["delta"]):
            largest = {"index": index, "delta": delta}
    return {
        "step_count": len(steps),
        "largest_absolute_step": largest,
        "maximum_step": max(steps) if steps else None,
        "minimum_step": min(steps) if steps else None,
        "definition": "difference of successive means; values are already in dB",
    }


def transpose(rows: Sequence[Sequence[float]]) -> list[list[float]]:
    return [list(column) for column in zip(*rows)]


def high_tail_bbox(rows: Sequence[Sequence[float]], threshold: float) -> dict:
    selected = []
    height = len(rows)
    width = len(rows[0]) if rows else 0
    for row_index, row in enumerate(rows):
        for col_index, value in enumerate(row):
            if math.isfinite(value) and value >= threshold:
                selected.append((row_index, col_index, float(value)))
    if not selected:
        return {"count": 0}
    rows_hit = [item[0] for item in selected]
    cols_hit = [item[1] for item in selected]
    row_span = max(rows_hit) - min(rows_hit) + 1
    col_span = max(cols_hit) - min(cols_hit) + 1
    return {
        "count": len(selected),
        "threshold": threshold,
        "row_min": min(rows_hit),
        "row_max": max(rows_hit),
        "col_min": min(cols_hit),
        "col_max": max(cols_hit),
        "bbox_pixel_area": row_span * col_span,
        "raster_pixel_area": height * width,
        "compact_relative_to_raster": (row_span * col_span) < 0.05 * height * width and len(selected) > 10,
    }


def neighborhood_summary(rows: Sequence[Sequence[float]], row: int, col: int, radius: int = 2) -> dict:
    values = []
    for y_coord in range(row - radius, row + radius + 1):
        for x_coord in range(col - radius, col + radius + 1):
            if 0 <= y_coord < len(rows) and 0 <= x_coord < len(rows[0]):
                value = rows[y_coord][x_coord]
                if math.isfinite(value):
                    values.append(float(value))
    return {
        "center_row": row,
        "center_col": col,
        "center_value": float(rows[row][col]),
        "finite_count": len(values),
        "minimum": min(values) if values else None,
        "maximum": max(values) if values else None,
    }


def layer_audit(values: list[list[float]], mask: list[list[int]], kind: str) -> dict:
    height = len(values)
    width = len(values[0])
    flat_mask = [code for row in mask for code in row]
    finite = []
    positive = []
    valid_positive = []
    valid_finite = []
    nodata = 0
    valid_mask = 0
    for row_values, row_mask in zip(values, mask):
        for value, code in zip(row_values, row_mask):
            if is_valid_subswath(code):
                valid_mask += 1
            if not math.isfinite(value):
                nodata += 1
                continue
            finite.append(float(value))
            if is_valid_subswath(code):
                valid_finite.append(float(value))
            if value > 0:
                positive.append(float(value))
                if is_valid_subswath(code):
                    valid_positive.append(float(value))
    summary = summarize(valid_positive if kind == "power" else valid_finite)
    db_values = [10.0 * math.log10(value) for value in valid_positive] if kind == "power" else []
    valid_flags = []
    for row_values, row_mask in zip(values, mask):
        flags = []
        for value, code in zip(row_values, row_mask):
            if kind == "power":
                flags.append(is_valid_subswath(code) and math.isfinite(value) and value > 0)
            else:
                flags.append(is_valid_subswath(code) and math.isfinite(value))
        valid_flags.append(flags)
    row_profile = axis_means(values, valid_flags)
    column_profile = axis_means(transpose(values), transpose(valid_flags))
    result = {
        "total_pixel_count": height * width,
        "finite_count": len(finite),
        "nodata_count": nodata,
        "valid_gcov_mask_count": valid_mask,
        "positive_finite_count": len(positive),
        "valid_positive_finite_count": len(valid_positive),
        "all_finite": summarize(finite),
        "analysis_sample": summary,
        "analysis_sample_definition": (
            "valid GCOV subswath and positive finite power"
            if kind == "power"
            else "valid GCOV subswath and finite numberOfLooks"
        ),
        "mask_value_counts": mask_frequencies(flat_mask),
        "unexpected_mask_codes": [
            code for code in mask_frequencies(flat_mask) if int(code) < 0 or int(code) > 255
        ],
        "row_mean_profile_summary": adjacent_steps(row_profile, as_db=kind == "power"),
        "column_mean_profile_summary": adjacent_steps(column_profile, as_db=kind == "power"),
        "row_mean_profile": row_profile,
        "column_mean_profile": column_profile,
    }
    if kind == "power":
        row_db = axis_db_means(values, valid_flags)
        column_db = axis_db_means(transpose(values), transpose(valid_flags))
        result["db_of_analysis_percentiles"] = {
            key: None if value is None else 10.0 * math.log10(value)
            for key, value in summary["percentiles"].items()
        }
        result["linear_log10_histogram"] = log10_histogram(valid_positive)
        result["db_histogram_2db"] = db_histogram(valid_positive)
        result["db_sample"] = summarize(db_values)
        result["row_db_mean_profile"] = row_db
        result["column_db_mean_profile"] = column_db
        result["row_db_mean_profile_summary"] = adjacent_differences(row_db)
        result["column_db_mean_profile_summary"] = adjacent_differences(column_db)
        result["profile_definitions"] = {
            "linear_mean_then_db_step": "mean of valid linear power, then 10*log10 of successive means",
            "mean_of_pixel_db": "mean of per-pixel 10*log10(power); steps are ordinary differences",
        }
        if summary["maximum"] is not None:
            result["high_tail_99_9"] = high_tail_bbox(values, summary["percentiles"]["99.9"])
            extremes = []
            for row_index, row in enumerate(values):
                for col_index, value in enumerate(row):
                    if math.isfinite(value) and value >= 10000:
                        extremes.append(neighborhood_summary(values, row_index, col_index))
            result["values_at_or_above_10000"] = {
                "count": len(extremes),
                "neighborhoods": extremes,
                "label": "location summary only; no physical class is assigned",
            }
    else:
        result["interpretation"] = "numberOfLooks distribution. Not a confidence or accuracy score."
    result["invalid_sample_bbox"] = _invalid_bbox(values, mask, kind)
    return result


def _invalid_bbox(values: list[list[float]], mask: list[list[int]], kind: str) -> dict:
    rows_hit = []
    cols_hit = []
    for row_index, (row_values, row_mask) in enumerate(zip(values, mask)):
        for col_index, (value, code) in enumerate(zip(row_values, row_mask)):
            invalid = not is_valid_subswath(code) or not math.isfinite(value)
            if kind == "power" and is_valid_subswath(code) and math.isfinite(value) and value <= 0:
                invalid = True
            if invalid:
                rows_hit.append(row_index)
                cols_hit.append(col_index)
    if not rows_hit:
        return {"count": 0}
    return {
        "count": len(rows_hit),
        "row_min": min(rows_hit),
        "row_max": max(rows_hit),
        "col_min": min(cols_hit),
        "col_max": max(cols_hit),
        "rows_with_any": len(set(rows_hit)),
        "columns_with_any": len(set(cols_hit)),
    }


def recorded_checksums(manifest_path: Path) -> dict[str, str]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    found: dict[str, str] = {}

    def walk(node):
        if isinstance(node, dict):
            path = node.get("path")
            digest = node.get("sha256")
            if isinstance(path, str) and isinstance(digest, str) and path.endswith(".tif"):
                found[path.replace("\\", "/")] = digest
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(payload)
    return found


def read_geotiff(path: Path) -> dict:
    """Read one GeoTIFF without writing a statistics sidecar."""

    os.environ["GDAL_PAM_ENABLED"] = "NO"
    from osgeo import gdal

    gdal.SetConfigOption("GDAL_PAM_ENABLED", "NO")
    gdal.UseExceptions()
    dataset = gdal.Open(str(path), gdal.GA_ReadOnly)
    if dataset is None:
        raise RuntimeError(f"could not open {path.name}")
    band = dataset.GetRasterBand(1)
    array = band.ReadAsArray()
    spatial = dataset.GetSpatialRef()
    authority = spatial.GetAuthorityCode(None) if spatial is not None else None
    nodata = band.GetNoDataValue()
    if nodata is not None and not math.isfinite(nodata):
        nodata = None
    release = gdal.VersionInfo("RELEASE_NAME")
    if not str(release).startswith("3."):
        raise RuntimeError(f"unexpected GDAL release {release}")
    return {
        "width": dataset.RasterXSize,
        "height": dataset.RasterYSize,
        "geotransform": list(dataset.GetGeoTransform()),
        "crs": f"EPSG:{authority}" if authority else None,
        "data_type": gdal.GetDataTypeName(band.DataType),
        "nodata": nodata,
        "values": array.tolist(),
        "gdal_version": gdal.__version__,
        "gdal_release": release,
    }


def verify_checksum(relative_path: str, recorded: dict[str, str]) -> dict:
    path = ROOT / relative_path
    if not path.is_file():
        return {"path": relative_path, "present": False, "matches_record": False}
    digest = sha256(path)
    expected = recorded.get(relative_path)
    return {
        "path": relative_path,
        "present": True,
        "bytes": path.stat().st_size,
        "sha256": digest,
        "recorded_sha256": expected,
        "matches_record": digest == expected,
    }


def _relative(name: str) -> str:
    return "data/processed/mission003/{}".format(name)


def build_audit() -> dict:
    raster_checksums = recorded_checksums(ROOT / "data" / "manifests" / "mission003_raster_qc.json")
    gslc_checksums = recorded_checksums(ROOT / "data" / "manifests" / "mission003_gslc_mask_qc.json")
    recorded = {**raster_checksums, **gslc_checksums}
    names = [
        "{}_gcov_frequencyA_{}.tif".format(date, layer)
        for date in DATES
        for layer in GCOV_LAYERS
    ] + ["{}_gslc_mask.tif".format(date) for date in DATES]
    checks = [verify_checksum(_relative(name), recorded) for name in names]
    if any(not item["matches_record"] for item in checks):
        raise SystemExit("CHECKSUM_MISMATCH")
    opened = {name: read_geotiff(ROOT / _relative(name)) for name in names}
    after = [verify_checksum(_relative(name), recorded) for name in names]
    if any(not item["matches_record"] for item in after):
        raise SystemExit("SOURCE_CHANGED_DURING_READ")
    gcov_grids = []
    for date in DATES:
        for layer in GCOV_LAYERS:
            grid = opened["{}_gcov_frequencyA_{}.tif".format(date, layer)]
            gcov_grids.append(
                {
                    "date": date,
                    "layer": layer,
                    "crs": grid["crs"],
                    "width": grid["width"],
                    "height": grid["height"],
                    "geotransform": grid["geotransform"],
                    "pixel_width_m": grid["geotransform"][1],
                    "pixel_height_m": grid["geotransform"][5],
                    "data_type": grid["data_type"],
                    "nodata": grid["nodata"],
                }
            )
    reference = gcov_grids[0]
    gcov_match = all(
        item["crs"] == reference["crs"]
        and item["width"] == reference["width"]
        and item["height"] == reference["height"]
        and item["geotransform"] == reference["geotransform"]
        for item in gcov_grids
    )
    layers = {}
    for date in DATES:
        mask = opened["{}_gcov_frequencyA_mask.tif".format(date)]["values"]
        for layer, kind in (("HHHH", "power"), ("HVHV", "power"), ("numberOfLooks", "looks")):
            values = opened["{}_gcov_frequencyA_{}.tif".format(date, layer)]["values"]
            layers["{}_{}".format(date, layer)] = layer_audit(values, mask, kind)
        mask_codes = [code for row in mask for code in row]
        layers["{}_gcov_mask".format(date)] = {
            "value_counts": mask_frequencies(mask_codes),
            "unexpected_mask_codes": [
                code for code in mask_frequencies(mask_codes) if int(code) < 0 or int(code) > 255
            ],
            "valid_subswath_count": sum(is_valid_subswath(code) for code in mask_codes),
            "interpretation": "Valid-samples subswath mask. Codes are not water or terrain classes.",
        }
        gslc = opened["{}_gslc_mask.tif".format(date)]
        gslc_codes = [code for row in gslc["values"] for code in row]
        layers["{}_gslc_mask".format(date)] = {
            "crs": gslc["crs"],
            "width": gslc["width"],
            "height": gslc["height"],
            "geotransform": gslc["geotransform"],
            "pixel_width_m": gslc["geotransform"][1],
            "pixel_height_m": gslc["geotransform"][5],
            "data_type": gslc["data_type"],
            "nodata": gslc["nodata"],
            "value_counts": mask_frequencies(gslc_codes),
            "applied_to_gcov": False,
            "resampled": False,
            "interpretation": "Native 5 m valid-samples subswath mask. Not applied to GCOV pixels.",
        }
    return {
        "mission": "005",
        "scientific_measurement": False,
        "real_data_classification": False,
        "audit_timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "software": {
            "python": platform.python_version(),
            "gdal": next(iter(opened.values()))["gdal_release"],
            "gdal_python_binding": next(iter(opened.values()))["gdal_version"],
            "percentile_method": "inclusive linear rank (n-1)*p/100",
            "standard_deviation": "population divisor n",
            "db_transform": "10*log10(positive linear power)",
            "histogram_db_width": 2,
            "histogram_log10_width": 1,
            "gdal_pam": "disabled",
        },
        "provenance": {
            "crid": "P05023",
            "group": "D40",
            "track": 5,
            "frame": 73,
            "orbit_direction": "DESCENDING",
            "frequency_a_bandwidth_mhz": 40,
            "polarizations": "HH+HV",
            "filename_fidelity_code": "N",
            "internal_orbit_type": "MOE",
            "orbit_discrepancy": "unresolved",
            "granules": {
                "20260906_gcov": "NISAR_L2_PR_GCOV_030_005_D_073_4005_DHDH_A_20260906T132236_20260906T132311_P05023_N_F_J_001",
                "20260930_gcov": "NISAR_L2_PR_GCOV_032_005_D_073_4005_DHDH_A_20260930T132236_20260930T132311_P05023_N_F_J_001",
                "20260906_gslc": "NISAR_L2_PR_GSLC_030_005_D_073_4005_DHDH_A_20260906T132236_20260906T132311_P05023_N_F_J_002",
                "20260930_gslc": "NISAR_L2_PR_GSLC_032_005_D_073_4005_DHDH_A_20260930T132236_20260930T132311_P05023_N_F_J_001",
            },
        },
        "checksums": checks,
        "checksums_after_read": after,
        "gcov_grid_comparable": gcov_match,
        "gcov_grids": gcov_grids,
        "layers": layers,
        "limitations": [
            "No real-data candidate classification was run.",
            "The GSLC masks were not resampled and were not applied to GCOV pixels.",
            "numberOfLooks is not a confidence score.",
            "Mask codes are not water or terrain classes.",
            "High-tail geometry is not a physical label.",
            "Filename code N and orbitType MOE remain unresolved.",
            "A linear-mean profile step in dB is not the same quantity as a mean of per-pixel dB.",
        ],
    }


def main() -> None:
    payload = build_audit()
    canonical = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    payload["output_sha256"] = {
        "algorithm": "sha256",
        "scope": "UTF-8 json.dumps of this object before output_sha256 was added, indent 2, sort_keys true",
        "sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }
    destination = ROOT / "data" / "manifests" / "mission005_distribution_audit.json"
    destination.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("AUDIT_BYTES {}".format(destination.stat().st_size))
    print("GCOV_GRID_COMPARABLE {}".format(payload["gcov_grid_comparable"]))
    print("OUTPUT_SHA256 {}".format(payload["output_sha256"]["sha256"]))


if __name__ == "__main__":
    main()
