# ADR-002: Technology stack

- Status: Accepted for the repository foundation by Mission 001
- Date: 2026-11-14
- Supersedes: none

## Context

The stack was frozen before Mission 000 and carried forward with the conditional approval. Mission 000 found the founder machine can support it after using Python 3.12.13 rather than the default 3.13.5 interpreter, and after starting Docker Desktop only when a later mission needs it.

## Decision

| Layer | Choice |
| --- | --- |
| Web | Next.js 16, React 19, TypeScript, Tailwind CSS v4, shadcn/ui, MapLibre GL JS, Supabase SSR |
| API | Go module target 1.25, Chi, pgx, sqlc, golang-migrate, OpenAPI |
| Worker | Python 3.12.13, GDAL, Rasterio, GeoPandas, Shapely, PyProj, NumPy, SciPy, Xarray, rioxarray |
| Identity and data | Supabase Auth, Supabase PostgreSQL, PostGIS, Supabase Storage |
| Tests | Go test, Pytest, Playwright, when those trees are implemented |
| Containers | Docker Compose may later build the worker. It does not host PostgreSQL. |

Go owns business logic. Python owns scientific processing. Next.js owns the interface.

Rejected for this project:

- FastAPI as a second business backend
- Kafka, Kubernetes, and additional microservices
- A second PostgreSQL instance beside Supabase
- Trusting editable user metadata for roles
- Using the service-role key for ordinary user requests

## Identity decision

The Go API verifies Supabase JWTs and establishes that verified identity inside each direct pgx transaction before application SQL runs. Row Level Security remains enabled. Details are in `docs/security/threat-model.md` and `docs/architecture/overview.md`.

## Consequences

- `go.mod`, `package.json`, and `pyproject.toml` are intentionally absent until the mission that creates each application.
- Dependencies are not installed in Mission 001.
- No Supabase project is created in Mission 001.
- `docker-compose.yml` has an empty service map so the file exists without implying a running stack.

## Environment notes from Mission 000

These were observed on 14 November 2026 and were not retested in Mission 001, except the working directory:

- Working directory for this repository: `C:\Projects\RIVET`. The previous OneDrive folder was left unused.
- Go on the machine was 1.27.0. The module target remains 1.25.
- Python 3.12.13 was available through `uv`. Python 3.13.5 was the default on PATH.
- Docker CLI 29.9.3 and Compose v5.7.0 were installed. The daemon was not running.
- Node.js was v24.11.0 and pnpm was 12.18.0. Next.js 16 engine support for that Node version was not executed, because nothing was installed.
