-- name: ListAuditEvents :many
SELECT id, actor_id, action, entity_table, entity_id, incident_id, before_data, after_data, occurred_at
FROM public.audit_events
WHERE incident_id = $1
ORDER BY occurred_at DESC;
