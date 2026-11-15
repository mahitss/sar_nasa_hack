-- Mission 017.1: RIVET identity, persistence and audit foundation (hardened)

create extension if not exists "pgcrypto";
create extension if not exists "uuid-ossp";

-- Private schema for internal SECURITY DEFINER helpers.
create schema if not exists private;

-- Enumerated role values used across the application.
do $$ begin
  create type incident_role as enum ('owner','analyst','reviewer','viewer');
exception when duplicate_object then null; end $$;

do $$ begin
  create type claim_level as enum ('observation','measurement','interpretation','hypothesis','model','gap');
exception when duplicate_object then null; end $$;

do $$ begin
  create type evidence_kind as enum ('observation','measurement','interpretation','hypothesis','gap');
exception when duplicate_object then null; end $$;

do $$ begin
  create type review_state as enum ('draft','submitted','accepted','rejected','needs_investigation');
exception when duplicate_object then null; end $$;

do $$ begin
  create type processing_job_state as enum ('queued','claimed','running','succeeded','failed','cancelled');
exception when duplicate_object then null; end $$;

do $$ begin
  create type product_maturity as enum ('provisional','validated');
exception when duplicate_object then null; end $$;

-- 1. profiles
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- 2. user_roles (global application privileges; not user-editable)
create table if not exists public.user_roles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('platform_admin')),
  created_at timestamptz not null default now(),
  unique (user_id, role)
);

-- 3. incidents
create table if not exists public.incidents (
  id uuid primary key default gen_random_uuid(),
  title text not null check (length(title) > 0),
  description text,
  discovery_west double precision,
  discovery_south double precision,
  discovery_east double precision,
  discovery_north double precision,
  archived_at timestamptz,
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (discovery_west is null or discovery_east is null or discovery_west < discovery_east),
  check (discovery_south is null or discovery_north is null or discovery_south < discovery_north)
);

-- 4. incident_members
create table if not exists public.incident_members (
  id uuid primary key default gen_random_uuid(),
  incident_id uuid not null references public.incidents(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role incident_role not null,
  created_at timestamptz not null default now(),
  unique (incident_id, user_id)
);

create index if not exists incident_members_user_idx on public.incident_members(user_id);
create index if not exists incident_members_incident_idx on public.incident_members(incident_id);

-- 5. acquisitions
create table if not exists public.acquisitions (
  id uuid primary key default gen_random_uuid(),
  incident_id uuid not null references public.incidents(id) on delete cascade,
  source_provider text not null check (length(source_provider) > 0),
  granule_id text not null check (length(granule_id) > 0),
  acquisition_start timestamptz,
  acquisition_end timestamptz,
  track integer check (track is null or track >= 0),
  frame integer check (frame is null or frame >= 0),
  orbit_direction text check (orbit_direction is null or orbit_direction in ('ascending','descending')),
  frequency_mhz integer check (frequency_mhz is null or frequency_mhz >= 0),
  bandwidth_mhz integer check (bandwidth_mhz is null or bandwidth_mhz >= 0),
  polarization text,
  crid text not null check (length(crid) > 0),
  product_maturity product_maturity not null default 'provisional',
  source_metadata jsonb not null default '{}'::jsonb check (jsonb_typeof(source_metadata) = 'object'),
  created_at timestamptz not null default now(),
  unique (incident_id, granule_id),
  unique (incident_id, id),
  check (acquisition_start is null or acquisition_end is null or acquisition_start <= acquisition_end)
);

create index if not exists acquisitions_incident_idx on public.acquisitions(incident_id);

-- 6. evidence_records
create table if not exists public.evidence_records (
  id uuid primary key default gen_random_uuid(),
  incident_id uuid not null references public.incidents(id) on delete cascade,
  acquisition_id uuid,
  claim_level claim_level not null,
  evidence_kind evidence_kind not null,
  source_mission text,
  title text not null check (length(title) > 0),
  summary text not null check (length(summary) > 0),
  details jsonb not null default '[]'::jsonb check (jsonb_typeof(details) = 'array'),
  source_path text not null check (length(source_path) > 0),
  limitations jsonb not null default '[]'::jsonb check (jsonb_typeof(limitations) = 'array'),
  processing_version text,
  code_version text,
  parameters jsonb check (parameters is null or jsonb_typeof(parameters) in ('object','array')),
  source_checksums jsonb check (source_checksums is null or jsonb_typeof(source_checksums) in ('object','array')),
  measurement_unit text,
  review_state review_state not null default 'draft',
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (incident_id, id),
  foreign key (incident_id, acquisition_id) references public.acquisitions(incident_id, id) on delete restrict
);

create index if not exists evidence_records_incident_idx on public.evidence_records(incident_id);
create index if not exists evidence_records_acquisition_idx on public.evidence_records(acquisition_id);

-- 7. processing_jobs
create table if not exists public.processing_jobs (
  id uuid primary key default gen_random_uuid(),
  incident_id uuid not null references public.incidents(id) on delete cascade,
  job_type text not null check (length(job_type) > 0),
  state processing_job_state not null default 'queued',
  claimed_by text,
  claimed_at timestamptz,
  started_at timestamptz,
  finished_at timestamptz,
  error_message text,
  retry_count integer not null default 0 check (retry_count >= 0),
  idempotency_key text not null check (length(idempotency_key) > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (incident_id, idempotency_key),
  check (claimed_at is null or claimed_by is not null),
  check (started_at is null or claimed_at is not null),
  check (finished_at is null or started_at is not null)
);

create index if not exists processing_jobs_incident_idx on public.processing_jobs(incident_id);
create index if not exists processing_jobs_state_idx on public.processing_jobs(state);

-- 8. decisions
create table if not exists public.decisions (
  id uuid primary key default gen_random_uuid(),
  incident_id uuid not null references public.incidents(id) on delete cascade,
  evidence_record_id uuid not null,
  reviewer_id uuid not null references auth.users(id),
  decision text not null check (decision in ('accept','reject','needs_investigation')),
  rationale text,
  created_at timestamptz not null default now(),
  foreign key (incident_id, evidence_record_id) references public.evidence_records(incident_id, id) on delete restrict
);

create index if not exists decisions_incident_idx on public.decisions(incident_id);
create index if not exists decisions_evidence_idx on public.decisions(evidence_record_id);

-- 9. reports
create table if not exists public.reports (
  id uuid primary key default gen_random_uuid(),
  incident_id uuid not null references public.incidents(id) on delete cascade,
  title text not null check (length(title) > 0),
  content jsonb not null default '{}'::jsonb check (jsonb_typeof(content) = 'object'),
  generated_by uuid not null references auth.users(id),
  created_at timestamptz not null default now()
);

create index if not exists reports_incident_idx on public.reports(incident_id);

-- 10. audit_events (append-only)
create table if not exists public.audit_events (
  id uuid primary key default gen_random_uuid(),
  actor_id uuid references auth.users(id),
  action text not null check (length(action) > 0),
  entity_table text not null check (length(entity_table) > 0),
  entity_id uuid,
  incident_id uuid references public.incidents(id) on delete restrict,
  occurred_at timestamptz not null default now(),
  before_data jsonb check (before_data is null or jsonb_typeof(before_data) = 'object'),
  after_data jsonb check (after_data is null or jsonb_typeof(after_data) = 'object')
);

create index if not exists audit_events_incident_idx on public.audit_events(incident_id);
create index if not exists audit_events_entity_idx on public.audit_events(entity_table, entity_id);

-- updated_at trigger helper
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

create trigger profiles_updated_at before update on public.profiles
  for each row execute function public.set_updated_at();
create trigger incidents_updated_at before update on public.incidents
  for each row execute function public.set_updated_at();
create trigger evidence_records_updated_at before update on public.evidence_records
  for each row execute function public.set_updated_at();
create trigger processing_jobs_updated_at before update on public.processing_jobs
  for each row execute function public.set_updated_at();

-- Private helper: incident membership
create or replace function private.is_incident_member(p_incident_id uuid)
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from public.incident_members m
    where m.incident_id = p_incident_id and m.user_id = auth.uid()
  );
$$;

create or replace function private.has_incident_role(p_incident_id uuid, p_role incident_role)
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from public.incident_members m
    where m.incident_id = p_incident_id and m.user_id = auth.uid() and m.role = p_role
  );
$$;

revoke execute on function private.is_incident_member(uuid) from public, anon, authenticated;
revoke execute on function private.has_incident_role(uuid, incident_role) from public, anon, authenticated;
grant execute on function private.is_incident_member(uuid) to authenticated;
grant execute on function private.has_incident_role(uuid, incident_role) to authenticated;
