-- name: ListEvidence :many
SELECT id, incident_id, acquisition_id, claim_level, evidence_kind, source_mission, title, summary, details, source_path, limitations, processing_version, code_version, parameters, source_checksums, measurement_unit, review_state, created_by, created_at, updated_at
FROM public.evidence_records
WHERE incident_id = $1
ORDER BY created_at ASC;

-- name: GetEvidence :one
SELECT id, incident_id, acquisition_id, claim_level, evidence_kind, source_mission, title, summary, details, source_path, limitations, processing_version, code_version, parameters, source_checksums, measurement_unit, review_state, created_by, created_at, updated_at
FROM public.evidence_records
WHERE incident_id = $1 AND id = $2;

-- name: CreateEvidence :one
INSERT INTO public.evidence_records (
  id, incident_id, acquisition_id, claim_level, evidence_kind, title, summary, source_path, created_by
)
VALUES ($1, $2, $3, sqlc.arg('claim_level')::claim_level, sqlc.arg('evidence_kind')::evidence_kind, $4, $5, $6, $7)
RETURNING id, incident_id, acquisition_id, claim_level, evidence_kind, source_mission, title, summary, details, source_path, limitations, processing_version, code_version, parameters, source_checksums, measurement_unit, review_state, created_by, created_at, updated_at;

-- name: PatchEvidence :one
UPDATE public.evidence_records
SET title = COALESCE(NULLIF(sqlc.arg('title')::text, ''), title),
    summary = COALESCE(NULLIF(sqlc.arg('summary')::text, ''), summary)
WHERE incident_id = $1 AND id = $2
RETURNING id, incident_id, acquisition_id, claim_level, evidence_kind, source_mission, title, summary, details, source_path, limitations, processing_version, code_version, parameters, source_checksums, measurement_unit, review_state, created_by, created_at, updated_at;
