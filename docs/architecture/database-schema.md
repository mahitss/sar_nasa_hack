# RIVET database schema (Mission 017.1 hardened)

Local Supabase/PostgreSQL schema. Migrations under `supabase/migrations/`.

## Tables

1. `profiles` — one row per `auth.users` user (display name only; no privilege column).
2. `user_roles` — global application privileges; not client-writable.
3. `incidents` — investigation cases with discovery bounding box and soft-archive timestamp.
4. `incident_members` — membership and incident-scoped role.
5. `acquisitions` — NISAR acquisition metadata with provenance and cross-incident FK.
6. `evidence_records` — evidence ledger entries with claim level, kind, source, provenance, review state.
7. `processing_jobs` — job lifecycle with state machine.
8. `decisions` — reviewer accept/reject/needs-investigation (append-only).
9. `reports` — generated report content (JSONB).
10. `audit_events` — append-only audit trail with allowlisted snapshots.

## Roles

Incident roles: `owner`, `analyst`, `reviewer`, `viewer`.
Global roles: `platform_admin` (in `user_roles`).

## Processing job states

`queued -> claimed -> running -> succeeded | failed | cancelled`.

## Incident ownership

Owner membership is created automatically by trigger on incident insert. Last-owner removal/demotion is blocked.

## Cross-incident integrity

Composite foreign keys tie `evidence_records.acquisition_id` and `decisions.evidence_record_id` to the same incident. Nullable acquisition references preserved. Deletion semantics: restrict (preserve provenance).

## Audit

Allowlisted snapshots only. `audit_events.incident_id` uses ON DELETE RESTRICT. Null-incident audit rows are not visible to ordinary users.

## Unused enum removed

`evidence_status` enum dropped; `review_state` is the single status model for evidence.
