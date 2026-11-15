-- Mission 021: Worker leasing, payload contract, result persistence, and lease recovery

alter table public.processing_jobs
  add column if not exists payload jsonb not null default '{}'::jsonb check (jsonb_typeof(payload) = 'object'),
  add column if not exists lease_token text,
  add column if not exists lease_expires_at timestamptz,
  add column if not exists attempt_id uuid,
  add column if not exists result jsonb check (result is null or jsonb_typeof(result) = 'object');

create index if not exists processing_jobs_queued_idx
  on public.processing_jobs(state, created_at)
  where state = 'queued';

create index if not exists processing_jobs_lease_idx
  on public.processing_jobs(state, lease_expires_at)
  where state in ('claimed', 'running');

-- Updated transition trigger to support lease recovery and heartbeats
create or replace function private.enforce_job_transition()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  if new.state = old.state then
    -- Terminal jobs cannot be modified in any way
    if old.state in ('succeeded', 'failed', 'cancelled') then
      raise exception 'terminal job cannot be modified';
    end if;
    -- Non-terminal jobs: allow heartbeats (updating lease_expires_at and updated_at)
    return new;
  end if;

  if old.state = 'queued' and new.state in ('claimed','cancelled') then
    if new.state = 'claimed' then
      if new.claimed_by is null or new.claimed_at is null then
        raise exception 'claimed job requires claimed_by and claimed_at';
      end if;
    end if;
    return new;
  end if;

  if old.state = 'claimed' and new.state in ('running','failed','cancelled','queued') then
    if new.state = 'running' and new.started_at is null then
      raise exception 'running job requires started_at';
    end if;
    return new;
  end if;

  if old.state = 'running' and new.state in ('succeeded','failed','cancelled','queued') then
    if new.state in ('succeeded','failed','cancelled') and new.finished_at is null then
      raise exception 'terminal job requires finished_at';
    end if;
    return new;
  end if;

  raise exception 'illegal processing_job transition % -> %', old.state, new.state;
end $$;

drop trigger if exists processing_jobs_state_transition on public.processing_jobs;
create trigger processing_jobs_state_transition
  before update on public.processing_jobs
  for each row execute function private.enforce_job_transition();
