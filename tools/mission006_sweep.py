"""Mission 006 sweep of the preregistered water-candidate domain.

The count algebra and the four-connected patch rule are tested against
``water_candidate.sensitivity``. This script does not compute area, a
shoreline, or a two-date change class.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CROP_DIR = ROOT / "data" / "processed" / "mission003"
DERIVED_DIR = ROOT / "data" / "derived" / "mission006"
MANIFEST_PATH = ROOT / "data" / "manifests" / "mission006_sweep_manifest.json"

HH_DB = tuple(range(-22, -9))
HV_DB = tuple(range(-28, -14))
MIN_LOOKS = (0.0, 2.0)
PATCH_SIZES = (1, 4, 9)
TOTAL_SETS = len(HH_DB) * len(HV_DB) * len(MIN_LOOKS) * len(PATCH_SIZES)

DATES = ("20260906", "20260930")
LAYERS = ("HHHH", "HVHV", "numberOfLooks", "mask")

GRANULES = {
    "20260906_gcov": "NISAR_L2_PR_GCOV_030_005_D_073_4005_DHDH_A_20260906T132236_20260906T132311_P05023_N_F_J_001",
    "20260930_gcov": "NISAR_L2_PR_GCOV_032_005_D_073_4005_DHDH_A_20260930T132236_20260930T132311_P05023_N_F_J_001",
}

EXPECTED_GRID = {
    "crs": "EPSG:32644",
    "width": 1171,
    "height": 1343,
    "geotransform": (379470.0, 10.0, 0.0, 3336070.0, 0.0, -10.0),
}

COUNT_PERCENTILES = (0.1, 1, 5, 10, 25, 50, 75, 90, 95, 99, 99.9)

VALIDITY_CODES = {
    "1": "valid in every parameter set",
    "0": "valid in some but not all parameter sets",
    "-1": "invalid in every parameter set",
}
STABILITY_CODES = {
    "2": "fully sweep-stable: valid in every set and a candidate in every set",
    "1": "candidate in every set in which valid, but not valid in every set",
    "0": "parameter-sensitive: candidate in some but not all valid sets",
    "-1": "never a candidate while valid",
    "-2": "invalid in every parameter set",
}


def db_to_linear(decibels: float) -> float:
    return 10.0 ** (decibels / 10.0)


def parameter_domain() -> list[dict]:
    """Ordered domain. HH, then HV, then looks, then patch size."""

    domain = []
    for hh_db in HH_DB:
        for hv_db in HV_DB:
            for min_looks in MIN_LOOKS:
                for patch in PATCH_SIZES:
                    domain.append(
                        {
                            "hh_db": hh_db,
                            "hh_max_linear": db_to_linear(hh_db),
                            "hv_db": hv_db,
                            "hv_max_linear": db_to_linear(hv_db),
                            "min_looks": min_looks,
                            "min_patch_pixels": patch,
                            "max_hv_over_hh": None,
                        }
                    )
    if len(domain) != 1092:
        raise RuntimeError(f"domain length {len(domain)} is not 1092")
    return domain


def domain_digest(domain: list[dict] | None = None) -> str:
    payload = domain if domain is not None else parameter_domain()
    canonical = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percentile(sorted_values, percent: float) -> float | None:
    """Inclusive linear percentile. Rank is (n - 1) * percent / 100."""

    if len(sorted_values) == 0:
        return None
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    rank = (len(sorted_values) - 1) * (percent / 100.0)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return float(sorted_values[low])
    weight = rank - low
    return float(sorted_values[low] * (1.0 - weight) + sorted_values[high] * weight)


def stability_code(valid_count: int, candidate_count: int, total_sets: int) -> int:
    """Combined stability code. Full stability requires validity in every set."""

    if valid_count == 0:
        return -2
    if candidate_count == 0:
        return -1
    if candidate_count == valid_count and valid_count == total_sets:
        return 2
    if candidate_count == valid_count:
        return 1
    return 0


def validity_code(valid_count: int, total_sets: int) -> int:
    if valid_count == total_sets:
        return 1
    if valid_count == 0:
        return -1
    return 0


def keep_large_components(raw, min_pixels: int):
    """Drop 4-connected True components smaller than ``min_pixels``.

    Components touch on edges only. A diagonal contact stays disconnected.
    ``min_pixels`` of 1 leaves the mask unchanged.
    """

    import numpy as np

    if min_pixels <= 1:
        return raw
    rows, cols = raw.shape
    labels = np.zeros((rows, cols), dtype=np.int32)
    parent = [0]
    rank = [0]

    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root == right_root:
            return
        if rank[left_root] < rank[right_root]:
            parent[left_root] = right_root
        elif rank[left_root] > rank[right_root]:
            parent[right_root] = left_root
        else:
            parent[right_root] = left_root
            rank[left_root] += 1

    next_id = 1
    previous: list[tuple[int, int, int]] = []
    for row_index in range(rows):
        row = raw[row_index]
        if not bool(row.any()):
            previous = []
            continue
        padded = np.empty(cols + 2, dtype=np.int8)
        padded[0] = 0
        padded[-1] = 0
        padded[1:-1] = row
        changes = np.diff(padded)
        starts = np.flatnonzero(changes == 1)
        ends = np.flatnonzero(changes == -1)
        runs: list[tuple[int, int, int]] = []
        previous_pos = 0
        for start, end in zip(starts.tolist(), ends.tolist()):
            parent.append(next_id)
            rank.append(0)
            labels[row_index, start:end] = next_id
            while previous_pos < len(previous) and previous[previous_pos][1] <= start:
                previous_pos += 1
            scan = previous_pos
            while scan < len(previous) and previous[scan][0] < end:
                union(next_id, previous[scan][2])
                scan += 1
            runs.append((start, end, next_id))
            next_id += 1
        previous = runs
    if next_id == 1:
        return np.zeros(raw.shape, dtype=bool)
    remap = np.empty(next_id, dtype=np.int32)
    remap[0] = 0
    for label in range(1, next_id):
        remap[label] = find(label)
    rooted = remap[labels]
    sizes = np.bincount(rooted.ravel())
    small = sizes < min_pixels
    small[0] = False
    kept = raw.copy()
    kept[small[rooted]] = False
    return kept


def sweep_counts(hhhh, hvhv, looks, mask, hh_limits, hv_limits, min_looks_values, patch_sizes):
    """Return valid, raw-candidate, and filtered-candidate counts.

    ``hh_limits`` and ``hv_limits`` must be strictly increasing. The ratio gate
    is not applied. Counts follow ``water_candidate.sensitivity`` when the
    looks rule rejects non-positive looks.
    """

    import numpy as np

    hh_limits = np.asarray(hh_limits, dtype=np.float64)
    hv_limits = np.asarray(hv_limits, dtype=np.float64)
    if hh_limits.size == 0 or hv_limits.size == 0 or len(min_looks_values) == 0 or len(patch_sizes) == 0:
        raise ValueError("the sweep domain is empty")
    if np.any(np.diff(hh_limits) <= 0) or np.any(np.diff(hv_limits) <= 0):
        raise ValueError("power limits must be strictly increasing")
    hh = np.asarray(hhhh, dtype=np.float64)
    hv = np.asarray(hvhv, dtype=np.float64)
    look = np.asarray(looks, dtype=np.float64)
    codes = np.asarray(mask)
    base = (
        (codes > 0)
        & (codes != 255)
        & np.isfinite(hh)
        & np.isfinite(hv)
        & (hh > 0)
        & (hv > 0)
        & np.isfinite(look)
        & (look > 0)
    )
    valid_count = np.zeros(hh.shape, dtype=np.int16)
    raw_count = np.zeros(hh.shape, dtype=np.int16)
    filtered_count = np.zeros(hh.shape, dtype=np.int16)
    sets_per_floor = int(hh_limits.size * hv_limits.size * len(patch_sizes))
    for floor in min_looks_values:
        valid = base & (look >= float(floor))
        valid_count += valid.astype(np.int16) * sets_per_floor
        hh_pass = np.zeros(hh.shape, dtype=np.int16)
        hv_pass = np.zeros(hh.shape, dtype=np.int16)
        if np.any(valid):
            hh_pass[valid] = hh_limits.size - np.searchsorted(hh_limits, hh[valid], side="left")
            hv_pass[valid] = hv_limits.size - np.searchsorted(hv_limits, hv[valid], side="left")
        raw_count += (hh_pass.astype(np.int32) * hv_pass.astype(np.int32) * len(patch_sizes)).astype(np.int16)
        for hh_limit in hh_limits:
            hh_ok = valid & (hh <= hh_limit)
            for hv_limit in hv_limits:
                raw = hh_ok & (hv <= hv_limit)
                for patch in patch_sizes:
                    if patch <= 1:
                        filtered_count += raw.astype(np.int16)
                    else:
                        filtered_count += keep_large_components(raw, int(patch)).astype(np.int16)
    if np.any(raw_count > valid_count) or np.any(filtered_count > raw_count):
        raise RuntimeError("candidate counts exceeded validity or raw counts")
    return valid_count, raw_count, filtered_count


def _stability_grid(valid_count, candidate_count, total_sets: int):
    import numpy as np

    valid = np.asarray(valid_count)
    candidate = np.asarray(candidate_count)
    coded = np.full(valid.shape, -2, dtype=np.int16)
    eligible = valid > 0
    coded[eligible & (candidate == 0)] = -1
    coded[eligible & (candidate > 0) & (candidate < valid)] = 0
    coded[eligible & (candidate == valid) & (valid < total_sets)] = 1
    coded[(valid == total_sets) & (candidate == total_sets)] = 2
    return coded


def class_rasters(valid_count, raw_count, filtered_count, total_sets: int):
    import numpy as np

    valid = np.asarray(valid_count)
    validity = np.full(valid.shape, 0, dtype=np.int16)
    validity[valid == total_sets] = 1
    validity[valid == 0] = -1
    return (
        validity,
        _stability_grid(valid, raw_count, total_sets),
        _stability_grid(valid, filtered_count, total_sets),
    )


def summarize_counts(valid_count, raw_count, filtered_count, total_sets: int) -> dict:
    import numpy as np

    valid = np.asarray(valid_count)
    raw = np.asarray(raw_count)
    filtered = np.asarray(filtered_count)
    eligible = valid > 0

    def distribution(values) -> dict:
        sample = np.sort(values.astype(np.float64))
        return {
            "count": int(sample.size),
            "minimum": None if sample.size == 0 else float(sample[0]),
            "maximum": None if sample.size == 0 else float(sample[-1]),
            "median": percentile(sample, 50),
            "percentiles": {str(item): percentile(sample, item) for item in COUNT_PERCENTILES},
        }

    fully_raw = int(np.count_nonzero((valid == total_sets) & (raw == total_sets)))
    fully_filtered = int(np.count_nonzero((valid == total_sets) & (filtered == total_sets)))
    return {
        "total_pixels": int(valid.size),
        "pixels_valid_in_all_sets": int(np.count_nonzero(valid == total_sets)),
        "pixels_valid_in_some_sets": int(np.count_nonzero((valid > 0) & (valid < total_sets))),
        "pixels_invalid_in_every_set": int(np.count_nonzero(valid == 0)),
        "fully_sweep_stable_raw_candidate_count": fully_raw,
        "fully_sweep_stable_filtered_candidate_count": fully_filtered,
        "raw_parameter_sensitive_count": int(np.count_nonzero(eligible & (raw > 0) & (raw < valid))),
        "filtered_parameter_sensitive_count": int(np.count_nonzero(eligible & (filtered > 0) & (filtered < valid))),
        "raw_never_selected_while_valid_count": int(np.count_nonzero(eligible & (raw == 0))),
        "filtered_never_selected_while_valid_count": int(np.count_nonzero(eligible & (filtered == 0))),
        "pixels_with_any_component_removal": int(np.count_nonzero(raw > filtered)),
        "selection_events_removed_by_component_filter": int(np.sum(raw.astype(np.int64) - filtered.astype(np.int64))),
        "raw_candidate_count_distribution_over_valid_pixels": distribution(raw[eligible]),
        "filtered_candidate_count_distribution_over_valid_pixels": distribution(filtered[eligible]),
        "confirmed_water_extent": False,
        "area_calculated": False,
        "shoreline_calculated": False,
    }


def _recorded_checksums(manifest_path: Path) -> dict[str, str]:
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


def verify_sources() -> list[dict]:
    recorded = _recorded_checksums(ROOT / "data" / "manifests" / "mission003_raster_qc.json")
    mission005 = _recorded_checksums(ROOT / "data" / "manifests" / "mission005_distribution_audit.json")
    recorded.update(mission005)
    checks = []
    for date in DATES:
        for layer in LAYERS:
            relative = f"data/processed/mission003/{date}_gcov_frequencyA_{layer}.tif"
            path = ROOT / relative
            digest = sha256(path)
            expected = recorded.get(relative)
            checks.append(
                {
                    "path": relative,
                    "bytes": path.stat().st_size,
                    "sha256": digest,
                    "recorded_sha256": expected,
                    "matches_record": digest == expected,
                }
            )
    if any(not item["matches_record"] for item in checks):
        raise SystemExit("CHECKSUM_MISMATCH")
    return checks


def read_crop(path: Path) -> dict:
    os.environ["GDAL_PAM_ENABLED"] = "NO"
    from osgeo import gdal

    gdal.SetConfigOption("GDAL_PAM_ENABLED", "NO")
    gdal.UseExceptions()
    dataset = gdal.Open(str(path), gdal.GA_ReadOnly)
    if dataset is None:
        raise RuntimeError(f"could not open {path.name}")
    band = dataset.GetRasterBand(1)
    spatial = dataset.GetSpatialRef()
    authority = spatial.GetAuthorityCode(None) if spatial is not None else None
    return {
        "width": dataset.RasterXSize,
        "height": dataset.RasterYSize,
        "geotransform": tuple(dataset.GetGeoTransform()),
        "projection": dataset.GetProjection(),
        "crs": f"EPSG:{authority}" if authority else None,
        "data_type": gdal.GetDataTypeName(band.DataType),
        "values": band.ReadAsArray(),
        "gdal_release": gdal.VersionInfo("RELEASE_NAME"),
    }


def _grid_ok(grid: dict) -> bool:
    return (
        grid["crs"] == EXPECTED_GRID["crs"]
        and grid["width"] == EXPECTED_GRID["width"]
        and grid["height"] == EXPECTED_GRID["height"]
        and tuple(grid["geotransform"]) == EXPECTED_GRID["geotransform"]
    )


def write_raster(path: Path, values, geotransform, projection: str, description: str, metadata: dict) -> dict:
    os.environ["GDAL_PAM_ENABLED"] = "NO"
    from osgeo import gdal

    gdal.SetConfigOption("GDAL_PAM_ENABLED", "NO")
    gdal.UseExceptions()
    driver = gdal.GetDriverByName("GTiff")
    path.parent.mkdir(parents=True, exist_ok=True)
    dataset = driver.Create(
        str(path),
        values.shape[1],
        values.shape[0],
        1,
        gdal.GDT_Int16,
        options=["COMPRESS=DEFLATE", "PREDICTOR=2", "TILED=YES"],
    )
    dataset.SetGeoTransform(tuple(geotransform))
    dataset.SetProjection(projection)
    band = dataset.GetRasterBand(1)
    band.SetDescription(description)
    for key, value in metadata.items():
        band.SetMetadataItem(key, value)
    band.WriteArray(values)
    band.FlushCache()
    dataset.FlushCache()
    dataset = None
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "width": int(values.shape[1]),
        "height": int(values.shape[0]),
        "data_type": "Int16",
        "sha256": sha256(path),
        "description": description,
    }


def run_date(date: str, arrays: dict) -> dict:
    import numpy as np

    started = time.perf_counter()
    tracemalloc.start()
    hh_limits = [db_to_linear(item) for item in HH_DB]
    hv_limits = [db_to_linear(item) for item in HV_DB]
    valid, raw, filtered = sweep_counts(
        arrays["HHHH"],
        arrays["HVHV"],
        arrays["numberOfLooks"],
        arrays["mask"],
        hh_limits,
        hv_limits,
        MIN_LOOKS,
        PATCH_SIZES,
    )
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    elapsed = time.perf_counter() - started
    validity, raw_stability, filtered_stability = class_rasters(valid, raw, filtered, TOTAL_SETS)
    stats = summarize_counts(valid, raw, filtered, TOTAL_SETS)
    stats["parameter_sets_executed"] = TOTAL_SETS
    stats["runtime_seconds"] = elapsed
    stats["tracemalloc_peak_bytes"] = int(peak)
    products = {
        "valid_count": valid,
        "raw_candidate_count": raw,
        "filtered_candidate_count": filtered,
        "validity_class": validity,
        "raw_candidate_stability": raw_stability,
        "filtered_candidate_stability": filtered_stability,
    }
    if int(valid.max()) > TOTAL_SETS or int(raw.max()) > TOTAL_SETS or int(filtered.max()) > TOTAL_SETS:
        raise RuntimeError("a count exceeded 1092")
    stats["maximum_valid_count"] = int(valid.max())
    stats["maximum_raw_candidate_count"] = int(raw.max())
    stats["maximum_filtered_candidate_count"] = int(filtered.max())
    return {"statistics": stats, "products": products, "numpy": np.__version__}


def main() -> None:
    before = verify_sources()
    opened = {}
    for date in DATES:
        opened[date] = {layer: read_crop(CROP_DIR / f"{date}_gcov_frequencyA_{layer}.tif") for layer in LAYERS}
    reference = opened[DATES[0]]["HHHH"]
    if any(not _grid_ok(opened[date][layer]) for date in DATES for layer in LAYERS):
        raise SystemExit("GRID_MISMATCH")
    if any(opened[date][layer]["geotransform"] != reference["geotransform"] for date in DATES for layer in LAYERS):
        raise SystemExit("GRID_MISMATCH")
    import numpy as np

    preflight = {}
    for date in DATES:
        mask = opened[date]["mask"]["values"]
        valid = (mask > 0) & (mask != 255)
        hh = opened[date]["HHHH"]["values"]
        hv = opened[date]["HVHV"]["values"]
        looks = opened[date]["numberOfLooks"]["values"]
        codes, counts = np.unique(mask, return_counts=True)
        preflight[date] = {
            "mask_value_counts": {str(int(code)): int(count) for code, count in zip(codes, counts)},
            "valid_samples": int(valid.sum()),
            "valid_nonpositive_or_nonfinite_power": int(
                np.count_nonzero(valid & (~(np.isfinite(hh) & np.isfinite(hv) & (hh > 0) & (hv > 0))))
            ),
            "valid_nonpositive_or_nonfinite_looks": int(
                np.count_nonzero(valid & (~(np.isfinite(looks) & (looks > 0))))
            ),
            "data_types": {layer: opened[date][layer]["data_type"] for layer in LAYERS},
        }
        unexpected = [int(code) for code in codes if int(code) < 0 or int(code) > 255]
        if unexpected or preflight[date]["valid_nonpositive_or_nonfinite_power"]:
            raise SystemExit("PREFLIGHT_FAILED")
    domain = parameter_domain()
    results = {}
    output_records = []
    descriptions = {
        "valid_count": "Count of parameter sets in which the pixel is valid. Not a water extent.",
        "raw_candidate_count": "Count of parameter sets in which the pixel is a raw candidate before patch filtering.",
        "filtered_candidate_count": "Count of parameter sets in which the pixel remains a candidate after four-connected patch filtering.",
        "validity_class": "Validity class across the 1092-set domain.",
        "raw_candidate_stability": "Raw-candidate stability. Code 2 is fully sweep-stable.",
        "filtered_candidate_stability": "Filtered-candidate stability. Code 2 is fully sweep-stable.",
    }
    for date in DATES:
        arrays = {layer: opened[date][layer]["values"] for layer in LAYERS}
        result = run_date(date, arrays)
        results[date] = result["statistics"]
        projection = opened[date]["HHHH"]["projection"]
        transform = opened[date]["HHHH"]["geotransform"]
        for name, values in result["products"].items():
            metadata = {
                "mission": "006",
                "candidate_not_confirmed_water": "true",
                "parameter_sets": str(TOTAL_SETS),
                "ratio_gate": "off",
            }
            if name == "validity_class":
                metadata["class_codes"] = json.dumps(VALIDITY_CODES)
            if "stability" in name:
                metadata["class_codes"] = json.dumps(STABILITY_CODES)
            record = write_raster(
                DERIVED_DIR / f"{date}_{name}.tif",
                values,
                transform,
                projection,
                descriptions[name],
                metadata,
            )
            record["date"] = date
            record["product"] = name
            output_records.append(record)
    after = verify_sources()
    manifest = {
        "mission": "006",
        "audit_timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "real_data_classification": True,
        "confirmed_water_extent": False,
        "area_calculated": False,
        "shoreline_calculated": False,
        "two_date_change_analysis": False,
        "gslc_resampled": False,
        "gslc_used_as_gcov_mask": False,
        "ratio_gate": "off",
        "parameter_set_count": TOTAL_SETS,
        "parameter_domain_digest_sha256": domain_digest(domain),
        "parameter_domain": domain,
        "parameter_order": "HH dB ascending, HV dB ascending, min_looks 0 then 2, patch size 1 then 4 then 9",
        "software": {
            "python": platform.python_version(),
            "numpy": results and __import__("numpy").__version__,
            "gdal": opened[DATES[0]]["HHHH"]["gdal_release"],
            "algorithm": "water_candidate.sensitivity semantics via mission006_sweep.sweep_counts",
            "looks_rule": "finite and strictly greater than zero, and greater than or equal to min_looks",
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
            "granules": GRANULES,
        },
        "source_grid": {
            "crs": EXPECTED_GRID["crs"],
            "width": EXPECTED_GRID["width"],
            "height": EXPECTED_GRID["height"],
            "geotransform": list(EXPECTED_GRID["geotransform"]),
            "posting_m": 10,
        },
        "source_checksums_before": before,
        "source_checksums_after": after,
        "preflight": preflight,
        "dates": results,
        "outputs": output_records,
        "class_semantics": {"validity": VALIDITY_CODES, "stability": STABILITY_CODES},
        "limitations": [
            "Outputs are algorithmic candidates, not confirmed water.",
            "No lake area, shoreline, or polygon was calculated.",
            "The two dates were not compared.",
            "Smooth wet soil can pass the screen.",
            "Radar shadow and layover can pass the screen.",
            "Wind-roughened water can fail the screen.",
            "Vegetation and debris can obscure water.",
            "Incidence geometry is not used.",
            "No terrain-shadow model is available.",
            "P05023 provisional calibration is unresolved.",
            "Filename code N and orbitType MOE remain unresolved.",
            "The ratio gate is off.",
            "The sensitivity sweep is not a confidence score.",
            "numberOfLooks is not a confidence or accuracy score.",
            "Two dates cannot separate moisture change from shoreline movement.",
        ],
    }
    text = json.dumps(manifest, indent=2, ensure_ascii=False)
    MANIFEST_PATH.write_text(text + "\n", encoding="utf-8")
    print("PARAMETER_SETS", TOTAL_SETS)
    print("DOMAIN_DIGEST", manifest["parameter_domain_digest_sha256"])
    for date, stats in results.items():
        print(
            date,
            "stable_filtered",
            stats["fully_sweep_stable_filtered_candidate_count"],
            "seconds",
            round(stats["runtime_seconds"], 3),
        )
    print("MANIFEST", MANIFEST_PATH)


if __name__ == "__main__":
    main()
