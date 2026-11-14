"""Revalidate NISAR L-band GCOV and GSLC catalogue records for Kuwari.

This module uses the Python standard library only. It queries NASA CMR,
checks the published study point against each footprint, and writes a
catalogue manifest. It does not download science files.

Run from the repository root:

    python tools/catalogue_audit.py
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping, Sequence

CMR_GRANULE_ENDPOINT = "https://cmr.earthdata.nasa.gov/search/granules.umm_json"
SHORT_NAMES = (
    "NISAR_L2_GCOV_PROVISIONAL_V1",
    "NISAR_L2_GSLC_PROVISIONAL_V1",
    "NISAR_L2_GCOV_V1",
    "NISAR_L2_GSLC_V1",
)
BOUNDING_BOX = "79.75,30.03,79.87,30.15"
TEMPORAL = "2026-07-08T00:00:00Z,2026-11-14T23:59:59Z"
STUDY_LATITUDE = 30.088337
STUDY_LONGITUDE = 79.808685
STUDY_POINT_SOURCE = (
    "SANDRP commentary, 22 November 2024. Secondary-source location, "
    "not a survey-grade coordinate."
)
PAGE_SIZE = 200
PAGE_GUARD = 100

FILENAME_RE = re.compile(
    r"^NISAR_L(?P<level>\d)_(?P<processing>PR|UR|OD)_(?P<product>GCOV|GSLC)_"
    r"(?P<cycle>\d{3})_(?P<track>\d{3})_(?P<direction>[AD])_(?P<frame>\d{3})_"
    r"(?P<mode>\d{4})_(?P<polarization>[A-Z]{4})_(?P<source>[AM])_"
    r"(?P<start>\d{8}T\d{6})_(?P<end>\d{8}T\d{6})_"
    r"(?P<crid>P\d{5})_(?P<orbit_letter>[PMNF])_(?P<coverage>[FP])_"
    r"(?P<location>[A-Z])_(?P<counter>\d{3})$"
)

# Primary-band codes from the ASF GCOV naming convention.
POLARIZATION_CODES = {
    "SH": frozenset({"HH"}),
    "SV": frozenset({"VV"}),
    "DH": frozenset({"HH", "HV"}),
    "DV": frozenset({"VV", "VH"}),
    "QP": frozenset({"HH", "HV", "VH", "VV"}),
    "CL": frozenset({"LH", "LV"}),
    "CR": frozenset({"RH", "RV"}),
}

ORBIT_LETTER_MEANING = {
    "P": "precise",
    "M": "medium",
    "N": "near_real_time",
    "F": "forecast",
}

SIGNED_QUERY_MARKERS = (
    "x-amz-signature",
    "x-amz-credential",
    "x-amz-security-token",
    "signature=",
    "token=",
    "awsaccesskeyid",
)

D40_REQUIREMENTS = {
    "product_type": "GCOV",
    "orbit_direction": "DESCENDING",
    "track": 5,
    "frame": 73,
    "frequency_a_bandwidth_mhz": 40,
    "frequency_a_polarizations": ("HH", "HV"),
    "crid": "P05023",
}


def point_on_segment(
    lon: float,
    lat: float,
    ax: float,
    ay: float,
    bx: float,
    by: float,
    eps: float = 1e-9,
) -> bool:
    """Return True when the point lies on the segment, including endpoints."""
    cross = (lon - ax) * (by - ay) - (lat - ay) * (bx - ax)
    if abs(cross) > eps:
        return False
    dot = (lon - ax) * (bx - ax) + (lat - ay) * (by - ay)
    if dot < -eps:
        return False
    length_sq = (bx - ax) ** 2 + (by - ay) ** 2
    if dot - length_sq > eps:
        return False
    return True


def point_in_ring(
    lon: float,
    lat: float,
    ring: Sequence[tuple[float, float]],
    eps: float = 1e-9,
) -> bool:
    """Even-odd containment. A point on the boundary counts as inside."""
    points = list(ring)
    if len(points) >= 2 and points[0] == points[-1]:
        points = points[:-1]
    count = len(points)
    if count < 3:
        return False
    for index in range(count):
        ax, ay = points[index]
        bx, by = points[(index + 1) % count]
        if point_on_segment(lon, lat, ax, ay, bx, by, eps):
            return True
    inside = False
    previous = count - 1
    for index in range(count):
        lon_i, lat_i = points[index]
        lon_j, lat_j = points[previous]
        crosses = (lat_i > lat) != (lat_j > lat)
        if crosses:
            edge_lon = (lon_j - lon_i) * (lat - lat_i) / (lat_j - lat_i) + lon_i
            if lon < edge_lon:
                inside = not inside
        previous = index
    return inside


def point_in_footprint(
    lon: float,
    lat: float,
    polygons: Sequence[Mapping[str, Any]],
) -> bool | None:
    """True if the point is in any exterior ring and not in a hole interior."""
    if not polygons:
        return None
    for polygon in polygons:
        exterior = polygon.get("exterior") or []
        if not point_in_ring(lon, lat, exterior):
            continue
        in_hole = False
        for hole in polygon.get("holes") or []:
            if point_in_ring(lon, lat, hole) and not _on_ring_boundary(lon, lat, hole):
                in_hole = True
                break
        if not in_hole:
            return True
    return False


def _on_ring_boundary(
    lon: float,
    lat: float,
    ring: Sequence[tuple[float, float]],
) -> bool:
    points = list(ring)
    if len(points) >= 2 and points[0] == points[-1]:
        points = points[:-1]
    count = len(points)
    for index in range(count):
        ax, ay = points[index]
        bx, by = points[(index + 1) % count]
        if point_on_segment(lon, lat, ax, ay, bx, by):
            return True
    return False


def comparability_key(record: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        record.get("product_type"),
        record.get("orbit_direction"),
        record.get("track"),
        record.get("frame"),
        record.get("frequency_a_bandwidth_mhz"),
        tuple(record.get("frequency_a_polarizations") or ()),
        record.get("crid"),
    )


def incompatibility_reasons(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> list[str]:
    """Reasons two records must not be differenced. Empty means compatible."""
    reasons: list[str] = []
    if left.get("crid") != right.get("crid"):
        reasons.append("different_crid")
    if left.get("frequency_a_bandwidth_mhz") != right.get("frequency_a_bandwidth_mhz"):
        reasons.append("different_bandwidth")
    if tuple(left.get("frequency_a_polarizations") or ()) != tuple(
        right.get("frequency_a_polarizations") or ()
    ):
        reasons.append("different_polarization")
    if left.get("orbit_direction") != right.get("orbit_direction"):
        reasons.append("different_orbit")
    if left.get("track") != right.get("track"):
        reasons.append("different_track")
    if left.get("frame") != right.get("frame"):
        reasons.append("different_frame")
    if left.get("product_type") != right.get("product_type"):
        reasons.append("different_product_type")
    return reasons


def is_d40(record: Mapping[str, Any]) -> bool:
    polarizations = tuple(record.get("frequency_a_polarizations") or ())
    return (
        record.get("product_type") == D40_REQUIREMENTS["product_type"]
        and record.get("orbit_direction") == D40_REQUIREMENTS["orbit_direction"]
        and record.get("track") == D40_REQUIREMENTS["track"]
        and record.get("frame") == D40_REQUIREMENTS["frame"]
        and record.get("frequency_a_bandwidth_mhz")
        == D40_REQUIREMENTS["frequency_a_bandwidth_mhz"]
        and polarizations == D40_REQUIREMENTS["frequency_a_polarizations"]
        and record.get("crid") == D40_REQUIREMENTS["crid"]
        and record.get("contains_study_point") is True
    )


def is_validated_d40_mode(record: Mapping[str, Any]) -> bool:
    """Same geometry and mode as D40, but the validated CRID P05036."""
    polarizations = tuple(record.get("frequency_a_polarizations") or ())
    return (
        record.get("product_type") == "GCOV"
        and record.get("collection_short_name") == "NISAR_L2_GCOV_V1"
        and record.get("orbit_direction") == "DESCENDING"
        and record.get("track") == 5
        and record.get("frame") == 73
        and record.get("frequency_a_bandwidth_mhz") == 40
        and polarizations == ("HH", "HV")
        and record.get("crid") == "P05036"
        and record.get("contains_study_point") is True
    )


def find_duplicates(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Detect repeated granule URs and multiple versions of one acquisition."""
    found: list[dict[str, Any]] = []
    by_ur: dict[str, list[Mapping[str, Any]]] = {}
    for record in records:
        by_ur.setdefault(str(record.get("granule_ur")), []).append(record)
    for granule_ur, group in sorted(by_ur.items()):
        if len(group) > 1:
            found.append(
                {
                    "kind": "repeated_granule_ur",
                    "granule_ur": granule_ur,
                    "count": len(group),
                }
            )
    by_identity: dict[tuple[Any, ...], list[str]] = {}
    for record in records:
        identity = (
            record.get("collection_short_name"),
            record.get("acquisition_start"),
            record.get("product_type"),
            record.get("track"),
            record.get("frame"),
            record.get("orbit_direction"),
            record.get("frequency_a_bandwidth_mhz"),
            tuple(record.get("frequency_a_polarizations") or ()),
            record.get("crid"),
        )
        by_identity.setdefault(identity, []).append(str(record.get("granule_ur")))
    for identity, urs in sorted(by_identity.items(), key=lambda item: item[1]):
        unique = sorted(set(urs))
        if len(unique) > 1:
            found.append(
                {
                    "kind": "multiple_versions_of_one_acquisition",
                    "collection_short_name": identity[0],
                    "acquisition_start": identity[1],
                    "product_type": identity[2],
                    "granule_urs": unique,
                }
            )
    return found


def prefer_version(records: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    """Prefer the highest product counter, then the highest CMR revision."""

    def sort_key(record: Mapping[str, Any]) -> tuple[int, int, str]:
        counter = record.get("product_counter")
        counter_value = int(counter) if isinstance(counter, int) else -1
        revision = record.get("revision_id")
        revision_value = int(revision) if isinstance(revision, int) else -1
        return (counter_value, revision_value, str(record.get("granule_ur")))

    return max(records, key=sort_key)


def acquisition_separation_days(start_a: str, start_b: str) -> float | None:
    try:
        left = _parse_time(start_a)
        right = _parse_time(start_b)
    except ValueError:
        return None
    return round(abs((left - right).total_seconds()) / 86400.0, 6)


def rank_pairs(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Rank distinct-time pairs. The two latest acquisitions are rank 1."""
    ordered = sorted(
        records,
        key=lambda record: (
            str(record.get("acquisition_start")),
            str(record.get("granule_ur")),
        ),
    )
    pairs: list[dict[str, Any]] = []
    for left_index, left in enumerate(ordered):
        for right in ordered[left_index + 1 :]:
            if left.get("acquisition_start") == right.get("acquisition_start"):
                continue
            reasons = incompatibility_reasons(left, right)
            separation = acquisition_separation_days(
                str(left.get("acquisition_start")),
                str(right.get("acquisition_start")),
            )
            pairs.append(
                {
                    "earlier_granule_ur": left.get("granule_ur"),
                    "later_granule_ur": right.get("granule_ur"),
                    "earlier_acquisition_start": left.get("acquisition_start"),
                    "later_acquisition_start": right.get("acquisition_start"),
                    "separation_days": separation,
                    "crid": left.get("crid"),
                    "compatible": not reasons,
                    "incompatibility_reasons": reasons,
                    "status": "pending_raster_quality_control",
                }
            )
    pairs.sort(
        key=lambda pair: (
            str(pair["later_acquisition_start"]),
            str(pair["earlier_acquisition_start"]),
        ),
        reverse=True,
    )
    for index, pair in enumerate(pairs, start=1):
        pair["rank"] = index
    return pairs


def sanitize_url(url: str) -> dict[str, Any] | None:
    """Keep a stable URL. Drop signed queries and non-https links."""
    if not url or not url.lower().startswith("https://"):
        return None
    parts = urllib.parse.urlsplit(url)
    query = parts.query.lower()
    signed = any(marker in query for marker in SIGNED_QUERY_MARKERS)
    if signed:
        return {
            "url": urllib.parse.urlunsplit(
                (parts.scheme, parts.netloc, parts.path, "", "")
            ),
            "signed_query_removed": True,
        }
    return {"url": url, "signed_query_removed": False}


def build_search_url(short_name: str, page_num: int) -> str:
    query = urllib.parse.urlencode(
        {
            "short_name": short_name,
            "bounding_box": BOUNDING_BOX,
            "temporal": TEMPORAL,
            "page_size": PAGE_SIZE,
            "page_num": page_num,
        }
    )
    return f"{CMR_GRANULE_ENDPOINT}?{query}"


def fetch_collection(
    short_name: str,
    opener: Callable[..., Any],
) -> dict[str, Any]:
    """Follow CMR pages until every hit in the collection search is loaded."""
    pages: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    hits: int | None = None
    page_num = 1
    while page_num <= PAGE_GUARD:
        url = build_search_url(short_name, page_num)
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        with opener(request, timeout=120) as response:
            header_hits = response.headers.get("CMR-Hits")
            if header_hits is not None:
                hits = int(header_hits)
            payload = json.loads(response.read().decode("utf-8"))
        page_items = payload.get("items") or []
        pages.append({"page_num": page_num, "url": url, "item_count": len(page_items)})
        items.extend(page_items)
        if not page_items:
            break
        if hits is not None and len(items) >= hits:
            break
        page_num += 1
    else:
        raise RuntimeError(f"CMR pagination exceeded {PAGE_GUARD} pages for {short_name}")
    if hits is not None and len(items) != hits:
        raise RuntimeError(
            f"CMR hit count {hits} did not match retrieved {len(items)} for {short_name}"
        )
    return {"short_name": short_name, "hits": hits, "pages": pages, "items": items}


def parse_granule(item: Mapping[str, Any], source_page_url: str) -> dict[str, Any]:
    meta = item.get("meta") or {}
    umm = item.get("umm") or {}
    attributes = {
        entry.get("Name"): entry.get("Values") or []
        for entry in (umm.get("AdditionalAttributes") or [])
    }
    identifiers = (umm.get("DataGranule") or {}).get("Identifiers") or []
    identifier_map = _identifiers(identifiers)
    granule_ur = umm.get("GranuleUR")
    temporal = ((umm.get("TemporalExtent") or {}).get("RangeDateTime") or {})
    polygons = _polygons(umm)
    contains = point_in_footprint(STUDY_LONGITUDE, STUDY_LATITUDE, polygons)
    filename_check = _filename_agreement(
        granule_ur,
        attributes,
        identifier_map,
        temporal,
    )
    polarizations = tuple(sorted(attributes.get("FREQUENCY_A_POLARIZATION") or []))
    archive = (umm.get("DataGranule") or {}).get("ArchiveAndDistributionInformation") or []
    access_links = []
    for related in umm.get("RelatedUrls") or []:
        if related.get("Type") != "GET DATA":
            continue
        cleaned = sanitize_url(related.get("URL") or "")
        if cleaned is None:
            continue
        access_links.append(
            {
                "type": related.get("Type"),
                "url": cleaned["url"],
                "signed_query_removed": cleaned["signed_query_removed"],
            }
        )
    access_links.sort(key=lambda link: link["url"])
    concept_id = meta.get("concept-id")
    record = {
        "collection_short_name": (umm.get("CollectionReference") or {}).get("ShortName"),
        "collection_concept_id": meta.get("collection-concept-id"),
        "granule_concept_id": concept_id,
        "granule_concept_url": (
            f"https://cmr.earthdata.nasa.gov/search/concepts/{concept_id}.umm_json"
            if concept_id
            else None
        ),
        "producer_granule_id": identifier_map.get("ProducerGranuleId"),
        "granule_ur": granule_ur,
        "acquisition_start": temporal.get("BeginningDateTime"),
        "acquisition_end": temporal.get("EndingDateTime"),
        "track": _as_int(_first(attributes.get("TRACK_NUMBER"))),
        "frame": _as_int(_first(attributes.get("FRAME_NUMBER"))),
        "orbit_direction": _first(attributes.get("ASCENDING_DESCENDING")),
        "frequency_a_bandwidth_mhz": _as_int(
            _first(attributes.get("FREQUENCY_A_RANGE_BANDWIDTH"))
        ),
        "frequency_a_polarizations": polarizations,
        "frequency_a_polarization_concat": _first(
            attributes.get("FREQUENCY_A_POLARIZATION_CONCAT")
        ),
        "frequency_b_bandwidth_mhz": _as_int(
            _first(attributes.get("FREQUENCY_B_RANGE_BANDWIDTH"))
        ),
        "crid": identifier_map.get("CRID"),
        "product_version": _first(attributes.get("PRODUCT_VERSION")),
        "product_counter": _as_int(identifier_map.get("ProductCounter")),
        "sas_version": identifier_map.get("SASVersionId"),
        "orbit_type": _first(attributes.get("ORBIT_TYPE")),
        "product_type": _first(attributes.get("PRODUCT_TYPE")),
        "processing_center": _first(attributes.get("PROCESSING_CENTER")),
        "full_frame": _first(attributes.get("FULL_FRAME")),
        "joint_observation": _first(attributes.get("JOINT_OBSERVATION")),
        "revision_id": meta.get("revision-id"),
        "revision_date": meta.get("revision-date"),
        "spatial_footprint": polygons,
        "contains_study_point": contains,
        "source_catalogue_url": source_page_url,
        "data_access_links": access_links,
        "files": [
            {
                "name": entry.get("Name"),
                "size_bytes": entry.get("SizeInBytes"),
                "format": entry.get("Format"),
                "checksum_algorithm": (entry.get("Checksum") or {}).get("Algorithm"),
                "checksum": (entry.get("Checksum") or {}).get("Value"),
            }
            for entry in archive
        ],
        "filename_metadata_agreement": filename_check,
    }
    return record


def build_manifest(
    fetched: Sequence[Mapping[str, Any]],
    retrieved_at: str,
) -> dict[str, Any]:
    granules: list[dict[str, Any]] = []
    queries = []
    for collection in fetched:
        for page in collection["pages"]:
            queries.append(
                {
                    "short_name": collection["short_name"],
                    "page_num": page["page_num"],
                    "url": page["url"],
                    "item_count": page["item_count"],
                    "cmr_hits": collection["hits"],
                }
            )
        for page in collection["pages"]:
            for item in _items_for_page(collection, page):
                granules.append(parse_granule(item, page["url"]))
    granules.sort(
        key=lambda record: (
            str(record.get("collection_short_name")),
            str(record.get("acquisition_start")),
            str(record.get("granule_ur")),
        )
    )
    rejected = [
        {
            "granule_ur": record["granule_ur"],
            "collection_short_name": record["collection_short_name"],
            "reason": (
                "footprint_misses_study_point"
                if record["contains_study_point"] is False
                else "footprint_missing_from_catalogue"
            ),
        }
        for record in granules
        if record["contains_study_point"] is not True
    ]
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for record in granules:
        if record["contains_study_point"] is not True:
            continue
        groups.setdefault(comparability_key(record), []).append(record)
    group_rows = []
    for key, members in sorted(groups.items(), key=lambda item: json.dumps(item[0])):
        group_rows.append(
            {
                "product_type": key[0],
                "orbit_direction": key[1],
                "track": key[2],
                "frame": key[3],
                "frequency_a_bandwidth_mhz": key[4],
                "frequency_a_polarizations": list(key[5]),
                "crid": key[6],
                "contains_study_point": True,
                "granule_urs": [member["granule_ur"] for member in members],
                "acquisition_starts": [member["acquisition_start"] for member in members],
            }
        )
    d40_selected, d40_duplicates = _select_unique(
        [record for record in granules if is_d40(record)]
    )
    validated_selected, validated_duplicates = _select_unique(
        [record for record in granules if is_validated_d40_mode(record)]
    )
    d40_pairs = rank_pairs(d40_selected)
    validated_pairs = rank_pairs(validated_selected)
    for pair in d40_pairs:
        pair["group"] = "D40"
        pair["maturity"] = "PROVISIONAL"
        pair["known_limits"] = _pair_limits("P05023")
    for pair in validated_pairs:
        pair["group"] = "validated_same_mode_as_D40"
        pair["maturity"] = "VALIDATED"
        pair["known_limits"] = _pair_limits("P05036")
    companions = _gslc_companions(granules, d40_selected)
    counts: dict[str, int] = {}
    for record in granules:
        name = str(record.get("collection_short_name"))
        counts[name] = counts.get(name, 0) + 1
    recommended = d40_pairs[0] if d40_pairs else None
    return {
        "manifest_type": "nisar_catalogue_record",
        "statement": (
            "This file is a catalogue record from NASA CMR metadata. "
            "It is not evidence that a scientific measurement succeeded. "
            "No HDF5 or GeoTIFF file was downloaded. "
            "The recommended pair is pending raster quality control."
        ),
        "retrieval_timestamp": retrieved_at,
        "study_point": {
            "latitude": STUDY_LATITUDE,
            "longitude": STUDY_LONGITUDE,
            "source": STUDY_POINT_SOURCE,
            "containment_method": "even_odd_ray_cast_boundary_included",
        },
        "discovery_bounding_box": {
            "west": 79.75,
            "south": 30.03,
            "east": 79.87,
            "north": 30.15,
        },
        "temporal_range": {
            "start": "2026-07-08T00:00:00Z",
            "end": "2026-11-14T23:59:59Z",
        },
        "queries": queries,
        "result_counts": counts,
        "granules": granules,
        "comparability_groups": group_rows,
        "rejected_candidates": rejected,
        "duplicates": find_duplicates(granules) + d40_duplicates + validated_duplicates,
        "group_d40": {
            "definition": D40_REQUIREMENTS,
            "selected_granule_urs": [record["granule_ur"] for record in d40_selected],
            "pairs": d40_pairs,
        },
        "validated_p05036_same_mode": {
            "selected_granule_urs": [
                record["granule_ur"] for record in validated_selected
            ],
            "pairs": validated_pairs,
            "recommendation": (
                "A validated same-mode pair exists and is listed separately. "
                "Do not mix it with provisional P05023."
                if len(validated_selected) >= 2
                else "Fewer than two validated P05036 acquisitions share the D40 "
                "geometry, bandwidth, polarization, and study-point coverage. "
                "No validated pair is recommended."
            ),
        },
        "gslc_companions_for_d40": companions,
        "recommended_pair": recommended,
        "outstanding_uncertainties": _uncertainties(granules, recommended),
        "references": [
            "https://cmr.earthdata.nasa.gov/search/granules.umm_json",
            "https://nisar-docs.asf.alaska.edu/gcov/",
            "https://nisar-docs.asf.alaska.edu/products-overview/",
            "https://nisar-docs.asf.alaska.edu/gslc/",
        ],
    }


def write_manifest(path: str, opener: Callable[..., Any] | None = None) -> dict[str, Any]:
    fetch = opener or urllib.request.urlopen
    retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    fetched = [fetch_collection(name, fetch) for name in SHORT_NAMES]
    manifest = build_manifest(fetched, retrieved_at)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return manifest


def _items_for_page(
    collection: Mapping[str, Any],
    page: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    """Slice the flat item list back into the page that fetched it."""
    offset = 0
    for earlier in collection["pages"]:
        if earlier["page_num"] == page["page_num"]:
            return list(collection["items"][offset : offset + page["item_count"]])
        offset += earlier["item_count"]
    return []


def _select_unique(
    records: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    buckets: dict[tuple[Any, ...], list[Mapping[str, Any]]] = {}
    for record in records:
        identity = (
            record.get("acquisition_start"),
            record.get("track"),
            record.get("frame"),
            record.get("crid"),
            record.get("frequency_a_bandwidth_mhz"),
            tuple(record.get("frequency_a_polarizations") or ()),
        )
        buckets.setdefault(identity, []).append(record)
    selected = []
    notes = []
    for identity, bucket in sorted(buckets.items(), key=lambda item: str(item[0][0])):
        chosen = prefer_version(bucket)
        selected.append(dict(chosen))
        if len(bucket) > 1:
            notes.append(
                {
                    "kind": "version_preference",
                    "acquisition_start": identity[0],
                    "preferred_granule_ur": chosen.get("granule_ur"),
                    "preference_rule": "highest_product_counter_then_highest_revision_id",
                    "other_granule_urs": [
                        item.get("granule_ur")
                        for item in bucket
                        if item.get("granule_ur") != chosen.get("granule_ur")
                    ],
                }
            )
    return selected, notes


def _gslc_companions(
    granules: Sequence[Mapping[str, Any]],
    gcov_records: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for gcov in gcov_records:
        matches = [
            record
            for record in granules
            if record.get("product_type") == "GSLC"
            and record.get("acquisition_start") == gcov.get("acquisition_start")
            and record.get("track") == gcov.get("track")
            and record.get("frame") == gcov.get("frame")
            and record.get("orbit_direction") == gcov.get("orbit_direction")
            and record.get("frequency_a_bandwidth_mhz")
            == gcov.get("frequency_a_bandwidth_mhz")
            and tuple(record.get("frequency_a_polarizations") or ())
            == tuple(gcov.get("frequency_a_polarizations") or ())
            and record.get("crid") == gcov.get("crid")
            and record.get("contains_study_point") is True
        ]
        chosen = prefer_version(matches) if matches else None
        rows.append(
            {
                "gcov_granule_ur": gcov.get("granule_ur"),
                "acquisition_start": gcov.get("acquisition_start"),
                "match_count": len(matches),
                "preferred_gslc_granule_ur": None
                if chosen is None
                else chosen.get("granule_ur"),
                "preferred_product_version": None
                if chosen is None
                else chosen.get("product_version"),
                "preferred_product_counter": None
                if chosen is None
                else chosen.get("product_counter"),
                "preferred_crid": None if chosen is None else chosen.get("crid"),
                "footprint_contains_study_point": None
                if chosen is None
                else chosen.get("contains_study_point"),
                "other_gslc_granule_urs": [
                    record.get("granule_ur")
                    for record in matches
                    if chosen is not None
                    and record.get("granule_ur") != chosen.get("granule_ur")
                ],
                "preference_rule": (
                    "highest_product_counter_then_highest_revision_id"
                    if len(matches) > 1
                    else None
                ),
            }
        )
    return rows


def _pair_limits(crid: str) -> list[str]:
    return [
        f"Catalogue maturity label follows CRID {crid}. Raster quality is unexamined.",
        "ASF states that mixing data maturities can introduce processing differences.",
        "GCOV pixel spacing is a posting. It is not independent spatial resolution.",
        "The GCOV mask describes the adaptive multi-looking ensemble, not water.",
        "The GSLC mask is the layer documented for water and shadow-layover.",
        "Backscatter contrast, layover at the lake, numberOfLooks, and RFI cannot be judged until the HDF5 is opened.",
    ]


def _uncertainties(
    granules: Sequence[Mapping[str, Any]],
    recommended: Mapping[str, Any] | None,
) -> list[str]:
    orbit_mismatches = [
        record["granule_ur"]
        for record in granules
        if any(
            not check["match"] and check["field"] == "orbit_fidelity_letter"
            for check in record["filename_metadata_agreement"]["checks"]
        )
    ]
    notes = [
        "The study coordinate is a secondary published location, not a surveyed lake polygon.",
        "Bounding-box intersection alone is not study-point coverage.",
        "No science file was opened, so geolocation, speckle, and mask values at the lake are unknown.",
        "S-band rasters inside joint-observation HDF5 files were not inspected.",
    ]
    if orbit_mismatches:
        notes.append(
            "At least one granule has CMR ORBIT_TYPE that does not match the "
            "filename orbit-fidelity letter defined in the ASF naming convention. "
            "Both values are kept. See filename_metadata_agreement."
        )
    if recommended is None:
        notes.append("No provisional D40 pair contained the study point.")
    else:
        notes.append(
            "The rank-1 D40 pair is a catalogue shortlist only and remains pending raster quality control."
        )
    return notes


def _filename_agreement(
    granule_ur: Any,
    attributes: Mapping[str, Any],
    identifier_map: Mapping[str, str],
    temporal: Mapping[str, Any],
) -> dict[str, Any]:
    parsed = FILENAME_RE.match(str(granule_ur or ""))
    if parsed is None:
        return {"parsed": False, "checks": []}
    fields = parsed.groupdict()
    primary_code = fields["polarization"][:2]
    expected_pol = POLARIZATION_CODES.get(primary_code)
    actual_pol = frozenset(attributes.get("FREQUENCY_A_POLARIZATION") or [])
    checks = [
        _check("track", _as_int(_first(attributes.get("TRACK_NUMBER"))), int(fields["track"])),
        _check("frame", _as_int(_first(attributes.get("FRAME_NUMBER"))), int(fields["frame"])),
        _check(
            "orbit_direction",
            _first(attributes.get("ASCENDING_DESCENDING")),
            "ASCENDING" if fields["direction"] == "A" else "DESCENDING",
        ),
        _check(
            "frequency_a_bandwidth_mhz",
            _as_int(_first(attributes.get("FREQUENCY_A_RANGE_BANDWIDTH"))),
            int(fields["mode"][:2]),
        ),
        _check("frequency_a_polarizations", actual_pol, expected_pol),
        _check("crid", identifier_map.get("CRID"), fields["crid"]),
        _check(
            "acquisition_start",
            _time_token(temporal.get("BeginningDateTime")),
            fields["start"],
        ),
        _check(
            "acquisition_end",
            _time_token(temporal.get("EndingDateTime")),
            fields["end"],
        ),
        _check(
            "product_counter",
            _as_int(identifier_map.get("ProductCounter")),
            int(fields["counter"]),
        ),
        {
            "field": "orbit_fidelity_letter",
            "metadata": _first(attributes.get("ORBIT_TYPE")),
            "filename": fields["orbit_letter"],
            "filename_meaning": ORBIT_LETTER_MEANING.get(fields["orbit_letter"]),
            "match": _orbit_letter_matches(
                _first(attributes.get("ORBIT_TYPE")),
                fields["orbit_letter"],
            ),
        },
    ]
    return {
        "parsed": True,
        "match": all(check["match"] for check in checks),
        "checks": checks,
    }


def _orbit_letter_matches(orbit_type: Any, letter: str) -> bool:
    normalized = str(orbit_type or "").upper()
    if letter == "M":
        return normalized in {"MOE", "MEDIUM", "M"}
    if letter == "P":
        return normalized in {"POE", "PRECISE", "P"}
    if letter == "N":
        return normalized in {"NRT", "NEAR_REAL_TIME", "NEAR-REAL-TIME", "N"}
    if letter == "F":
        return normalized in {"FORECAST", "PREDICTED", "F"}
    return False


def _check(field: str, metadata: Any, filename: Any) -> dict[str, Any]:
    left = _jsonable(metadata)
    right = _jsonable(filename)
    return {"field": field, "metadata": left, "filename": right, "match": left == right}


def _jsonable(value: Any) -> Any:
    if isinstance(value, frozenset):
        return sorted(value)
    return value


def _identifiers(entries: Iterable[Mapping[str, Any]]) -> dict[str, str]:
    found: dict[str, str] = {}
    for entry in entries:
        if entry.get("IdentifierType") == "Other" and entry.get("IdentifierName"):
            found[str(entry["IdentifierName"])] = str(entry.get("Identifier"))
        elif entry.get("IdentifierType"):
            found[str(entry["IdentifierType"])] = str(entry.get("Identifier"))
    return found


def _polygons(umm: Mapping[str, Any]) -> list[dict[str, Any]]:
    geometry = (
        (umm.get("SpatialExtent") or {}).get("HorizontalSpatialDomain") or {}
    ).get("Geometry") or {}
    polygons = []
    for polygon in geometry.get("GPolygons") or []:
        boundary = polygon.get("Boundary") or {}
        exterior = [
            (point["Longitude"], point["Latitude"])
            for point in (boundary.get("Points") or [])
        ]
        holes = []
        exclusive = polygon.get("ExclusiveZone") or {}
        for hole in exclusive.get("Boundaries") or []:
            holes.append(
                [
                    (point["Longitude"], point["Latitude"])
                    for point in (hole.get("Points") or [])
                ]
            )
        polygons.append({"exterior": exterior, "holes": holes})
    return polygons


def _first(values: Any) -> Any:
    if isinstance(values, list):
        return values[0] if values else None
    return values


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _time_token(value: Any) -> str | None:
    if not value:
        return None
    parsed = _parse_time(str(value))
    return parsed.strftime("%Y%m%dT%H%M%S")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="data/manifests/nisar_kuwari_catalogue.json",
        help="Path for the catalogue manifest.",
    )
    args = parser.parse_args()
    try:
        manifest = write_manifest(args.output)
    except Exception as exc:
        raise SystemExit(f"CMR catalogue audit failed: {exc}") from exc
    print(
        json.dumps(
            {
                "output": args.output,
                "retrieval_timestamp": manifest["retrieval_timestamp"],
                "result_counts": manifest["result_counts"],
                "d40": manifest["group_d40"]["selected_granule_urs"],
                "validated_same_mode": manifest["validated_p05036_same_mode"][
                    "selected_granule_urs"
                ],
                "recommended_pair": manifest["recommended_pair"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
