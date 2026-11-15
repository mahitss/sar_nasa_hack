-- name: ListIncidents :many
SELECT id, title, description, discovery_west, discovery_south, discovery_east, discovery_north, archived_at, created_by, created_at, updated_at
FROM public.incidents
ORDER BY created_at DESC;

-- name: GetIncident :one
SELECT id, title, description, discovery_west, discovery_south, discovery_east, discovery_north, archived_at, created_by, created_at, updated_at
FROM public.incidents
WHERE id = $1;

-- name: CreateIncident :one
INSERT INTO public.incidents (id, title, description, discovery_west, discovery_south, discovery_east, discovery_north, created_by)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
RETURNING id, title, description, discovery_west, discovery_south, discovery_east, discovery_north, archived_at, created_by, created_at, updated_at;

-- name: GetIncidentMemberRole :one
SELECT role
FROM public.incident_members
WHERE incident_id = $1 AND user_id = $2;

-- name: ListIncidentMembers :many
SELECT id, incident_id, user_id, role, created_at
FROM public.incident_members
WHERE incident_id = $1;

-- name: AddIncidentMember :one
INSERT INTO public.incident_members (incident_id, user_id, role)
VALUES ($1, $2, sqlc.arg('role')::incident_role)
RETURNING id, incident_id, user_id, role, created_at;
