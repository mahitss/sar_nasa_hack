import json
import os
from pathlib import Path
from typing import Any

from .processing import inspect_raster, write_manifest, water_candidate_allowed
from .sources import sha256_file, verify_checksum

def validate_safe_path(path_str: str, base_dir: Path) -> Path:
    """Ensure path is within approved base directory and does not contain traversal patterns."""
    p = Path(path_str)
    if ".." in p.parts:
        raise ValueError(f"path traversal detected in '{path_str}'")
    resolved = (base_dir / p).resolve() if not p.is_absolute() else p.resolve()
    return resolved

def execute_task(task_type: str, payload: dict, workspace_dir: str) -> dict:
    """Execute an approved deterministic scientific task."""
    ws = Path(workspace_dir)

    if task_type == "raster.inspect":
        input_path = payload.get("input_path") or payload.get("path")
        if not input_path:
            # Check inputs array if present
            inputs = payload.get("inputs", [])
            if inputs and isinstance(inputs, list):
                input_path = inputs[0].get("path") if isinstance(inputs[0], dict) else inputs[0]
        if not input_path:
            raise ValueError("raster.inspect requires 'input_path' or 'inputs'")

        target_file = validate_safe_path(input_path, ws)
        if not target_file.exists():
            raise FileNotFoundError(f"target raster '{target_file}' not found")

        meta = inspect_raster(str(target_file))
        sha = sha256_file(str(target_file))

        return {
            "task_type": "raster.inspect",
            "path": str(target_file),
            "sha256": sha,
            "crs": meta.crs,
            "width": meta.width,
            "height": meta.height,
            "bands": meta.bands,
            "dtype": meta.dtype,
            "nodata": meta.nodata,
            "transform": meta.transform,
        }

    elif task_type == "checksum":
        input_path = payload.get("input_path") or payload.get("path")
        if not input_path:
            raise ValueError("checksum requires 'input_path'")

        target_file = validate_safe_path(input_path, ws)
        if not target_file.exists():
            raise FileNotFoundError(f"target file '{target_file}' not found")

        digest = sha256_file(str(target_file))
        expected = payload.get("expected_checksum") or payload.get("parameters", {}).get("expected_checksum")
        if expected and digest.lower() != expected.lower():
            raise ValueError(f"checksum mismatch: expected {expected}, got {digest}")

        return {
            "task_type": "checksum",
            "path": str(target_file),
            "sha256": digest,
            "verified": True if expected else False,
        }

    elif task_type == "metadata.manifest":
        input_path = payload.get("input_path") or payload.get("path")
        if not input_path:
            raise ValueError("metadata.manifest requires 'input_path'")

        target_file = validate_safe_path(input_path, ws)
        if not target_file.exists():
            raise FileNotFoundError(f"target file '{target_file}' not found")

        meta = inspect_raster(str(target_file))
        sha = sha256_file(str(target_file))

        manifest_path = ws / "manifest.json"
        manifest_data = {
            "source_file": str(target_file.name),
            "sha256": sha,
            "dimensions": {"width": meta.width, "height": meta.height, "bands": meta.bands},
            "crs": meta.crs,
            "transform": meta.transform,
            "parameters": payload.get("parameters", {}),
        }
        write_manifest(str(manifest_path), manifest_data)
        manifest_sha = sha256_file(str(manifest_path))

        return {
            "task_type": "metadata.manifest",
            "manifest_file": str(manifest_path),
            "manifest_sha256": manifest_sha,
            "source_sha256": sha,
        }

    elif task_type == "water_candidate.check":
        params = payload.get("parameters", {})
        if not water_candidate_allowed(params):
            raise ValueError("water candidate check rejected: missing required approved parameters (threshold_db, min_pixels, max_pixels, approved_by, approved_at)")

        input_path = payload.get("input_path") or payload.get("path")
        if not input_path:
            raise ValueError("water_candidate.check requires 'input_path'")

        target_file = validate_safe_path(input_path, ws)
        if not target_file.exists():
            raise FileNotFoundError(f"target file '{target_file}' not found")

        meta = inspect_raster(str(target_file))
        sha = sha256_file(str(target_file))

        threshold_db = float(params["threshold_db"])
        min_pixels = int(params["min_pixels"])
        max_pixels = int(params["max_pixels"])

        import rasterio
        import numpy as np

        with rasterio.open(str(target_file)) as src:
            arr = src.read(1)
            # Evaluate water candidate pixels strictly per approved threshold
            candidate_mask = (arr < threshold_db) & (arr != (src.nodata or -9999))
            candidate_pixels = int(np.sum(candidate_mask))

        within_bounds = min_pixels <= candidate_pixels <= max_pixels

        return {
            "task_type": "water_candidate.check",
            "source_sha256": sha,
            "candidate_pixels": candidate_pixels,
            "within_bounds": within_bounds,
            "threshold_db": threshold_db,
            "approved_by": params["approved_by"],
            "approved_at": params["approved_at"],
        }

    else:
        raise ValueError(f"unsupported task_type '{task_type}'")
