"""Human-review inventory of Mission 006 candidate counts.

This module checks stored rasters and groups pixels that already carry a
review class. It does not rerun the screen, change thresholds, or estimate area.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MISSION006_MANIFEST = ROOT / "data" / "manifests" / "mission006_sweep_manifest.json"
REVIEW_MANIFEST = ROOT / "data" / "manifests" / "mission007_review_manifest.json"

EXPECTED_GRID = {
    "crs": "EPSG:32644",
    "width": 1171,
    "height": 1343,
    "geotransform": (379470.0, 10.0, 0.0, 3336070.0, 0.0, -10.0),
}
TOTAL_SETS = 1092

REVIEW_DECISIONS = (
    "accept_unresolved_water_candidate",
    "reject_likely_non_water_or_confounder",
    "request_independent_evidence",
    "unresolved_insufficient_evidence",
)

EVIDENCE_FIELDS = (
    "provider",
    "dataset",
    "acquisition_date",
    "spatial_coverage",
    "resolution_or_posting",
    "processing_level",
    "access",
    "overlaps_candidate_region",
    "overlaps_acquisition_dates",
    "limitations",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percentile(sorted_values, percent: float) -> float | None:
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


def count_relationships(valid, raw, filtered) -> list[str]:
    """Return problems. An empty list means the stored counts are consistent."""

    problems = []
    if any(len(row) != len(valid[0]) for grid in (raw, filtered) for row in grid):
        return ["array shapes differ"]
    for row_index, valid_row in enumerate(valid):
        for col_index, valid_count in enumerate(valid_row):
            raw_count = raw[row_index][col_index]
            filtered_count = filtered[row_index][col_index]
            if raw_count > valid_count or filtered_count > valid_count:
                problems.append(f"candidate count exceeds valid_count at {row_index},{col_index}")
            if filtered_count > raw_count:
                problems.append(f"filtered count exceeds raw count at {row_index},{col_index}")
            if valid_count > TOTAL_SETS or raw_count > TOTAL_SETS or filtered_count > TOTAL_SETS:
                problems.append(f"count exceeds 1092 at {row_index},{col_index}")
            if problems:
                return problems
    return problems


def connected_components(flags) -> list[list[tuple[int, int]]]:
    """Four-connected components. Diagonal pixels stay separate."""

    rows = len(flags)
    cols = len(flags[0]) if rows else 0
    seen = [[False for _ in range(cols)] for _ in range(rows)]
    components = []
    for row_index in range(rows):
        for col_index in range(cols):
            if not flags[row_index][col_index] or seen[row_index][col_index]:
                continue
            stack = [(row_index, col_index)]
            seen[row_index][col_index] = True
            component = []
            while stack:
                y_coord, x_coord = stack.pop()
                component.append((y_coord, x_coord))
                for y_step, x_step in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    next_y = y_coord + y_step
                    next_x = x_coord + x_step
                    if (
                        0 <= next_y < rows
                        and 0 <= next_x < cols
                        and flags[next_y][next_x]
                        and not seen[next_y][next_x]
                    ):
                        seen[next_y][next_x] = True
                        stack.append((next_y, next_x))
            components.append(component)
    return components


def _median(values: list[int]) -> float | None:
    ordered = sorted(values)
    return percentile(ordered, 50)


def _bounds(pixels: list[tuple[int, int]]) -> dict:
    rows = [item[0] for item in pixels]
    cols = [item[1] for item in pixels]
    return {
        "row_min": min(rows),
        "row_max": max(rows),
        "col_min": min(cols),
        "col_max": max(cols),
    }


def _touches_boundary(pixels: list[tuple[int, int]], height: int, width: int) -> bool:
    return any(row in (0, height - 1) or col in (0, width - 1) for row, col in pixels)


def _touches_invalid(pixels: list[tuple[int, int]], validity) -> bool:
    height = len(validity)
    width = len(validity[0])
    members = set(pixels)
    for row, col in pixels:
        for y_step, x_step in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            next_y = row + y_step
            next_x = col + x_step
            if not (0 <= next_y < height and 0 <= next_x < width):
                continue
            if (next_y, next_x) in members:
                continue
            if validity[next_y][next_x] == -1:
                return True
    return False


def component_record(
    identifier: str,
    date: str,
    candidate_class: str,
    pixels: list[tuple[int, int]],
    raw_counts,
    filtered_counts,
    validity,
) -> dict:
    raw_values = [int(raw_counts[row][col]) for row, col in pixels]
    filtered_values = [int(filtered_counts[row][col]) for row, col in pixels]
    height = len(validity)
    width = len(validity[0])
    return {
        "id": identifier,
        "date": date,
        "pixel_bounds": _bounds(pixels),
        "pixel_count": len(pixels),
        "candidate_class": candidate_class,
        "selection_count_summary": {
            "raw_minimum": min(raw_values),
            "raw_maximum": max(raw_values),
            "raw_median": _median(raw_values),
            "filtered_minimum": min(filtered_values),
            "filtered_maximum": max(filtered_values),
            "filtered_median": _median(filtered_values),
        },
        "touches_invalid_pixels": _touches_invalid(pixels, validity),
        "touches_raster_boundary": _touches_boundary(pixels, height, width),
        "coordinate_frame": "crop row and column, origin at the upper left",
        "georeferencing": "not independently surveyed; product geotransform was checked only for internal consistency",
        "limitations": [
            "This patch is an algorithmic candidate group, not a lake.",
            "No area or shoreline is defined.",
            "The Mission 005 parameter domain was not changed.",
        ],
    }


def inventory_regions(date: str, raw_stability, filtered_stability, raw_counts, filtered_counts, validity) -> list[dict]:
    """List four-connected review patches from stored classes only."""

    classes = (
        ("raw_fully_sweep_stable", raw_stability, 2),
        ("filtered_fully_sweep_stable", filtered_stability, 2),
        ("filtered_candidate_in_every_valid_set_but_partially_valid", filtered_stability, 1),
    )
    records = []
    for class_name, grid, code in classes:
        flags = [[value == code for value in row] for row in grid]
        components = connected_components(flags)
        components.sort(key=lambda item: (_bounds(item)["row_min"], _bounds(item)["col_min"], len(item)))
        for index, pixels in enumerate(components, start=1):
            records.append(
                component_record(
                    f"R007-{date}-{class_name}-{index:03d}",
                    date,
                    class_name,
                    pixels,
                    raw_counts,
                    filtered_counts,
                    validity,
                )
            )
    return records


def parameter_sensitive_summary(filtered_stability) -> dict:
    flags = [[value == 0 for value in row] for row in filtered_stability]
    components = connected_components(flags)
    sizes = sorted(len(item) for item in components)
    return {
        "candidate_class": "filtered_parameter_sensitive",
        "component_count": len(components),
        "pixel_count": sum(sizes),
        "largest_component_pixels": sizes[-1] if sizes else 0,
        "component_size_median": _median(sizes) if sizes else None,
        "listed_as_review_patches": False,
        "reason": "The class is widespread. Listing every component would treat a parameter-sensitive field as a set of lakes.",
    }


def review_record(region_id: str, decision: str, note: str) -> dict:
    if decision not in REVIEW_DECISIONS:
        raise ValueError(f"unsupported review decision: {decision}")
    return {
        "region_id": region_id,
        "decision": decision,
        "note": note,
        "confirmed_water": False,
        "area_estimated": False,
        "shoreline_estimated": False,
    }


def validate_evidence(record: dict) -> list[str]:
    missing = [field for field in EVIDENCE_FIELDS if field not in record or record[field] in ("", None)]
    problems = [f"missing {field}" for field in missing]
    if record.get("used_to_retune_thresholds") is True:
        problems.append("evidence must not retune the Mission 005 domain")
    return problems


def published_statistics(valid, raw, filtered, raw_stability, filtered_stability) -> dict:
    total = len(valid) * len(valid[0])
    valid_all = valid_some = invalid = 0
    raw_stable = filtered_stable = 0
    raw_sensitive = filtered_sensitive = 0
    raw_never = filtered_never = 0
    for row_index, valid_row in enumerate(valid):
        for col_index, valid_count in enumerate(valid_row):
            raw_count = raw[row_index][col_index]
            filtered_count = filtered[row_index][col_index]
            if valid_count == TOTAL_SETS:
                valid_all += 1
            elif valid_count == 0:
                invalid += 1
            else:
                valid_some += 1
            if valid_count == TOTAL_SETS and raw_count == TOTAL_SETS:
                raw_stable += 1
            if valid_count == TOTAL_SETS and filtered_count == TOTAL_SETS:
                filtered_stable += 1
            if valid_count > 0 and 0 < raw_count < valid_count:
                raw_sensitive += 1
            if valid_count > 0 and 0 < filtered_count < valid_count:
                filtered_sensitive += 1
            if valid_count > 0 and raw_count == 0:
                raw_never += 1
            if valid_count > 0 and filtered_count == 0:
                filtered_never += 1
    return {
        "total_pixels": total,
        "pixels_valid_in_all_sets": valid_all,
        "pixels_valid_in_some_sets": valid_some,
        "pixels_invalid_in_every_set": invalid,
        "fully_sweep_stable_raw_candidate_count": raw_stable,
        "fully_sweep_stable_filtered_candidate_count": filtered_stable,
        "raw_parameter_sensitive_count": raw_sensitive,
        "filtered_parameter_sensitive_count": filtered_sensitive,
        "raw_never_selected_while_valid_count": raw_never,
        "filtered_never_selected_while_valid_count": filtered_never,
        "filtered_stability_code_2_pixels": sum(value == 2 for row in filtered_stability for value in row),
        "raw_stability_code_2_pixels": sum(value == 2 for row in raw_stability for value in row),
    }


def compare_statistics(observed: dict, recorded: dict) -> list[str]:
    problems = []
    for key, value in observed.items():
        if key in ("filtered_stability_code_2_pixels", "raw_stability_code_2_pixels"):
            continue
        if key not in recorded:
            problems.append(f"manifest lacks {key}")
        elif recorded[key] != value:
            problems.append(f"{key} raster {value} manifest {recorded[key]}")
    if observed["fully_sweep_stable_filtered_candidate_count"] != 0:
        problems.append("a fully sweep-stable filtered candidate is present")
    if observed["filtered_stability_code_2_pixels"] != 0:
        problems.append("filtered stability code 2 is present")
    if observed["raw_stability_code_2_pixels"] != observed["fully_sweep_stable_raw_candidate_count"]:
        problems.append("raw stability code 2 does not match the full-stability count")
    return problems


def _lists(array) -> list[list[int]]:
    return [[int(value) for value in row] for row in array]


def load_mission006_raster(path: Path) -> dict:
    import os
    from osgeo import gdal

    os.environ["GDAL_PAM_ENABLED"] = "NO"
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
        "crs": f"EPSG:{authority}" if authority else None,
        "data_type": gdal.GetDataTypeName(band.DataType),
        "description": band.GetDescription(),
        "metadata": band.GetMetadata() or {},
        "values": band.ReadAsArray(),
    }


def verify_outputs(manifest: dict) -> tuple[list[dict], list[str]]:
    checks = []
    problems = []
    loaded = {}
    for record in manifest["outputs"]:
        path = ROOT / record["path"]
        digest = sha256(path)
        grid = load_mission006_raster(path)
        item = {
            "path": record["path"],
            "sha256": digest,
            "matches_manifest_sha256": digest == record["sha256"],
            "width": grid["width"],
            "height": grid["height"],
            "crs": grid["crs"],
            "geotransform": list(grid["geotransform"]),
            "data_type": grid["data_type"],
            "description": grid["description"],
        }
        checks.append(item)
        if digest != record["sha256"]:
            problems.append(f"checksum mismatch {record['path']}")
        if grid["width"] != EXPECTED_GRID["width"] or grid["height"] != EXPECTED_GRID["height"]:
            problems.append(f"shape mismatch {record['path']}")
        if grid["crs"] != EXPECTED_GRID["crs"] or grid["geotransform"] != EXPECTED_GRID["geotransform"]:
            problems.append(f"grid mismatch {record['path']}")
        if grid["data_type"] != "Int16":
            problems.append(f"data type mismatch {record['path']}")
        if not grid["description"]:
            problems.append(f"missing description {record['path']}")
        loaded.setdefault(record["date"], {})[record["product"]] = _lists(grid["values"])
    for date, layers in loaded.items():
        relation_problems = count_relationships(
            layers["valid_count"],
            layers["raw_candidate_count"],
            layers["filtered_candidate_count"],
        )
        problems.extend(f"{date} {item}" for item in relation_problems)
        observed = published_statistics(
            layers["valid_count"],
            layers["raw_candidate_count"],
            layers["filtered_candidate_count"],
            layers["raw_candidate_stability"],
            layers["filtered_candidate_stability"],
        )
        problems.extend(f"{date} {item}" for item in compare_statistics(observed, manifest["dates"][date]))
    return checks, problems


EVIDENCE = [
    {
        "provider": "Springer Nature, Discover Geoscience",
        "dataset": "Ghoke and colleagues, Reactivation dynamics of the Kuwari landslide, DOI 10.1007/s44288-026-00717-w",
        "acquisition_date": "optical and Sentinel-1 analysis from 2013 through 2025; article published 2026-09-05",
        "spatial_coverage": "Kuwari landslide on the Shambhu River, Kapkot, Bageshwar. The article states a landslide extent near 30.084–30.087 N and 79.79–79.80 E.",
        "resolution_or_posting": "Resourcesat-2/2A LISS-IV, three Sentinel-2 scenes, one Cartosat-3 scene, and Sentinel-1 SBAS; CartoDEM 10 m and SRTM 30 m are cited as model inputs",
        "processing_level": "published interpretation and a HEC-RAS scenario, not a RIVET measurement",
        "access": "https://doi.org/10.1007/s44288-026-00717-w",
        "overlaps_candidate_region": "historical overlap with the same valley; not a pixel match to the Mission 006 crops",
        "overlaps_acquisition_dates": "no; the optical series ends in 2025 and does not include 2026-09-06 or 2026-09-30",
        "limitations": "Lake lengths reported in that paper are prior results. They are not an area for these candidate pixels and were not used to choose thresholds.",
        "used_to_retune_thresholds": False,
    },
    {
        "provider": "Journal of the Geological Society of India",
        "dataset": "Bisht and colleagues, Kuwari Lake, 2022, DOI 10.1007/s12594-022-1927-3",
        "acquisition_date": "2022 note; observations begin years earlier",
        "spatial_coverage": "Kuwari landslide-dammed lake, Bageshwar",
        "resolution_or_posting": "short geological communication; no new raster was retrieved",
        "processing_level": "published note",
        "access": "https://doi.org/10.1007/s12594-022-1927-3",
        "overlaps_candidate_region": "same valley, historical",
        "overlaps_acquisition_dates": "no",
        "limitations": "It cannot confirm or reject a September 2026 candidate pixel.",
        "used_to_retune_thresholds": False,
    },
    {
        "provider": "South Asia Network on Dams, Rivers and People",
        "dataset": "SANDRP Kunwari landslide-dam note, 22 November 2024",
        "acquisition_date": "narrative covering May 2022 through November 2024",
        "spatial_coverage": "secondary coordinate 30.088337 N, 79.808685 E",
        "resolution_or_posting": "article, not a survey",
        "processing_level": "secondary report",
        "access": "https://sandrp.in/2024/11/22/uttarakhand-kunwari-potentially-dangerous-for-landslides-dam-in-pindar-valley/",
        "overlaps_candidate_region": "the coordinate is the study point already used for catalogue selection; it is not a surveyed patch corner",
        "overlaps_acquisition_dates": "no",
        "limitations": "A secondary article is not independent pixel evidence.",
        "used_to_retune_thresholds": False,
    },
    {
        "provider": "Copernicus / ESA",
        "dataset": "Sentinel-2 MSI L2A",
        "acquisition_date": "a scene-level query for 2026-09-06 and 2026-09-30 was not run",
        "spatial_coverage": "global 110 km tiles; the tile covering the study point was not confirmed in this mission",
        "resolution_or_posting": "10 m visible and near-infrared bands, 20 m and 60 m for other bands",
        "processing_level": "L2A surface reflectance when a scene is retrieved",
        "access": "https://dataspace.copernicus.eu/",
        "overlaps_candidate_region": "unknown until a catalogue query",
        "overlaps_acquisition_dates": "unknown; global acquisition plans include September 2026, which does not prove a cloud-free scene over Kuwari",
        "limitations": "One L2A tile is commonly several hundred megabytes to about a gigabyte. It was not downloaded. No tile identifier is claimed.",
        "used_to_retune_thresholds": False,
    },
    {
        "provider": "USGS",
        "dataset": "Landsat 8/9 Collection 2 Level-2",
        "acquisition_date": "a path/row and scene query for the two NISAR dates was not run",
        "spatial_coverage": "WRS-2 scene; the path and row for 79.81 E, 30.09 N were not resolved here",
        "resolution_or_posting": "30 m optical and thermal",
        "processing_level": "Collection 2 Level-2",
        "access": "https://doi.org/10.5066/P9OGBGM6",
        "overlaps_candidate_region": "unknown until a catalogue query",
        "overlaps_acquisition_dates": "unknown",
        "limitations": "A 30 m pixel is coarser than the 10 m GCOV posting. No scene was downloaded.",
        "used_to_retune_thresholds": False,
    },
    {
        "provider": "Copernicus DEM",
        "dataset": "GLO-30 Public digital surface model, 2021 release",
        "acquisition_date": "static composite; not an observation on 2026-09-06 or 2026-09-30",
        "spatial_coverage": "global where the public 30 m tiles have been released; India tile release was not checked file by file",
        "resolution_or_posting": "30 m",
        "processing_level": "DSM, including vegetation and structures where present",
        "access": "https://registry.opendata.aws/copernicus-dem/",
        "overlaps_candidate_region": "a 30 m crop of the diagnostic window would be a few hundred pixels on a side, on the order of a few megabytes, and was not downloaded",
        "overlaps_acquisition_dates": "no; a DEM is not dated to the NISAR acquisitions",
        "limitations": "A DSM can support a later shadow and layover test. It does not by itself identify water, and it was not used to edit the candidate counts.",
        "used_to_retune_thresholds": False,
    },
]


def build_review(evidence: list[dict] | None = None) -> dict:
    if evidence is None:
        evidence = EVIDENCE
    manifest = json.loads(MISSION006_MANIFEST.read_text(encoding="utf-8"))
    checks, problems = verify_outputs(manifest)
    if problems:
        return {
            "mission": "007",
            "verification_passed": False,
            "problems": problems,
            "output_checks": checks,
            "regions": [],
            "confirmed_water_extent": False,
            "area_calculated": False,
            "shoreline_calculated": False,
        }
    regions = []
    sensitive = {}
    for date in ("20260906", "20260930"):
        layers = {}
        for record in manifest["outputs"]:
            if record["date"] == date:
                layers[record["product"]] = _lists(load_mission006_raster(ROOT / record["path"])["values"])
        regions.extend(
            inventory_regions(
                date,
                layers["raw_candidate_stability"],
                layers["filtered_candidate_stability"],
                layers["raw_candidate_count"],
                layers["filtered_candidate_count"],
                layers["validity_class"],
            )
        )
        sensitive[date] = parameter_sensitive_summary(layers["filtered_candidate_stability"])
    evidence_problems = {record["dataset"]: validate_evidence(record) for record in evidence}
    reviews = [
        review_record(
            region["id"],
            "request_independent_evidence",
            "No same-date optical or terrain observation was retrieved. The patch stays an unresolved candidate group.",
        )
        for region in regions
    ]
    return {
        "mission": "007",
        "source_mission006_commit_expected": "a7fadb9d6c144d856563f310c4ada26c18e70c83",
        "verification_passed": True,
        "parameter_domain_changed": False,
        "classifier_rerun": False,
        "confirmed_water_extent": False,
        "area_calculated": False,
        "shoreline_calculated": False,
        "output_checks": checks,
        "problems": [],
        "parameter_sensitive_summary": sensitive,
        "regions": regions,
        "review_records": reviews,
        "evidence": evidence,
        "evidence_problems": evidence_problems,
        "review_decisions_allowed": list(REVIEW_DECISIONS),
        "terrain_mission_proposed": True,
        "gslc_mask_used_as_terrain": False,
    }


def looks_range_for_review_classes() -> dict:
    """Read stored Mission 003 looks at the Mission 006 review classes.

    This does not rerun the screen. It records the looks values already on disk.
    """
    summary = {}
    for date in ("20260906", "20260930"):
        looks = load_mission006_raster(
            ROOT / "data" / "processed" / "mission003" / f"{date}_gcov_frequencyA_numberOfLooks.tif"
        )["values"]
        raw = load_mission006_raster(
            ROOT / "data" / "derived" / "mission006" / f"{date}_raw_candidate_stability.tif"
        )["values"]
        filtered = load_mission006_raster(
            ROOT / "data" / "derived" / "mission006" / f"{date}_filtered_candidate_stability.tif"
        )["values"]
        summary[date] = {}
        for name, mask in (("raw_stability_code_2", raw == 2), ("filtered_stability_code_1", filtered == 1)):
            values = looks[mask]
            summary[date][name] = {
                "pixel_count": int(mask.sum()),
                "minimum": float(values.min()) if values.size else None,
                "maximum": float(values.max()) if values.size else None,
                "source": f"data/processed/mission003/{date}_gcov_frequencyA_numberOfLooks.tif",
            }
    return summary


def main() -> None:
    from datetime import datetime, timezone

    payload = build_review()
    payload["stored_looks_at_review_classes"] = looks_range_for_review_classes()
    payload["review_timestamp_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    REVIEW_MANIFEST.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print("VERIFICATION", payload["verification_passed"])
    print("PROBLEMS", len(payload["problems"]))
    print("REGIONS", len(payload["regions"]))
    if payload["problems"]:
        print(payload["problems"][0])
        raise SystemExit(1)


if __name__ == "__main__":
    main()
