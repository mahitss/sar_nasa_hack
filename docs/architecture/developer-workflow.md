# RIVET developer workflow

## Frontend (implemented)

```powershell
Set-Location C:\Projects\RIVET\apps\web
npm ci
npm run lint
npm run typecheck
npm run build
npm run dev
```

## Go API (not implemented yet)

Not available. `services/api` contains only `.gitkeep`.

## Python worker (not implemented yet)

Not available. `services/worker` contains only `.gitkeep`.

Python 3.12.13 is available through `uv` on this machine.

## Supabase local development

Docker daemon is not running on this machine. Supabase CLI is available via `npx supabase`. No Supabase project has been created. Do not start Docker Desktop automatically.

## Scientific tests

```powershell
Set-Location C:\Projects\RIVET
uv run --python 3.12 pytest tests/scientific
```

## Vercel local build

```powershell
Set-Location C:\Projects\RIVET\apps\web
npx vercel@latest link --yes --project web --scope <team>
npx vercel@latest pull --yes --environment preview
npx vercel@latest build --yes --environment preview
```

On Windows, the Vercel build may fail with EPERM symlink errors. This is an environment limitation, not a project build failure.

## Local database

```powershell
Set-Location C:\Projects\RIVET
npx supabase start
npx supabase db reset
npx supabase test db
```

Docker Desktop must be running. Do not start it automatically; the founder starts it.

## Safety

- Do not commit `.vercel`, `.env.local`, secrets, science files, or build output.
- Do not run `vercel deploy`.
- Do not modify `main`.
