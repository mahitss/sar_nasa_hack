"""Mission 008 optical archive discovery.

Queries public STAC catalogues and records scene metadata. It does not
download imagery, classify water, or change the Mission 006 screen.
"""

from __future__ import annotations

import json
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data" / "manifests" / "mission008_optical_catalogue.json"

DISCOVERY_BBOX = [79.75, 30.03, 79.87, 30.15]
DISCOVERY_CRS = "EPSG:4326"

NISAR_ACQUISITIONS = {
    "2026-09-06": "2026-09-06T13:22:36Z",
    "2026-09-30": "2026-09-30T13:22:36Z",
}

ELEMENT84_SEARCH = "https://earth-search.aws.element84.com/v1/search"
CDSE_SEARCH = "https://stac.dataspace.copernicus.eu/v1/search"
USGS_SEARCH = "https://landsatlook.usgs.gov/stac-server/search"

ELEMENT84_L2A = ("sentinel-2-l2a", "sentinel-2-c1-l2a", "sentinel-2-pre-c1-l2a")
SECRET_QUERY_KEYS = {
    "token",
    "access_token",
    "signature",
    "sig",
    "credential",
    "x-amz-signature",
    "x-amz-security-token",
}


def parse_utc(value: str) -> datetime:
    text = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def temporal_relation(acquired: str, target_date: str, fallback_days: int) -> dict:
    """Classify a scene against one NISAR calendar date.

    A scene inside the fallback window is nearby evidence. It is not
    same-date ground truth. An exact calendar date is still not ground truth.
    """
    if target_date not in NISAR_ACQUISITIONS:
        raise ValueError(f"unknown NISAR date {target_date}")
    if fallback_days < 0:
        raise ValueError("fallback_days must be zero or positive")
    moment = parse_utc(acquired)
    target = date.fromisoformat(target_date)
    offset = (moment.date() - target).days
    if offset == 0:
        kind = "exact"
    elif abs(offset) <= fallback_days:
        kind = "nearby"
    else:
        kind = "outside"
    hours = (moment - parse_utc(NISAR_ACQUISITIONS[target_date])).total_seconds() / 3600
    return {
        "nisar_date": target_date,
        "temporal_class": kind,
        "day_offset_from_nisar_date": offset,
        "hours_after_nisar_acquisition": hours,
        "same_date_ground_truth": False,
    }


def processing_level(collection_id: str, properties: dict | None = None) -> dict:
    """Preserve the catalogue processing level.

    A Level-1C collection stays Level-1C even if another property says L2.
    Level-1C is top-of-atmosphere reflectance and needs atmospheric correction
    before it can be used as a surface-reflectance source.
    """
    properties = properties or {}
    collection = collection_id.lower()
    product = str(properties.get("s2:product_type") or properties.get("product:type") or "").upper()
    stated = str(properties.get("processing:level") or "").upper()
    if "l1c" in collection or product == "S2MSI1C":
        return {
            "level": "L1C",
            "surface_reflectance": False,
            "atmospheric_correction_required": True,
            "substitutes_for_surface_reflectance": False,
        }
    if "l2a" in collection or product == "S2MSI2A" or stated in {"L2", "L2A"}:
        return {
            "level": "L2A",
            "surface_reflectance": True,
            "atmospheric_correction_required": False,
            "substitutes_for_surface_reflectance": False,
        }
    if collection == "landsat-c2l2-sr":
        return {
            "level": "Collection-2 Level-2 Surface Reflectance",
            "surface_reflectance": True,
            "atmospheric_correction_required": False,
            "substitutes_for_surface_reflectance": False,
        }
    if collection == "landsat-c2l2-st":
        return {
            "level": "Collection-2 Level-2 Surface Temperature",
            "surface_reflectance": False,
            "atmospheric_correction_required": False,
            "substitutes_for_surface_reflectance": False,
        }
    return {
        "level": "unidentified",
        "surface_reflectance": False,
        "atmospheric_correction_required": False,
        "substitutes_for_surface_reflectance": False,
    }


def _clip(points: list[tuple[float, float]], inside, intersect) -> list[tuple[float, float]]:
    if not points:
        return []
    output = []
    previous = points[-1]
    previous_inside = inside(previous)
    for current in points:
        current_inside = inside(current)
        if current_inside:
            if not previous_inside:
                output.append(intersect(previous, current))
            output.append(current)
        elif previous_inside:
            output.append(intersect(previous, current))
        previous = current
        previous_inside = current_inside
    return output


def clip_ring_to_bbox(ring: list[list[float]], bbox: list[float]) -> list[tuple[float, float]]:
    west, south, east, north = bbox
    points = [(float(x), float(y)) for x, y in ring]
    if len(points) > 1 and points[0] == points[-1]:
        points = points[:-1]

    def vertical(edge, bound):
        def intersect(start, end):
            if end[0] == start[0]:
                return (bound, start[1])
            fraction = (bound - start[0]) / (end[0] - start[0])
            return (bound, start[1] + fraction * (end[1] - start[1]))

        return _clip(edge, lambda point: point[0] >= bound if bound == west else point[0] <= bound, intersect)

    def horizontal(edge, bound, lower: bool):
        def intersect(start, end):
            if end[1] == start[1]:
                return (start[0], bound)
            fraction = (bound - start[1]) / (end[1] - start[1])
            return (start[0] + fraction * (end[0] - start[0]), bound)

        return _clip(edge, lambda point: point[1] >= bound if lower else point[1] <= bound, intersect)

    clipped = vertical(points, west)
    clipped = vertical(clipped, east)
    clipped = horizontal(clipped, south, True)
    clipped = horizontal(clipped, north, False)
    return clipped


def ring_area(points: list[tuple[float, float]]) -> float:
    if len(points) < 3:
        return 0.0
    area = 0.0
    for index, point in enumerate(points):
        nxt = points[(index + 1) % len(points)]
        area += point[0] * nxt[1] - nxt[0] * point[1]
    return abs(area) / 2


def window_overlap_percent(geometry: dict, bbox: list[float] | None = None) -> dict:
    """Approximate percentage of the discovery window covered by a footprint.

    The percentage uses planar longitude and latitude. It is not a geodesic
    area and not a lake area.
    """
    bbox = DISCOVERY_BBOX if bbox is None else bbox
    west, south, east, north = bbox
    window_area = (east - west) * (north - south)
    polygons = []
    if geometry.get("type") == "Polygon":
        polygons = [geometry.get("coordinates") or []]
    elif geometry.get("type") == "MultiPolygon":
        polygons = geometry.get("coordinates") or []
    covered = 0.0
    for polygon in polygons:
        if not polygon:
            continue
        exterior = ring_area(clip_ring_to_bbox(polygon[0], bbox))
        holes = sum(ring_area(clip_ring_to_bbox(hole, bbox)) for hole in polygon[1:])
        covered += max(0.0, exterior - holes)
    percent = 100 * covered / window_area if window_area else 0.0
    return {
        "discovery_window_covered_percent": percent,
        "intersects_discovery_window": percent > 0,
        "overlap_method": "planar longitude/latitude clip of the item footprint to the discovery window",
    }


def public_href(href: str | None) -> dict:
    if not href:
        return {"href": None, "query_secrets_removed": False}
    parts = urlsplit(href)
    kept = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key.lower() not in SECRET_QUERY_KEYS]
    removed = len(kept) != len(parse_qsl(parts.query, keep_blank_values=True))
    cleaned = urlunsplit((parts.scheme, parts.netloc, parts.path, "&".join(f"{key}={value}" for key, value in kept), ""))
    return {"href": cleaned, "query_secrets_removed": removed}


def asset_record(key: str, asset: dict) -> dict:
    bands = asset.get("eo:bands") or []
    band_gsd = [band.get("gsd") for band in bands if isinstance(band, dict) and band.get("gsd") is not None]
    href = public_href(asset.get("href"))
    return {
        "key": key,
        "media_type": asset.get("type"),
        "roles": asset.get("roles") or [],
        "gsd_meters": asset.get("gsd"),
        "band_gsd_meters": band_gsd,
        "file_size_bytes": asset.get("file:size"),
        "href": href["href"],
        "query_secrets_removed": href["query_secrets_removed"],
        "downloaded": False,
    }


def cloud_metadata(properties: dict) -> dict:
    fields = (
        "eo:cloud_cover",
        "s2:cloud_shadow_percentage",
        "s2:high_proba_clouds_percentage",
        "s2:medium_proba_clouds_percentage",
        "s2:thin_cirrus_percentage",
        "s2:nodata_pixel_percentage",
        "landsat:cloud_cover_land",
    )
    return {field: properties.get(field) for field in fields if field in properties}


def summarize_feature(feature: dict, target_date: str, fallback_days: int, catalogue: str) -> dict:
    properties = feature.get("properties") or {}
    collection = feature.get("collection") or ""
    level = processing_level(collection, properties)
    assets = [asset_record(key, asset) for key, asset in (feature.get("assets") or {}).items() if isinstance(asset, dict)]
    cloud_assets = [
        asset["key"]
        for asset in assets
        if "cloud" in asset["roles"] or asset["key"].lower().startswith(("scl", "cld", "qa_pixel", "qa_aerosol"))
    ]
    known_sizes = [asset["file_size_bytes"] for asset in assets if isinstance(asset["file_size_bytes"], int)]
    overlap = window_overlap_percent(feature.get("geometry") or {})
    relation = temporal_relation(properties["datetime"], target_date, fallback_days)
    return {
        "catalogue": catalogue,
        "collection_id": collection,
        "item_id": feature.get("id"),
        "datetime_utc": properties.get("datetime"),
        "start_datetime_utc": properties.get("start_datetime"),
        "end_datetime_utc": properties.get("end_datetime"),
        "platform": properties.get("platform"),
        "instruments": properties.get("instruments"),
        "constellation": properties.get("constellation"),
        "processing": level,
        "stated_processing_level": properties.get("processing:level"),
        "product_type": properties.get("s2:product_type") or properties.get("product:type"),
        "product_uri": properties.get("s2:product_uri"),
        "processing_baseline": properties.get("s2:processing_baseline") or properties.get("processing:version"),
        "mgrs_grid": properties.get("grid:code"),
        "mgrs_utm_zone": properties.get("mgrs:utm_zone"),
        "mgrs_latitude_band": properties.get("mgrs:latitude_band"),
        "mgrs_grid_square": properties.get("mgrs:grid_square"),
        "landsat_product_id": feature.get("id") if collection == "landsat-c2l2-sr" else None,
        "landsat_scene_id": properties.get("landsat:scene_id"),
        "wrs_path": properties.get("landsat:wrs_path"),
        "wrs_row": properties.get("landsat:wrs_row"),
        "wrs_type": properties.get("landsat:wrs_type"),
        "landsat_collection_number": properties.get("landsat:collection_number"),
        "landsat_collection_category": properties.get("landsat:collection_category"),
        "landsat_correction": properties.get("landsat:correction"),
        "proj_epsg": properties.get("proj:epsg"),
        "cloud": cloud_metadata(properties),
        "cloud_is_scene_wide": True,
        "diagnostic_window_cloud_known": False,
        "cloud_mask_assets": cloud_assets,
        "assets": assets,
        "known_asset_size_bytes": sum(known_sizes) if known_sizes else None,
        "assets_missing_size": sum(1 for asset in assets if asset["file_size_bytes"] is None),
        "bbox": feature.get("bbox"),
        "geometry": feature.get("geometry"),
        "overlap": overlap,
        "temporal": relation,
        "requester_pays": (properties.get("storage:requester_pays")),
        "imagery_downloaded": False,
        "used_to_retune_thresholds": False,
        "water_classified": False,
    }


def pagination_status(matched, collected_ids: list[str], unfollowed_next: bool) -> dict:
    unique = len(set(collected_ids))
    if unfollowed_next:
        return {
            "complete": False,
            "matched_reported": matched is not None,
            "matched": matched,
            "collected": unique,
            "reason": "a next link was not followed",
        }
    if matched is None:
        return {
            "complete": True,
            "matched_reported": False,
            "matched": None,
            "collected": unique,
            "reason": "the server did not report numberMatched and no next link remained",
        }
    complete = matched == unique
    return {
        "complete": complete,
        "matched_reported": True,
        "matched": matched,
        "collected": unique,
        "reason": "matched equals collected items" if complete else "matched does not equal collected items",
    }


def _request_json(url: str, body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode()
    headers = {"Accept": "application/geo+json, application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.loads(response.read().decode())


def search_pages(url: str, body: dict, page_limit: int = 20) -> tuple[list[dict], bool]:
    """Follow STAC next links. Tokens are not returned."""
    pages = [_request_json(url, body)]
    seen = set()
    while len(pages) < page_limit:
        link = next((item for item in pages[-1].get("links") or [] if item.get("rel") == "next"), None)
        if link is None:
            return pages, False
        method = str(link.get("method") or "GET").upper()
        if method == "POST":
            next_body = link.get("body") or {}
            marker = json.dumps(next_body.get("next"), sort_keys=True, default=str)
            if marker in seen:
                return pages, False
            seen.add(marker)
            pages.append(_request_json(link.get("href") or url, next_body))
        else:
            href = link.get("href")
            if not href or href in seen:
                return pages, False
            seen.add(href)
            pages.append(_request_json(href))
    link = next((item for item in pages[-1].get("links") or [] if item.get("rel") == "next"), None)
    return pages, link is not None


def _matched(page: dict):
    context = page.get("context") or {}
    if "matched" in context:
        return context.get("matched")
    return page.get("numberMatched")


def query_plan() -> list[dict]:
    exact = {
        "2026-09-06": "2026-09-06T00:00:00Z/2026-09-06T23:59:59Z",
        "2026-09-30": "2026-09-30T00:00:00Z/2026-09-30T23:59:59Z",
    }
    sentinel_nearby = {
        "2026-09-06": "2026-09-01T00:00:00Z/2026-09-11T23:59:59Z",
        "2026-09-30": "2026-09-25T00:00:00Z/2026-10-05T23:59:59Z",
    }
    landsat_nearby = {
        "2026-09-06": "2026-08-29T00:00:00Z/2026-09-14T23:59:59Z",
        "2026-09-30": "2026-09-22T00:00:00Z/2026-10-08T23:59:59Z",
    }
    plan = []
    for collection in ELEMENT84_L2A:
        for target, interval in exact.items():
            plan.append(_query("element84", ELEMENT84_SEARCH, collection, target, "exact", interval, 5))
        for target, interval in sentinel_nearby.items():
            plan.append(_query("element84", ELEMENT84_SEARCH, collection, target, "nearby_window", interval, 5))
    for collection in ("sentinel-2-l1c",):
        for target, interval in exact.items():
            plan.append(_query("element84", ELEMENT84_SEARCH, collection, target, "exact", interval, 5, "L1C fallback because the exact NISAR dates had to be checked independently of L2A"))
        for target, interval in sentinel_nearby.items():
            plan.append(_query("element84", ELEMENT84_SEARCH, collection, target, "nearby_window", interval, 5, "L1C fallback, not a surface-reflectance product"))
    for collection in ("sentinel-2-l2a", "sentinel-2-l1c"):
        for target, interval in exact.items():
            plan.append(_query("copernicus", CDSE_SEARCH, collection, target, "exact", interval, 5))
        for target, interval in sentinel_nearby.items():
            plan.append(_query("copernicus", CDSE_SEARCH, collection, target, "nearby_window", interval, 5))
    for target, interval in exact.items():
        plan.append(_query("usgs", USGS_SEARCH, "landsat-c2l2-sr", target, "exact", interval, 8))
    for target, interval in landsat_nearby.items():
        plan.append(_query("usgs", USGS_SEARCH, "landsat-c2l2-sr", target, "nearby_window", interval, 8))
    return plan


def _query(catalogue, endpoint, collection, target, mode, interval, fallback_days, note=None) -> dict:
    return {
        "catalogue": catalogue,
        "endpoint": endpoint,
        "collection_id": collection,
        "nisar_date": target,
        "search_class": mode,
        "datetime": interval,
        "fallback_days": fallback_days,
        "note": note,
    }


def run_query(spec: dict) -> dict:
    body = {
        "collections": [spec["collection_id"]],
        "bbox": DISCOVERY_BBOX,
        "datetime": spec["datetime"],
        "limit": 50,
    }
    try:
        pages, unfollowed = search_pages(spec["endpoint"], body)
    except Exception as exc:
        return {
            **spec,
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc)[:300],
            "items": [],
            "pagination": {"complete": False, "reason": "query failed"},
        }
    features = [feature for page in pages for feature in page.get("features") or []]
    items = [
        summarize_feature(feature, spec["nisar_date"], spec["fallback_days"], spec["catalogue"])
        for feature in features
        if (feature.get("properties") or {}).get("datetime")
    ]
    status = pagination_status(_matched(pages[0]), [item["item_id"] for item in items], unfollowed)
    status["pages"] = len(pages)
    return {**spec, "ok": True, "items": items, "pagination": status}


def catalogue_versions() -> list[dict]:
    roots = [
        ("element84", "https://earth-search.aws.element84.com/v1/"),
        ("copernicus", "https://stac.dataspace.copernicus.eu/v1/"),
        ("usgs", "https://landsatlook.usgs.gov/stac-server/"),
    ]
    found = []
    for name, url in roots:
        document = _request_json(url)
        found.append(
            {
                "catalogue": name,
                "endpoint": url,
                "stac_version": document.get("stac_version"),
                "catalogue_id": document.get("id"),
                "title": document.get("title"),
            }
        )
    return found


def build_manifest(query_results: list[dict], versions: list[dict], timestamp: str) -> dict:
    items = []
    queries = []
    failures = []
    for result in query_results:
        queries.append(
            {
                "catalogue": result["catalogue"],
                "endpoint": result["endpoint"],
                "collection_id": result["collection_id"],
                "nisar_date": result["nisar_date"],
                "search_class": result["search_class"],
                "datetime": result["datetime"],
                "fallback_days": result["fallback_days"],
                "note": result.get("note"),
                "ok": result["ok"],
                "pagination": result.get("pagination"),
                "item_ids": [item["item_id"] for item in result.get("items") or []],
            }
        )
        if not result["ok"]:
            failures.append({"collection_id": result["collection_id"], "datetime": result["datetime"], "error_type": result.get("error_type"), "error": result.get("error")})
        for item in result.get("items") or []:
            recorded = dict(item)
            recorded["search_class"] = result["search_class"]
            recorded["query_datetime"] = result["datetime"]
            items.append(recorded)
    return {
        "mission": "008",
        "query_timestamp_utc": timestamp,
        "discovery_window": {
            "crs": DISCOVERY_CRS,
            "bbox": DISCOVERY_BBOX,
            "bbox_order": "west, south, east, north",
            "role": "catalogue discovery window, not a mapped lake boundary",
        },
        "literature_location": {
            "description": "Published Kuwari landslide location cited by Mission 007 from Ghoke and colleagues",
            "latitude_north": [30.084, 30.087],
            "longitude_east": [79.79, 79.80],
            "role": "literature context, not a surveyed candidate-patch location",
        },
        "nisar_acquisitions_utc": NISAR_ACQUISITIONS,
        "candidate_patch_coordinates": "Mission 007 row and column coordinates were not converted to longitude and latitude",
        "catalogues": versions,
        "queries": queries,
        "items": items,
        "failures": failures,
        "imagery_downloaded": False,
        "cloud_masks_downloaded": False,
        "water_classified": False,
        "area_calculated": False,
        "shoreline_calculated": False,
        "mission006_outputs_modified": False,
        "mission006_thresholds_changed": False,
        "optical_scenes_used_as_ground_truth": False,
        "software": {"python": _python_version()},
    }


def _python_version() -> str:
    import sys

    return sys.version.split()[0]


def main() -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    versions = catalogue_versions()
    results = [run_query(spec) for spec in query_plan()]
    manifest = build_manifest(results, versions, timestamp)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("QUERIES", len(manifest["queries"]))
    print("ITEMS", len(manifest["items"]))
    print("FAILURES", len(manifest["failures"]))
    print("INCOMPLETE", sum(1 for query in manifest["queries"] if query.get("pagination") and not query["pagination"].get("complete", False)))


if __name__ == "__main__":
    main()
