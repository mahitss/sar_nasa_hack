-- name: ListReports :many
SELECT id, incident_id, title, content, generated_by, created_at
FROM public.reports
WHERE incident_id = $1
ORDER BY created_at DESC;

-- name: GetReport :one
SELECT id, incident_id, title, content, generated_by, created_at
FROM public.reports
WHERE incident_id = $1 AND id = $2;

-- name: CreateReport :one
INSERT INTO public.reports (
  id, incident_id, title, content, generated_by
)
VALUES ($1, $2, $3, $4, $5)
RETURNING id, incident_id, title, content, generated_by, created_at;
