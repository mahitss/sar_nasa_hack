import signal
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .client import WorkerClient, WorkerAPIError
from .manifest import build_result_manifest
from .tasks import execute_task

class WorkerRunner:
    """Orchestrates job claiming, leasing, execution, and completion."""

    def __init__(self, client: WorkerClient, heartbeat_interval: float = 30.0):
        self.client = client
        self.heartbeat_interval = heartbeat_interval
        self._stop_requested = False

    def request_stop(self):
        self._stop_requested = True

    def run_once(self) -> Optional[dict[str, Any]]:
        """Claim and execute a single job if available."""
        job = self.client.claim_job()
        if not job:
            return None

        job_id = job.get("id")
        lease_token = job.get("lease_token")
        attempt_id = job.get("attempt_id", "")
        job_type = job.get("job_type", "")
        payload = job.get("payload", {})

        if not job_id or not lease_token:
            return None

        # Transition to running
        self.client.start_job(job_id, lease_token)
        started_at = datetime.now(timezone.utc)

        # Background heartbeat thread
        stop_hb = threading.Event()

        def heartbeat_loop():
            while not stop_hb.wait(self.heartbeat_interval):
                try:
                    self.client.heartbeat(job_id, lease_token, extend_seconds=180)
                except Exception:
                    break

        hb_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        hb_thread.start()

        try:
            with tempfile.TemporaryDirectory(prefix=f"rivet-job-{job_id}-") as ws_dir:
                task_summary = execute_task(job_type, payload, ws_dir)
                finished_at = datetime.now(timezone.utc)

                stop_hb.set()
                hb_thread.join(timeout=2.0)

                inputs_list = []
                if "sha256" in task_summary:
                    inputs_list.append({"source": task_summary.get("path", "input"), "sha256": task_summary["sha256"]})
                elif "source_sha256" in task_summary:
                    inputs_list.append({"source": payload.get("input_path", "input"), "sha256": task_summary["source_sha256"]})

                outputs_list = []
                if "manifest_file" in task_summary:
                    outputs_list.append({"path": task_summary["manifest_file"], "sha256": task_summary.get("manifest_sha256", ""), "type": "manifest"})

                manifest = build_result_manifest(
                    job_id=job_id,
                    attempt_id=attempt_id,
                    worker_id=self.client.signer.worker_id,
                    task_type=job_type,
                    started_at=started_at,
                    finished_at=finished_at,
                    task_summary=task_summary,
                    inputs=inputs_list,
                    outputs=outputs_list,
                    status="succeeded",
                )

                completed_job = self.client.complete_job(job_id, lease_token, manifest)
                return completed_job

        except Exception as e:
            stop_hb.set()
            hb_thread.join(timeout=2.0)
            err_msg = str(e)
            try:
                self.client.fail_job(job_id, lease_token, err_msg)
            except Exception:
                pass
            raise

    def poll(self, interval: float = 5.0, max_jobs: int = 0) -> int:
        """Poll the queue continuously until stopped or max_jobs processed."""
        processed_count = 0

        def handle_signal(sig, frame):
            self.request_stop()

        old_sigint = signal.signal(signal.SIGINT, handle_signal)
        old_sigterm = signal.signal(signal.SIGTERM, handle_signal)

        try:
            while not self._stop_requested:
                try:
                    job = self.run_once()
                    if job:
                        processed_count += 1
                        if max_jobs > 0 and processed_count >= max_jobs:
                            break
                        continue
                except Exception as e:
                    time.sleep(interval)

                time.sleep(interval)
        finally:
            signal.signal(signal.SIGINT, old_sigint)
            signal.signal(signal.SIGTERM, old_sigterm)

        return processed_count
