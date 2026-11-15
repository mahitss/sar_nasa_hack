import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import rasterio

@dataclass
class RasterMetadata:
    path: str
    crs: str
    width: int
    height: int
    bands: int
    dtype: str
    nodata: Any
    transform: list

def inspect_raster(path: str) -> RasterMetadata:
    with rasterio.open(path) as src:
        return RasterMetadata(
            path=path,
            crs=str(src.crs),
            width=src.width,
            height=src.height,
            bands=src.count,
            dtype=str(src.dtypes[0]),
            nodata=src.nodata,
            transform=list(src.transform),
        )

def write_manifest(path: str, data: dict) -> None:
    Path(path).write_text(json.dumps(data, sort_keys=True, indent=2) + "\n")

def water_candidate_allowed(parameters: dict) -> bool:
    # Requires explicitly supplied, pre-registered parameters.
    required = {"threshold_db", "min_pixels", "max_pixels", "approved_by", "approved_at"}
    if not required.issubset(parameters.keys()):
        return False
    if not parameters.get("approved_by"):
        return False
    if not parameters.get("approved_at"):
        return False
    return True
