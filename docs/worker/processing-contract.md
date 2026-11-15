# Worker Processing Contract and Security Boundary

## Overview

The processing worker executes compute-intensive geospatial algorithms (SAR backscatter analysis, native-grid validity masking, thresholding, and provenance-checked candidate detection). It must interact with the database strictly through an authorized, non-interactive service identity without inheriting arbitrary database administrator privileges.

## 1. Job Lifecycle and State Transitions

Jobs follow the strict state machine enforced by PostgreSQL trigger `private.enforce_job_transition()` on `public.processing_jobs`:

```
queued ──> claimed ──> running ──┬──> succeeded (terminal)
  │                               ├──> failed    (terminal)
  └──> cancelled                  └──> cancelled (terminal)
```

Transitions are strictly validated:
- `queued -> claimed`: Requires `claimed_by` and `claimed_at` to be populated.
- `claimed -> running`: Requires `started_at` to be populated.
- `running -> succeeded / failed / cancelled`: Terminal state requiring `finished_at` timestamp.
- Direct transition from `queued -> cancelled` allowed for aborting unstarted work.
- Arbitrary jumps (e.g. `queued -> succeeded`) raise exception `illegal processing_job transition`.

## 2. Worker Identity and Authentication

- The Python worker communicates with the backend exclusively via the internal Go Worker API (`/internal/v1/worker/...`). The Python worker NEVER connects directly to PostgreSQL and never receives database credentials, Supabase service-role keys, or user authentication tokens.
- Authentication uses Ed25519 cryptographic request signing with canonical headers:
  - `X-Worker-ID`: Verified worker identifier.
  - `X-Key-ID`: Registered key identifier for key rotation.
  - `X-Timestamp`: Epoch timestamp (verified within 5-minute clock skew).
  - `X-Nonce`: Unique per-request nonce (cached to prevent replay attacks).
  - `X-Signature`: Ed25519 signature over canonical string `METHOD\nPATH\nWORKER_ID\nKEY_ID\nTIMESTAMP\nNONCE\nBODY_SHA256`.
- The Go API verifies the cryptographic signature against its registered public key registry, enforces nonce uniqueness, and acts as the sole authorized executor of persistent state changes.
- Ordinary web users (`authenticated` role) have `SELECT` and `INSERT` permissions only; column grants strictly prevent ordinary users from modifying `state`, `claimed_by`, `claimed_at`, `started_at`, `finished_at`, `error_message`, `retry_count`, or lease tokens.

## 3. Job Claiming Protocol

Jobs are claimed atomically by the Go API using row-level locking with `FOR UPDATE SKIP LOCKED`:

```sql
WITH candidate AS (
  SELECT id
  FROM public.processing_jobs
  WHERE state = 'queued'
  ORDER BY created_at ASC
  LIMIT 1
  FOR UPDATE SKIP LOCKED
)
UPDATE public.processing_jobs j
SET state = 'claimed',
    claimed_by = $1,
    claimed_at = now(),
    lease_token = $2,
    lease_expires_at = $3,
    attempt_id = $4,
    retry_count = retry_count + 1,
    updated_at = now()
FROM candidate
WHERE j.id = candidate.id
RETURNING j.id, j.incident_id, j.job_type, j.state, j.claimed_by, j.claimed_at, j.started_at, j.finished_at, j.error_message, j.retry_count, j.idempotency_key, j.payload, j.lease_token, j.lease_expires_at, j.attempt_id, j.result, j.created_at, j.updated_at;
```

This prevents duplicate execution across multiple worker instances without distributed locking mechanisms.

## 4. Progress, Leases, and State Recording

- When work starts: Worker issues `POST /internal/v1/worker/jobs/{jobID}/start` with its active `lease_token`. Go transitions the job to `state = 'running'`, setting `started_at = now()`.
- Heartbeat / lease renewal: Worker periodically calls `POST /internal/v1/worker/jobs/{jobID}/heartbeat` with its `lease_token`. Go extends `lease_expires_at` and updates `updated_at = now()`.
- Completion: Upon successful processing, worker calls `POST /internal/v1/worker/jobs/{jobID}/complete` providing its `lease_token` and the versioned result manifest. Go validates the manifest, transitions the job to `state = 'succeeded'`, sets `finished_at = now()`, and stores the result in `processing_jobs.result`.
- Lease recovery: If a worker crashes or fails to heartbeat before `lease_expires_at`, `POST /internal/v1/worker/leases/recover` resets the job back to `state = 'queued'` (if `retry_count < max_retries`), or marks it `failed` if retries are exhausted. Stale workers attempting to complete after lease expiration are rejected with HTTP 403.

## 5. Retries and Failure Handling

- When an execution fails with an unrecoverable error, the job transitions to `state = 'failed'`, setting `error_message = $1` and `finished_at = now()`.
- Retries: Transient infrastructure failures (e.g., transient network timeout fetching granules) increment `retry_count`. If `retry_count < max_retries` (default 3), the job transitions back to `queued` with backoff; if exhausted, it transitions to `failed`.
- Sanitization: Error messages recorded in `error_message` are sanitized to avoid logging credentials, access tokens, or sensitive system paths.

## 6. Artifact Storage and Scientific Provenance

- Scientific outputs (GeoTIFFs, masks, intermediate rasters) are stored in configured content-addressable storage paths under `data/processed/` or authorized Supabase storage buckets.
- Manifest and provenance metadata: Every evidence record generated references:
  - Source granule identifiers and CRID (e.g. `P05023`).
  - Code version and Git commit hash.
  - Processing version.
  - Exact parameters used in calculation.
  - SHA-256 checksums of source products and output rasters.

## 7. Checksum Verification

Before processing any source raster or HDF5 product, the worker verifies its SHA-256 digest against the committed manifest in `data/manifests/`. If checksum verification fails, the job fails immediately with `checksum_mismatch`, halting execution before scientific evaluation.
