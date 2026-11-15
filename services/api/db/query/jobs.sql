-- name: ListJobs :many
SELECT id, incident_id, job_type, state, claimed_by, claimed_at, started_at, finished_at, error_message, retry_count, idempotency_key, payload, lease_token, lease_expires_at, attempt_id, result, created_at, updated_at
FROM public.processing_jobs
WHERE incident_id = $1
ORDER BY created_at DESC;

-- name: GetJob :one
SELECT id, incident_id, job_type, state, claimed_by, claimed_at, started_at, finished_at, error_message, retry_count, idempotency_key, payload, lease_token, lease_expires_at, attempt_id, result, created_at, updated_at
FROM public.processing_jobs
WHERE incident_id = $1 AND id = $2;

-- name: GetJobByID :one
SELECT id, incident_id, job_type, state, claimed_by, claimed_at, started_at, finished_at, error_message, retry_count, idempotency_key, payload, lease_token, lease_expires_at, attempt_id, result, created_at, updated_at
FROM public.processing_jobs
WHERE id = $1;

-- name: CreateJob :one
INSERT INTO public.processing_jobs (
  id, incident_id, job_type, idempotency_key, payload
)
VALUES ($1, $2, $3, $4, $5)
RETURNING id, incident_id, job_type, state, claimed_by, claimed_at, started_at, finished_at, error_message, retry_count, idempotency_key, payload, lease_token, lease_expires_at, attempt_id, result, created_at, updated_at;

-- name: ClaimNextJob :one
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

-- name: StartJob :one
UPDATE public.processing_jobs
SET state = 'running',
    started_at = now(),
    updated_at = now()
WHERE id = $1 AND claimed_by = $2 AND state = 'claimed' AND lease_token = $3 AND lease_expires_at > now()
RETURNING id, incident_id, job_type, state, claimed_by, claimed_at, started_at, finished_at, error_message, retry_count, idempotency_key, payload, lease_token, lease_expires_at, attempt_id, result, created_at, updated_at;

-- name: HeartbeatJob :one
UPDATE public.processing_jobs
SET lease_expires_at = $3,
    updated_at = now()
WHERE id = $1 AND claimed_by = $2 AND state IN ('claimed', 'running') AND lease_token = $4 AND lease_expires_at > now()
RETURNING id, incident_id, job_type, state, claimed_by, claimed_at, started_at, finished_at, error_message, retry_count, idempotency_key, payload, lease_token, lease_expires_at, attempt_id, result, created_at, updated_at;

-- name: CompleteJob :one
UPDATE public.processing_jobs
SET state = 'succeeded',
    finished_at = now(),
    result = $4,
    updated_at = now()
WHERE id = $1 AND claimed_by = $2 AND state = 'running' AND lease_token = $3 AND lease_expires_at > now()
RETURNING id, incident_id, job_type, state, claimed_by, claimed_at, started_at, finished_at, error_message, retry_count, idempotency_key, payload, lease_token, lease_expires_at, attempt_id, result, created_at, updated_at;

-- name: FailJob :one
UPDATE public.processing_jobs
SET state = 'failed',
    started_at = COALESCE(started_at, now()),
    finished_at = now(),
    error_message = $4,
    updated_at = now()
WHERE id = $1 AND claimed_by = $2 AND state IN ('claimed', 'running') AND lease_token = $3
RETURNING id, incident_id, job_type, state, claimed_by, claimed_at, started_at, finished_at, error_message, retry_count, idempotency_key, payload, lease_token, lease_expires_at, attempt_id, result, created_at, updated_at;

-- name: RecoverExpiredLeasesToQueued :many
UPDATE public.processing_jobs
SET state = 'queued',
    claimed_by = null,
    claimed_at = null,
    started_at = null,
    lease_token = null,
    lease_expires_at = null,
    attempt_id = null,
    updated_at = now()
WHERE state IN ('claimed', 'running')
  AND lease_expires_at < now()
  AND retry_count < $1
RETURNING id, incident_id, job_type, state, claimed_by, claimed_at, started_at, finished_at, error_message, retry_count, idempotency_key, payload, lease_token, lease_expires_at, attempt_id, result, created_at, updated_at;

-- name: FailExhaustedExpiredLeases :many
UPDATE public.processing_jobs
SET state = 'failed',
    started_at = COALESCE(started_at, now()),
    finished_at = now(),
    error_message = 'lease expired and max retries exceeded',
    updated_at = now()
WHERE state IN ('claimed', 'running')
  AND lease_expires_at < now()
  AND retry_count >= $1
RETURNING id, incident_id, job_type, state, claimed_by, claimed_at, started_at, finished_at, error_message, retry_count, idempotency_key, payload, lease_token, lease_expires_at, attempt_id, result, created_at, updated_at;
