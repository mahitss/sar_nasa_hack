import platform
import sys
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
import rasterio

def build_result_manifest(
    job_id: str,
    attempt_id: str,
    worker_id: str,
    task_type: str,
    started_at: datetime,
    finished_at: datetime,
    task_summary: dict[str, Any],
    inputs: Optional[list[dict[str, Any]]] = None,
    outputs: Optional[list[dict[str, Any]]] = None,
    status: str = "succeeded",
) -> dict[str, Any]:
    """Constructs a versioned, auditable scientific result manifest."""
    return {
        "schema_version": "1.0",
        "job_id": job_id,
        "attempt_id": attempt_id,
        "worker_id": worker_id,
        "task_type": task_type,
        "status": status,
        "started_at": started_at.astimezone(timezone.utc).isoformat(),
        "finished_at": finished_at.astimezone(timezone.utc).isoformat(),
        "inputs": inputs or [],
        "outputs": outputs or [],
        "tool_versions": {
            "worker": "0.1.0",
            "rasterio": rasterio.__version__,
            "numpy": np.__version__,
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "summary": task_summary,
    }
