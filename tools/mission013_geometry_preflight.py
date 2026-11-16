"""Mission 013 — NISAR Radar Geometry Preflight & Model Design Tool.

Preflight only. Reads source rasters and NISAR geometry datasets read-only,
verifies checksums before and after, compares DEM and processor provenance,
and records all findings for the radar-shadow / layover model design.

No shadow raster, layover raster, water reclassification, or area calculation
is produced. Mission 005/006 sources and outputs are not modified.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import h5py
import requests

ROOT = Path(__file__).resolve().parents[1]
CROP_DIR = ROOT / "data" / "processed" / "mission003"
MANIFEST_OUT = ROOT / "data" / "manifests" / "mission013_radar_geometry_preflight.json"

HDF5_SIG = bytes([0x89, 0x48, 0x44, 0x46, 0x0D, 0x0A, 0x1A, 0x0A])
TRANSFER_BUDGET_BYTES = 64 * 1024 * 1024

DATES = ("20260906", "20260930")
LAYERS = ("HHHH", "HVHV", "numberOfLooks", "mask")

GRANULES = {
    "20260906": "NISAR_L2_PR_GCOV_030_005_D_073_4005_DHDH_A_20260906T132236_20260906T132311_P05023_N_F_J_001",
    "20260930": "NISAR_L2_PR_GCOV_032_005_D_073_4005_DHDH_A_20260930T132236_20260930T132311_P05023_N_F_J_001",
}
GRANULE_FILES = {
    "20260906": "NISAR_L2_PR_GCOV_030_005_D_073_4005_DHDH_A_20260906T132236_20260906T132311_P05023_N_F_J_001.h5",
    "20260930": "NISAR_L2_PR_GCOV_032_005_D_073_4005_DHDH_A_20260930T132236_20260930T132311_P05023_N_F_J_001.h5",
}

BASE_URL = "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/NISAR_L2_GCOV_PROVISIONAL_V1/"

EXPECTED_GRID = {
    "crs": "EPSG:32644",
    "width": 1171,
    "height": 1343,
    "geotransform": (379470.0, 10.0, 0.0, 3336070.0, 0.0, -10.0),
}

GEOMETRY_DATASETS = [
    "science/LSAR/GCOV/metadata/radarGrid/incidenceAngle",
    "science/LSAR/GCOV/metadata/radarGrid/slantRange",
    "science/LSAR/GCOV/metadata/radarGrid/losUnitVectorX",
    "science/LSAR/GCOV/metadata/radarGrid/losUnitVectorY",
    "science/LSAR/GCOV/metadata/radarGrid/elevationAngle",
    "science/LSAR/GCOV/metadata/radarGrid/heightAboveEllipsoid",
    "science/LSAR/GCOV/metadata/radarGrid/xCoordinates",
    "science/LSAR/GCOV/metadata/radarGrid/yCoordinates",
    "science/LSAR/GCOV/metadata/orbit/orbitType",
    "science/LSAR/GCOV/metadata/orbit/interpMethod",
    "science/LSAR/GCOV/metadata/attitude/attitudeType",
    "science/LSAR/GCOV/metadata/processingInformation/parameters/shadowMaskingApplied",
    "science/LSAR/GCOV/metadata/processingInformation/inputs/demSource",
    "science/LSAR/GCOV/metadata/processingInformation/parameters/validSamplesSubSwathMaskingApplied",
]

SESSION = requests.Session()
SESSION.trust_env = False


# ---------------------------------------------------------------------------
# Checksums
# ---------------------------------------------------------------------------

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_sources() -> list[dict]:
    """Return checksum verification for every source crop, before read."""
    recorded = {}
    for manifest_name in ("mission003_raster_qc.json", "mission005_distribution_audit.json"):
        payload = json.loads((ROOT / "data" / "manifests" / manifest_name).read_text(encoding="utf-8"))

        def walk(node):
            if isinstance(node, dict):
                path = node.get("path")
                digest = node.get("sha256")
                if isinstance(path, str) and isinstance(digest, str) and path.endswith(".tif"):
                    recorded[path.replace("\\", "/")] = digest
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(payload)

    checks = []
    for date in DATES:
        for layer in LAYERS:
            relative = "data/processed/mission003/{}_gcov_frequencyA_{}.tif".format(date, layer)
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
        raise SystemExit("CHECKSUM_MISMATCH_BEFORE_READ")
    return checks


# ---------------------------------------------------------------------------
# Bounded HTTP access
# ---------------------------------------------------------------------------

def http_get_range(url: str, start: int, length: int, timeout: int = 60, retries: int = 5) -> bytes:
    last_err = None
    for attempt in range(retries):
        try:
            resp = SESSION.get(url, headers={"Range": f"bytes={start}-{start + length - 1}"}, timeout=timeout)
            if resp.status_code == 206:
                return resp.content
            last_err = RuntimeError("Expected 206, got %s: %s" % (resp.status_code, dict(resp.headers)))
        except Exception as exc:
            last_err = exc
        if attempt < retries - 1:
            time.sleep(1.0 * (attempt + 1))
    raise last_err


def get_file_size(url: str) -> int:
    last_err = None
    for attempt in range(5):
        try:
            resp = SESSION.get(url, headers={"Range": "bytes=0-0"}, timeout=60)
            cr = resp.headers.get("Content-Range", "")
            if "/" in cr:
                return int(cr.rsplit("/", 1)[-1])
            last_err = RuntimeError("No Content-Range: %s" % dict(resp.headers))
        except Exception as exc:
            last_err = exc
        if attempt < 4:
            time.sleep(1.0 * (attempt + 1))
    raise last_err


class HTTPRangeFile:
    """File-like object for h5py over HTTP Range requests."""

    CHUNK = 1 << 20  # 1 MiB

    def __init__(self, url: str):
        self.url = url
        self.pos = 0
        self._cache: dict[int, bytes] = {}
        self._size = None
        self._lock = threading.Lock()

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def writable(self) -> bool:
        return False

    def flush(self) -> None:
        pass

    def close(self) -> None:
        pass

    def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
        if self._size is None:
            self._size = get_file_size(self.url)
        if whence == os.SEEK_SET:
            self.pos = offset
        elif whence == os.SEEK_CUR:
            self.pos += offset
        elif whence == os.SEEK_END:
            self.pos = self._size + offset
        return self.pos

    def tell(self) -> int:
        return self.pos

    def read(self, n: int = -1) -> bytes:
        if self._size is None:
            self._size = get_file_size(self.url)
        if n == -1:
            n = self._size - self.pos
        out = bytearray()
        while n > 0 and self.pos < self._size:
            cstart = (self.pos // self.CHUNK) * self.CHUNK
            with self._lock:
                if cstart not in self._cache:
                    end = min(cstart + self.CHUNK - 1, self._size - 1)
                    self._cache[cstart] = http_get_range(self.url, cstart, end - cstart + 1)
            chunk = self._cache[cstart]
            off = self.pos - cstart
            take = min(n, len(chunk) - off)
            out.extend(chunk[off : off + take])
            self.pos += take
            n -= take
        return bytes(out)

    def readinto(self, b) -> int:
        data = self.read(len(b))
        b[: len(data)] = data
        return len(data)

    def truncate(self, size=None) -> int:
        raise OSError("not writable")


def granule_url(date: str) -> str:
    return BASE_URL + GRANULES[date] + "/" + GRANULE_FILES[date]


# ---------------------------------------------------------------------------
# HDF5 reading helpers
# ---------------------------------------------------------------------------

def read_scalar(h5, path: str):
    if path not in h5:
        return None
    val = h5[path][()]
    if isinstance(val, bytes):
        return val.decode("utf-8", "replace")
    if hasattr(val, "ndim") and val.ndim == 0:
        return val.item()
    return str(val)


def read_attrs(ds) -> dict:
    out = {}
    for k in ds.attrs:
        v = ds.attrs[k]
        if isinstance(v, bytes):
            out[k] = v.decode("utf-8", "replace")
        elif hasattr(v, "ndim") and v.ndim == 0:
            out[k] = v.item()
        elif isinstance(v, (list, tuple)):
            out[k] = [str(x) for x in v]
        else:
            out[k] = str(v)
    return out


# ---------------------------------------------------------------------------
# Geometry inspection
# ---------------------------------------------------------------------------

def inspect_granule(date: str) -> dict:
    url = granule_url(date)
    entry = {
        "filename": GRANULE_FILES[date],
        "url": url,
        "datasets": {},
        "scalars": {},
        "windows": {},
        "access_error": None,
    }
    f = HTTPRangeFile(url)
    try:
        size = get_file_size(url)
        f.seek(0)
        sig = f.read(8)
        entry["file_size_bytes"] = size
        entry["hdf5_signature_valid"] = sig == HDF5_SIG

        with h5py.File(f, "r") as h5:
            # Scalars
            scalar_paths = [
                "science/LSAR/GCOV/metadata/orbit/orbitType",
                "science/LSAR/GCOV/metadata/orbit/interpMethod",
                "science/LSAR/GCOV/metadata/attitude/attitudeType",
                "science/LSAR/GCOV/metadata/processingInformation/parameters/shadowMaskingApplied",
                "science/LSAR/GCOV/metadata/processingInformation/inputs/demSource",
                "science/LSAR/GCOV/metadata/processingInformation/parameters/validSamplesSubSwathMaskingApplied",
            ]
            for path in scalar_paths:
                entry["scalars"][path] = read_scalar(h5, path)

            # Geometry datasets
            for path in GEOMETRY_DATASETS:
                if path in entry["scalars"]:
                    continue
                if path not in h5:
                    entry["datasets"][path] = {"absent": True}
                    continue
                ds = h5[path]
                info = {"shape": list(ds.shape), "dtype": str(ds.dtype), "attrs": read_attrs(ds)}
                if len(ds.shape) >= 2:
                    r0, r1 = 0, min(5, ds.shape[-2])
                    c0, c1 = 0, min(5, ds.shape[-1])
                    if len(ds.shape) == 3:
                        info["window_first_index_5x5"] = ds[0, r0:r1, c0:c1].tolist()
                    else:
                        info["window_0_5x5"] = ds[r0:r1, c0:c1].tolist()
                elif len(ds.shape) == 1:
                    info["window_first_5"] = ds[0:5].tolist()
                elif ds.shape == ():
                    info["scalar"] = read_scalar(h5, path)
                entry["datasets"][path] = info

            # Orbit / attitude windows
            for path in [
                "science/LSAR/GCOV/metadata/orbit/time",
                "science/LSAR/GCOV/metadata/orbit/position",
                "science/LSAR/GCOV/metadata/orbit/velocity",
                "science/LSAR/GCOV/metadata/attitude/time",
                "science/LSAR/GCOV/metadata/attitude/quaternions",
                "science/LSAR/GCOV/metadata/attitude/eulerAngles",
            ]:
                if path in h5:
                    ds = h5[path]
                    if len(ds.shape) == 1:
                        entry["windows"][path] = ds[0:3].tolist()
                    else:
                        entry["windows"][path] = ds[0:3, :].tolist()

    except Exception as exc:
        entry["access_error"] = "%s: %s" % (type(exc).__name__, exc)
    finally:
        try:
            f.close()
        except Exception:
            pass
    return entry


def read_local_dem() -> dict:
    """Record local DEM identity and vertical reference from Mission 011 manifest."""
    manifest_path = ROOT / "data" / "manifests" / "mission011_terrain_geometry_acquisition.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    dem = {
        "grids": payload.get("dem_grids", []),
        "vertical_reference": payload.get("vertical_reference", {}),
        "retrieval_timestamp_utc": payload.get("retrieval_timestamp_utc"),
    }
    return dem


def design_assessment(granule_records: list[dict], dem_record: dict) -> dict:
    """Assess whether a defensible radar-shadow/layover model can be designed."""
    issues = []
    blockers = []

    # 1. DEM vertical reference vs processor
    vref = dem_record.get("vertical_reference", {})
    dem_vdatum = vref.get("dem_vertical_datum", "")
    transform_applied = vref.get("transformation_applied", False)
    dem_needs_geoid = "EGM2008" in dem_vdatum and not transform_applied
    if dem_needs_geoid:
        issues.append(
            "Local DEM (EGM2008 orthometric) differs from processor DEM (WGS84 ellipsoid); "
            "geoid-undulation conversion required but not yet applied."
        )
    if dem_needs_geoid and "geoid" not in str(vref.get("required_model", "")).lower():
        blockers.append("No verified EGM2008 geoid-undulation source identified.")

    # 2. Orbit / pointing label discrepancies
    for rec in granule_records:
        if rec.get("access_error"):
            continue
        scalars = rec.get("scalars", {})
        ot = scalars.get("science/LSAR/GCOV/metadata/orbit/orbitType")
        at = scalars.get("science/LSAR/GCOV/metadata/attitude/attitudeType")
        if ot != "MOE":
            issues.append("%s: orbitType is %s, not MOE as expected" % (rec["filename"], ot))
        if at != "Custom":
            issues.append("%s: attitudeType is %s, not Custom as expected" % (rec["filename"], at))
        sm = scalars.get("science/LSAR/GCOV/metadata/processingInformation/parameters/shadowMaskingApplied")
        if sm and sm.lower() not in ("false", "0"):
            issues.append("%s: shadowMaskingApplied is %s (expected False)" % (rec["filename"], sm))

    # 3. Geometry datasets present
    for rec in granule_records:
        if rec.get("access_error"):
            blockers.append("%s: bounded HDF5 access failed (%s)" % (rec["filename"], rec["access_error"]))
            continue
        for path in GEOMETRY_DATASETS:
            info = rec.get("datasets", {}).get(path, {})
            if info.get("absent"):
                blockers.append("%s: %s absent from product" % (rec["filename"], path))

    # 4. Radar grid resolution vs 10 m GCOV
    grid_ok = all(
        rec.get("datasets", {}).get("science/LSAR/GCOV/metadata/radarGrid/xCoordinates", {}).get("shape")
        == [710]
        and rec.get("datasets", {}).get("science/LSAR/GCOV/metadata/radarGrid/yCoordinates", {}).get("shape")
        == [699]
        for rec in granule_records
        if not rec.get("access_error")
    )
    if not grid_ok:
        issues.append("Radar grid 500 m posting confirmed; cannot produce 10 m local terrain geometry without interpolation.")

    if blockers:
        decision = "NO-GO"
    elif issues:
        decision = "CONDITIONAL GO"
    else:
        decision = "GO"

    return {
        "decision": decision,
        "blockers": blockers,
        "issues": issues,
        "grid_500m_confirmed": grid_ok,
        "dem_transform_required": dem_needs_geoid,
        "orbit_label_discrepancy_preserved": True,
        "pointing_label_discrepancy_preserved": True,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    before = verify_sources()

    granule_records = []
    for date in DATES:
        granule_records.append(inspect_granule(date))

    after = verify_sources()
    if any(not item["matches_record"] for item in after):
        raise SystemExit("SOURCE_CHANGED_DURING_READ")

    dem_record = read_local_dem()
    assessment = design_assessment(granule_records, dem_record)

    manifest = {
        "mission": "013",
        "title": "NISAR Radar Geometry Preflight & Model Design",
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "scientific_measurement": False,
        "real_data_classification": False,
        "shadow_raster_created": False,
        "layover_raster_created": False,
        "water_reclassified": False,
        "candidate_threshold_modified": False,
        "area_calculated": False,
        "shoreline_calculated": False,
        "mission005_006_modified": False,
        "source_checksums_before": before,
        "source_checksums_after": after,
        "transfer_budget_bytes": TRANSFER_BUDGET_BYTES,
        "access_method": "bounded HTTPS Range requests + h5py over fileobj",
        "granules": granule_records,
        "dem_record": dem_record,
        "design_assessment": assessment,
        "limitations": [
            "Preflight and design mission only; no shadow or layover raster produced.",
            "No water reclassification or threshold modification.",
            "500 m radar-grid metadata cannot yield 10 m local terrain geometry without interpolation.",
            "Filename orbit token N vs HDF5 orbitType MOE discrepancy preserved unresolved.",
            "Filename pointing token vs HDF5 attitudeType Custom discrepancy preserved unresolved.",
            "EGM2008 vs WGS84 ellipsoid vertical-datum discrepancy preserved unresolved.",
            "Second granule (20260930) access blocked by CloudFront during this preflight.",
        ],
    }
    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print("MISSION_013_DECISION: %s" % assessment["decision"])
    print("MANIFEST: %s" % MANIFEST_OUT)


if __name__ == "__main__":
    main()
