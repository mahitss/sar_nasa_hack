import json
from typing import Any, Optional
import requests

from .signer import WorkerSigner

class WorkerAPIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Worker API error {status_code}: {message}")

class WorkerClient:
    """Client for authenticated Go Worker API."""

    def __init__(self, base_url: str, signer: WorkerSigner, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.signer = signer
        self.timeout = timeout
        self.session = requests.Session()

    def _request(self, method: str, path: str, json_data: Optional[dict] = None) -> dict:
        url = f"{self.base_url}{path}"
        body_bytes = json.dumps(json_data).encode("utf-8") if json_data is not None else b"{}"

        headers = self.signer.sign_request(method, path, body_bytes)
        headers["Content-Type"] = "application/json"

        resp = self.session.request(
            method=method,
            url=url,
            data=body_bytes,
            headers=headers,
            timeout=self.timeout,
        )

        if resp.status_code >= 400:
            err_msg = resp.text
            try:
                err_json = resp.json()
                if "error" in err_json:
                    err_msg = err_json["error"]
            except Exception:
                pass
            raise WorkerAPIError(resp.status_code, err_msg)

        if resp.status_code == 204 or not resp.content:
            return {}

        return resp.json()

    def claim_job(self) -> Optional[dict]:
        data = self._request("POST", "/internal/v1/worker/jobs/claim", {})
        return data.get("job")

    def start_job(self, job_id: str, lease_token: str) -> dict:
        data = self._request("POST", f"/internal/v1/worker/jobs/{job_id}/start", {
            "lease_token": lease_token,
        })
        return data.get("job", {})

    def heartbeat(self, job_id: str, lease_token: str, extend_seconds: int = 300) -> dict:
        data = self._request("POST", f"/internal/v1/worker/jobs/{job_id}/heartbeat", {
            "lease_token": lease_token,
            "extend_seconds": extend_seconds,
        })
        return data.get("job", {})

    def complete_job(self, job_id: str, lease_token: str, manifest: dict) -> dict:
        data = self._request("POST", f"/internal/v1/worker/jobs/{job_id}/complete", {
            "lease_token": lease_token,
            "manifest": manifest,
        })
        return data.get("job", {})

    def fail_job(self, job_id: str, lease_token: str, error_message: str) -> dict:
        data = self._request("POST", f"/internal/v1/worker/jobs/{job_id}/fail", {
            "lease_token": lease_token,
            "error_message": error_message,
        })
        return data.get("job", {})

    def recover_leases(self) -> int:
        data = self._request("POST", "/internal/v1/worker/leases/recover", {})
        return data.get("recovered_count", 0)
