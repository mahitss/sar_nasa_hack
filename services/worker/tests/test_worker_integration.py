import hashlib
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from worker.client import WorkerClient, WorkerAPIError
from worker.manifest import build_result_manifest
from worker.runner import WorkerRunner
from worker.signer import WorkerSigner, DEFAULT_DEV_PUB_KEY
from worker.tasks import execute_task, validate_safe_path

@pytest.fixture
def sample_raster(tmp_path):
    raster_path = tmp_path / "sample.tif"
    arr = np.array([[-12.0, -18.0], [-20.0, -10.0]], dtype=np.float32)
    transform = from_origin(79.0, 30.0, 10.0, 10.0)
    with rasterio.open(
        str(raster_path),
        "w",
        driver="GTiff",
        height=2,
        width=2,
        count=1,
        dtype=arr.dtype,
        crs="EPSG:4326",
        transform=transform,
        nodata=-9999.0,
    ) as dst:
        dst.write(arr, 1)
    return str(raster_path)

# 1. Worker configuration validation
def test_worker_signer_config():
    signer = WorkerSigner.dev_default()
    assert signer.worker_id == "worker-local-1"
    assert signer.key_id == "key-local-1"
    assert signer.public_key_hex == DEFAULT_DEV_PUB_KEY

# 2. Worker signature generation
def test_worker_signature_generation():
    signer = WorkerSigner.dev_default()
    headers = signer.sign_request("POST", "/internal/v1/worker/jobs/claim", b"{}")
    assert headers["X-Worker-ID"] == "worker-local-1"
    assert headers["X-Key-ID"] == "key-local-1"
    assert "X-Timestamp" in headers
    assert "X-Nonce" in headers
    assert len(headers["X-Signature"]) == 128  # Ed25519 signature is 64 bytes = 128 hex chars

# 3. Request canonicalization
def test_request_canonicalization():
    signer = WorkerSigner.dev_default()
    canonical = signer.canonical_string("POST", "/test", 1700000000, "nonce1", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
    expected = "POST\n/test\nworker-local-1\nkey-local-1\n1700000000\nnonce1\ne3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert canonical == expected

# 4. Path traversal rejection
def test_path_traversal_rejection(tmp_path):
    with pytest.raises(ValueError, match="path traversal detected"):
        validate_safe_path("../../../etc/passwd", tmp_path)

# 5. Unsupported task rejection
def test_unsupported_task_rejection(tmp_path):
    with pytest.raises(ValueError, match="unsupported task_type"):
        execute_task("arbitrary.execute", {}, str(tmp_path))

# 6. Raster inspection task
def test_task_raster_inspect(sample_raster, tmp_path):
    res = execute_task("raster.inspect", {"input_path": sample_raster}, str(tmp_path))
    assert res["task_type"] == "raster.inspect"
    assert res["width"] == 2
    assert res["height"] == 2
    assert res["bands"] == 1
    assert "sha256" in res
    assert res["crs"] == "EPSG:4326"

# 7. Checksum generation and verification
def test_task_checksum(sample_raster, tmp_path):
    with open(sample_raster, "rb") as f:
        expected = hashlib.sha256(f.read()).hexdigest()

    res = execute_task("checksum", {"input_path": sample_raster, "expected_checksum": expected}, str(tmp_path))
    assert res["verified"] is True
    assert res["sha256"] == expected

# 8. Checksum mismatch handling
def test_task_checksum_mismatch(sample_raster, tmp_path):
    with pytest.raises(ValueError, match="checksum mismatch"):
        execute_task("checksum", {"input_path": sample_raster, "expected_checksum": "0000000000000000000000000000000000000000000000000000000000000000"}, str(tmp_path))

# 9. Manifest generation task
def test_task_metadata_manifest(sample_raster, tmp_path):
    res = execute_task("metadata.manifest", {"input_path": sample_raster}, str(tmp_path))
    assert res["task_type"] == "metadata.manifest"
    assert Path(res["manifest_file"]).exists()
    assert "manifest_sha256" in res

# 10. Water candidate check with approved parameters
def test_task_water_candidate_approved(sample_raster, tmp_path):
    payload = {
        "input_path": sample_raster,
        "parameters": {
            "threshold_db": -16.0,
            "min_pixels": 1,
            "max_pixels": 10,
            "approved_by": "analyst-1",
            "approved_at": "2026-11-15T00:00:00Z",
        },
    }
    res = execute_task("water_candidate.check", payload, str(tmp_path))
    assert res["task_type"] == "water_candidate.check"
    assert res["candidate_pixels"] == 2  # -18.0 and -20.0 are < -16.0
    assert res["within_bounds"] is True
    assert res["approved_by"] == "analyst-1"

# 11. Water candidate check without approved parameters is rejected
def test_task_water_candidate_unapproved_rejected(sample_raster, tmp_path):
    payload = {
        "input_path": sample_raster,
        "parameters": {
            "threshold_db": -16.0,
        },
    }
    with pytest.raises(ValueError, match="missing required approved parameters"):
        execute_task("water_candidate.check", payload, str(tmp_path))

# 12. Result manifest schema versioning
def test_build_result_manifest_schema():
    from datetime import datetime, timezone
    t0 = datetime.now(timezone.utc)
    t1 = datetime.now(timezone.utc)
    manifest = build_result_manifest(
        job_id="job-1",
        attempt_id="att-1",
        worker_id="worker-1",
        task_type="raster.inspect",
        started_at=t0,
        finished_at=t1,
        task_summary={"bands": 1},
    )
    assert manifest["schema_version"] == "1.0"
    assert manifest["status"] == "succeeded"
    assert manifest["tool_versions"]["worker"] == "0.1.0"
    assert "rasterio" in manifest["tool_versions"]
    assert "numpy" in manifest["tool_versions"]

# 13. Runner run_once executes task, writes manifest, and completes job
def test_runner_run_once_success(sample_raster):
    client = MagicMock()
    client.signer = WorkerSigner.dev_default()
    client.claim_job.return_value = {
        "id": "11111111-1111-1111-1111-111111111111",
        "lease_token": "token-xyz",
        "attempt_id": "att-xyz",
        "job_type": "raster.inspect",
        "payload": {"input_path": sample_raster},
    }
    client.complete_job.return_value = {"id": "11111111-1111-1111-1111-111111111111", "state": "succeeded"}

    runner = WorkerRunner(client)
    res = runner.run_once()

    assert res["state"] == "succeeded"
    client.start_job.assert_called_once_with("11111111-1111-1111-1111-111111111111", "token-xyz")
    client.complete_job.assert_called_once()
    call_args = client.complete_job.call_args[0]
    assert call_args[0] == "11111111-1111-1111-1111-111111111111"
    assert call_args[1] == "token-xyz"
    assert call_args[2]["schema_version"] == "1.0"
    assert call_args[2]["status"] == "succeeded"

# 14. Runner reports failure to API on exception
def test_runner_run_once_reports_failure():
    client = MagicMock()
    client.signer = WorkerSigner.dev_default()
    client.claim_job.return_value = {
        "id": "22222222-2222-2222-2222-222222222222",
        "lease_token": "token-fail",
        "job_type": "checksum",
        "payload": {"input_path": "non_existent_file.tif"},
    }

    runner = WorkerRunner(client)
    with pytest.raises(FileNotFoundError):
        runner.run_once()

    client.fail_job.assert_called_once()
    fail_args = client.fail_job.call_args[0]
    assert fail_args[0] == "22222222-2222-2222-2222-222222222222"
    assert fail_args[1] == "token-fail"
    assert "not found" in fail_args[2]

# 15. Graceful shutdown on stop requested
def test_runner_graceful_stop():
    client = MagicMock()
    client.claim_job.return_value = None
    runner = WorkerRunner(client)
    runner.request_stop()
    count = runner.poll(interval=0.01, max_jobs=5)
    assert count == 0
