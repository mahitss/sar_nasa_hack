# Architecture overview

Status: approved for the repository foundation. Application code is not implemented.

## System

RIVET is one product with three code owners and one hosted data platform.

```text
Browser
  Next.js 16 (React 19, TypeScript, Tailwind CSS v4, shadcn/ui, MapLibre GL JS)
  Supabase SSR for the user session only
        |
        | user JWT
        v
Go API 1.25 (Chi, pgx, sqlc, golang-migrate, OpenAPI)
  verifies the JWT
  sets that identity on each pgx transaction
  owns records, authorization, jobs, review, and reports
        |
        | job row
        v
Python 3.12.13 worker (GDAL, Rasterio, GeoPandas, Shapely, PyProj, NumPy, SciPy, Xarray, rioxarray)
  reads allowlisted Earthdata objects named by the job
  writes measurements and checksums
        |
        v
Supabase PostgreSQL + PostGIS, Supabase Auth, Supabase Storage
```

The worker is not an HTTP business API. It does not own incidents, roles, or decisions.

## Database identity

User-scoped queries use a direct pgx transaction that carries a verified JWT identity. The sequence is:

1. Go verifies the bearer token against the Supabase JWKS in `SUPABASE_JWKS_URL`. Checks include signature, expiry, issuer, and audience. The environment template does not carry an HMAC shared secret.
2. Go opens a transaction with pgx.
3. Inside that transaction, before any application query, Go sets the database session to the verified subject (`sub`) and the `authenticated` role, using transaction-local configuration such as `set_config('request.jwt.claims', ..., true)` and `SET LOCAL ROLE authenticated`.
4. Row Level Security then sees that identity through `auth.uid()` and the membership policies.
5. The transaction ends. The identity setting does not leak into the next request on a pooled connection, because it is local to the transaction.

The client does not choose the user id that the database trusts. Editable user metadata is not a role source. Roles live in `user_roles`, written by an administrative path.

The service-role key bypasses RLS. It is not the default connection for user requests. It is not available to Next.js. Any future use of it has to be an explicit server-side exception with its own authorization check and an audit row.

## What is intentionally absent

- FastAPI, or any second business backend
- Kafka, Kubernetes, and extra network services
- A PostgreSQL service in Docker Compose
- Application routes, schema migrations, and a Supabase project
- Scientific processing code

`docker-compose.yml` is a placeholder with no services. Supabase remains the only database, when a later mission creates it.

## Module boundaries

| Path | Future contents | This mission |
| --- | --- | --- |
| `apps/web/` | Next.js UI | Empty placeholder |
| `services/api/` | Go API and OpenAPI | Empty placeholder. No `go.mod` yet |
| `services/worker/` | Python worker | Empty placeholder. No virtualenv and no `pyproject.toml` yet |
| `data/manifests/` | Rechecked catalogue metadata | Readme only. Mission 000 ids are not ingested |
| `docs/api/` | Published API notes | Empty placeholder |

The Go module line, when the API mission creates `go.mod`, is `go 1.25`. The installed toolchain may be newer. The module target stays 1.25 unless the architect changes this decision.

The worker interpreter is Python 3.12.13, including the copy already available through `uv` on the founder machine at Mission 000. The default `python` on PATH was 3.13.5 and is not the worker runtime.
