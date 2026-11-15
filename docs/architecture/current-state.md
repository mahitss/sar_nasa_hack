# RIVET current implementation state

Date: 2026-11-15
Branch: `rebuild/submission-mvp`

## Existing

- Next.js 16 / React 19 / TypeScript prototype in `apps/web` (5 routes).
- Go API foundation in `services/api` (health, ready, whoami, incidents, acquisitions, evidence, decisions, jobs, reports).
- JWT verification via JWKS; transaction wrapper with transaction-local identity.
- Python worker foundation in `services/worker` (CLI, job model, source allowlist, checksums, raster inspection, water-candidate guard).
- Supabase migrations (4 files) with RLS, grants, audit, job state machine.
- pgTAP tests (6 files, 41 assertions) — unverified (Docker unavailable).
- Scientific audit tools and committed manifests.
- CI workflows (frontend, go, python, db).

## Not yet implemented

- Full Supabase runtime verification (Docker blocker).
- Go API database integration (pgx repository) — in-memory store used for now.
- sqlc generated code.
- Supabase SSR frontend auth.
- End-to-end integration tests.

## Verified commands

- Go: `go build ./...`, `go vet ./...`, `go test ./...` pass.
- Python: `uv run pytest` (11 passed).
- Scientific: 128 passed.
- Frontend: lint/typecheck/build pass.

## Unresolved scientific blockers

- Filename N vs MOE/Custom mismatch.
- Mission 006 zero filtered candidates; thresholds unapproved.
- No validated shadow/layover model.
- P05023 provisional.
- Local DEM not processor DEM.
