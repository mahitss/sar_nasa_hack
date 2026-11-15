-- name: SubmitEvidenceDecision :one
SELECT public.submit_evidence_decision($1, $2, $3, $4) AS decision_id;

-- name: GetDecision :one
SELECT id, incident_id, evidence_record_id, reviewer_id, decision, rationale, created_at
FROM public.decisions
WHERE id = $1;

-- name: ListDecisionsForEvidence :many
SELECT id, incident_id, evidence_record_id, reviewer_id, decision, rationale, created_at
FROM public.decisions
WHERE incident_id = $1 AND evidence_record_id = $2
ORDER BY created_at DESC;
