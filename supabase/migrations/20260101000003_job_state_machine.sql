-- Mission 017.1: job state machine, review RPC, and function grants

-- Hardened transition enforcement.
create or replace function private.enforce_job_transition()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  if new.state = old.state then
    -- same state: only allow retry_count increment? Block arbitrary metadata edits by requiring no other changes.
    if new.claimed_by is distinct from old.claimed_by
       or new.claimed_at is distinct from old.claimed_at
       or new.started_at is distinct from old.started_at
       or new.finished_at is distinct from old.finished_at
       or new.error_message is distinct from old.error_message
       or new.retry_count is distinct from old.retry_count then
      raise exception 'job metadata cannot be modified without a state transition';
    end if;
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
  if old.state = 'claimed' and new.state in ('running','failed','cancelled') then
    if new.state = 'running' and new.started_at is null then
      raise exception 'running job requires started_at';
    end if;
    return new;
  end if;
  if old.state = 'running' and new.state in ('succeeded','failed','cancelled') then
    if new.finished_at is null then
      raise exception 'terminal job requires finished_at';
    end if;
    return new;
  end if;
  raise exception 'illegal processing_job transition % -> %', old.state, new.state;
end $$;

revoke execute on function private.enforce_job_transition() from public, anon, authenticated;

create trigger processing_jobs_state_transition before update of state on public.processing_jobs
  for each row execute function private.enforce_job_transition();

-- Atomic review decision RPC.
create or replace function public.submit_evidence_decision(
  p_incident_id uuid,
  p_evidence_record_id uuid,
  p_decision text,
  p_rationale text
) returns uuid language plpgsql security definer set search_path = '' as $$
declare
  v_reviewer uuid := auth.uid();
  v_state review_state;
  v_decision_id uuid;
begin
  if p_decision not in ('accept','reject','needs_investigation') then
    raise exception 'invalid decision value';
  end if;
  if not exists (
    select 1 from public.incident_members
    where incident_id = p_incident_id and user_id = v_reviewer
      and role in ('owner','reviewer')
  ) then
    raise exception 'not authorized to review';
  end if;
  if not exists (
    select 1 from public.evidence_records
    where id = p_evidence_record_id and incident_id = p_incident_id
  ) then
    raise exception 'evidence not in incident';
  end if;
  if exists (
    select 1 from public.evidence_records
    where id = p_evidence_record_id and created_by = v_reviewer
  ) then
    raise exception 'cannot review own evidence';
  end if;
  v_state := case p_decision
    when 'accept' then 'accepted'::review_state
    when 'reject' then 'rejected'::review_state
    when 'needs_investigation' then 'needs_investigation'::review_state
  end;
  insert into public.decisions (incident_id, evidence_record_id, reviewer_id, decision, rationale)
  values (p_incident_id, p_evidence_record_id, v_reviewer, p_decision, p_rationale)
  returning id into v_decision_id;
  update public.evidence_records
    set review_state = v_state, updated_at = now()
    where id = p_evidence_record_id;
  return v_decision_id;
end $$;

revoke execute on function public.submit_evidence_decision(uuid, uuid, text, text) from public, anon;
grant execute on function public.submit_evidence_decision(uuid, uuid, text, text) to authenticated;

-- Function execution grants for private helpers already granted in migration 0000 for member/role helpers.
-- audit helpers remain trigger-only (no client grant).
