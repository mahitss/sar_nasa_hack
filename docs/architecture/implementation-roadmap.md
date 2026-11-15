# RIVET implementation roadmap

This roadmap sequences the remaining implementation work. Each phase lists dependencies, acceptance criteria, test requirements, and risks.

## Phase A — Database and identity

Dependencies: none (foundational).

Scope:
- Supabase Auth.
- Supabase PostgreSQL and PostGIS.
- Profiles, user roles, incidents, incident memberships.
- Acquisitions, evidence records, processing jobs, decisions, reports.
- Append-only audit events.
- Database migrations.
- RLS policies for every application table.

Acceptance criteria:
- Migrations apply cleanly to a fresh Supabase database.
- Every application table has RLS enabled.
- A user cannot read or write another user's incident data.
- Roles are derived from database tables, not editable user metadata.

Test requirements:
- Migration up/down tests.
- RLS isolation tests for each table.

Risks:
- Incorrect RLS policies could expose cross-tenant data.
- Supabase project creation requires founder approval.

## Phase B — Go API

Dependencies: Phase A.

Scope:
- Go 1.25 module.
- Chi router, pgx, sqlc, golang-migrate, OpenAPI.
- Health and readiness endpoints.
- JWT verification through Supabase JWKS.
- Transaction-local verified identity.
- `SET LOCAL ROLE authenticated`.
- Explicit authorization and membership checks.
- Structured errors and audit logging.

Acceptance criteria:
- `/healthz` and `/readyz` respond correctly.
- Protected endpoints reject unauthenticated requests.
- Authorization is enforced in Go, not only in RLS.
- Every protected request creates an audit event.

Test requirements:
- Go unit tests for handlers and authorization.
- Integration tests against a real Supabase database.

Risks:
- JWT verification mistakes could bypass authorization.
- Transaction-local role setup must be exact.

## Phase C — Python scientific worker

Dependencies: Phase A (job queue tables), Phase B (job creation API).

Scope:
- Python 3.12.13.
- GDAL, Rasterio, GeoPandas, Shapely, PyProj.
- NumPy, SciPy, Xarray, rioxarray.
- Job claiming and lifecycle.
- Allowlisted Earthdata/ASF access.
- Source checksums.
- Reproducible processing manifests.
- Deterministic output artifacts.
- Failure, retry, and audit handling.

Acceptance criteria:
- Worker claims a job, processes it, and records a manifest.
- Missing input files or thresholds cause a documented failure, not a fabricated result.
- Re-running a job produces identical outputs and checksums.

Test requirements:
- Python unit tests.
- Scientific tests against committed manifests.
- Checksum verification.

Risks:
- Missing real inputs could lead to fabricated results if not guarded.
- Operational thresholds for Mission 006 remain unresolved.

## Phase D — Frontend integration

Dependencies: Phase B (API), Phase A (auth).

Scope:
- Supabase SSR authentication.
- API client with session handling.
- Real incident and evidence data.
- Acquisition browsing.
- Processing job status.
- Human review workflow.
- Decision history.
- Report generation.
- Empty, error, and loading states.
- Responsive design and accessibility.

Acceptance criteria:
- Authenticated users can log in and view their incidents.
- Review decisions persist to the backend.
- Reports are generated from persisted evidence.
- All controls are functional.

Test requirements:
- Component tests.
- Playwright E2E tests.

Risks:
- Frontend could drift from API contracts without OpenAPI generation.

## Phase E — Scientific vertical slice

Dependencies: Phase C (worker), Phase D (frontend review), Phase A/B (persistence).

Scope (first approved slice only):
- Group D40, track 5, frame 73, descending, Frequency A 40 MHz, HH+HV, provisional CRID P05023.
- Two acquisitions: 6 September and 30 September 2026.
- GCOV input layers and valid-samples mask.
- GSLC native-grid validity-mask QA as a separate companion record.
- Water-candidate experiment only.
- Human review.
- Traceable report.

Acceptance criteria:
- One measurement from two acquisitions is stored with full provenance.
- GSLC mask is not treated as water, shadow, or layover.
- No confirmed water detection is claimed.
- P05023 is labeled provisional on every record.
- Report traces to evidence and decision ids.

Test requirements:
- Scientific tests verifying counts match manifests.
- Provenance completeness checks.

Risks:
- Mission 006 has zero filtered sweep-stable candidates; thresholds unresolved.
- Filename-N vs MOE/Custom mismatch remains unresolved.

## Phase F — Verification and release

Dependencies: Phases A-E.

Scope:
- Go unit and integration tests.
- Python unit and scientific tests.
- Frontend component tests.
- Playwright E2E tests.
- API authorization tests.
- RLS isolation tests.
- Security review.
- CI workflows.
- Deployment build verification.
- Operational runbook.
- Reproducible local setup.

Acceptance criteria:
- All tests pass in CI.
- Security review has no critical findings.
- Local setup documented and reproducible.
- Deployment build succeeds in Vercel with Root Directory set to `apps/web`.

Test requirements:
- Full test suite in CI.

Risks:
- Windows symlink limitations may affect local Vercel builds; use CI (Linux) for deployment verification.
