-- Mission 017.1: RLS policies, grants, and ownership trigger

-- Enable RLS
alter table public.profiles enable row level security;
alter table public.user_roles enable row level security;
alter table public.incidents enable row level security;
alter table public.incident_members enable row level security;
alter table public.acquisitions enable row level security;
alter table public.evidence_records enable row level security;
alter table public.processing_jobs enable row level security;
alter table public.decisions enable row level security;
alter table public.reports enable row level security;
alter table public.audit_events enable row level security;

-- Base grants: revoke everything from anon, public, authenticated
revoke all on all tables in schema public from anon, public, authenticated;
revoke all on all sequences in schema public from anon, public, authenticated;
revoke all on all functions in schema public from anon, public, authenticated;

-- authenticated: explicit per-table and per-column grants
-- profiles
grant select on public.profiles to authenticated;
grant insert (id, display_name) on public.profiles to authenticated;
grant update (display_name) on public.profiles to authenticated;

-- user_roles: no client access
-- (already revoked)

-- incidents
grant select on public.incidents to authenticated;
grant insert (id, title, description, discovery_west, discovery_south, discovery_east, discovery_north, created_by) on public.incidents to authenticated;
grant update (title, description, discovery_west, discovery_south, discovery_east, discovery_north) on public.incidents to authenticated;

-- incident_members
grant select, delete on public.incident_members to authenticated;
grant insert (incident_id, user_id, role) on public.incident_members to authenticated;
grant update (role) on public.incident_members to authenticated;

-- acquisitions
grant select on public.acquisitions to authenticated;
grant insert (id, incident_id, source_provider, granule_id, acquisition_start, acquisition_end, track, frame, orbit_direction, frequency_mhz, bandwidth_mhz, polarization, crid, product_maturity, source_metadata) on public.acquisitions to authenticated;
grant update (source_metadata) on public.acquisitions to authenticated;

-- evidence_records
grant select on public.evidence_records to authenticated;
grant insert (id, incident_id, acquisition_id, claim_level, evidence_kind, source_mission, title, summary, details, source_path, limitations, processing_version, code_version, parameters, source_checksums, measurement_unit, created_by) on public.evidence_records to authenticated;
grant update (title, summary, details, limitations, processing_version, code_version, parameters, source_checksums, measurement_unit) on public.evidence_records to authenticated;

-- processing_jobs: no client update/delete
grant select, insert on public.processing_jobs to authenticated;

-- decisions: read only for clients (insert via function)
grant select on public.decisions to authenticated;

-- reports
grant select on public.reports to authenticated;
grant insert (id, incident_id, title, content, generated_by) on public.reports to authenticated;

-- audit_events: select only
grant select on public.audit_events to authenticated;

-- Default privileges for future objects
alter default privileges for role postgres in schema public revoke all on tables from public, anon, authenticated;
alter default privileges for role postgres in schema public revoke all on sequences from public, anon, authenticated;
alter default privileges for role postgres in schema public revoke all on functions from public, anon, authenticated;
alter default privileges for role postgres in schema public grant select on tables to authenticated;

-- ---- RLS policies (all TO authenticated) ----

-- profiles
create policy profiles_select_own on public.profiles for select to authenticated using (id = auth.uid());
create policy profiles_insert_own on public.profiles for insert to authenticated with check (id = auth.uid());
create policy profiles_update_own on public.profiles for update to authenticated using (id = auth.uid()) with check (id = auth.uid());

-- user_roles: no client access (no policies + no grants)

-- incidents
create policy incidents_select_member on public.incidents for select to authenticated
  using (created_by = auth.uid() or private.is_incident_member(id));
create policy incidents_insert_creator on public.incidents for insert to authenticated
  with check (created_by = auth.uid());
create policy incidents_update_owner on public.incidents for update to authenticated
  using (private.has_incident_role(id,'owner')) with check (private.has_incident_role(id,'owner'));

-- incident_members
create policy incident_members_select on public.incident_members for select to authenticated
  using (private.is_incident_member(incident_id));
create policy incident_members_insert_owner on public.incident_members for insert to authenticated
  with check (private.has_incident_role(incident_id,'owner'));
create policy incident_members_update_owner on public.incident_members for update to authenticated
  using (private.has_incident_role(incident_id,'owner')) with check (private.has_incident_role(incident_id,'owner'));
create policy incident_members_delete_owner on public.incident_members for delete to authenticated
  using (private.has_incident_role(incident_id,'owner'));

-- acquisitions
create policy acquisitions_select_member on public.acquisitions for select to authenticated
  using (private.is_incident_member(incident_id));
create policy acquisitions_insert_analyst on public.acquisitions for insert to authenticated
  with check (private.has_incident_role(incident_id,'owner') or private.has_incident_role(incident_id,'analyst'));
create policy acquisitions_update_analyst on public.acquisitions for update to authenticated
  using (private.has_incident_role(incident_id,'owner') or private.has_incident_role(incident_id,'analyst'))
  with check (private.has_incident_role(incident_id,'owner') or private.has_incident_role(incident_id,'analyst'));

-- evidence_records
create policy evidence_select_member on public.evidence_records for select to authenticated
  using (private.is_incident_member(incident_id));
create policy evidence_insert_analyst on public.evidence_records for insert to authenticated
  with check (
    created_by = auth.uid() and review_state = 'draft' and
    (private.has_incident_role(incident_id,'owner') or private.has_incident_role(incident_id,'analyst'))
  );
create policy evidence_update_analyst on public.evidence_records for update to authenticated
  using (
    private.has_incident_role(incident_id,'owner') or
    (private.has_incident_role(incident_id,'analyst') and review_state = 'draft')
  )
  with check (
    private.has_incident_role(incident_id,'owner') or
    (private.has_incident_role(incident_id,'analyst') and review_state = 'draft')
  );

-- processing_jobs
create policy jobs_select_member on public.processing_jobs for select to authenticated
  using (private.is_incident_member(incident_id));
create policy jobs_insert_analyst on public.processing_jobs for insert to authenticated
  with check (private.has_incident_role(incident_id,'owner') or private.has_incident_role(incident_id,'analyst'));

-- decisions: read only (insert via function)
create policy decisions_select_member on public.decisions for select to authenticated
  using (private.is_incident_member(incident_id));

-- reports
create policy reports_select_member on public.reports for select to authenticated
  using (private.is_incident_member(incident_id));
create policy reports_insert_analyst on public.reports for insert to authenticated
  with check (generated_by = auth.uid() and
    (private.has_incident_role(incident_id,'owner') or private.has_incident_role(incident_id,'analyst')));

-- audit_events
create policy audit_select_member on public.audit_events for select to authenticated
  using (incident_id is not null and private.is_incident_member(incident_id));

-- Incident owner auto-creation trigger
create or replace function private.create_incident_owner()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  insert into public.incident_members (incident_id, user_id, role)
  values (new.id, new.created_by, 'owner');
  return new;
end $$;

revoke execute on function private.create_incident_owner() from public, anon, authenticated;

create trigger incidents_create_owner after insert on public.incidents
  for each row execute function private.create_incident_owner();

-- Last-owner protection trigger
create or replace function private.protect_last_owner()
returns trigger language plpgsql security definer set search_path = '' as $$
declare
  v_incident uuid;
  v_remaining integer;
begin
  if tg_op = 'DELETE' then
    v_incident := old.incident_id;
    if old.role = 'owner' then
      perform 1 from public.incidents where id = v_incident for update;
      select count(*) into v_remaining
        from public.incident_members
        where incident_id = v_incident and role = 'owner' and id <> old.id;
      if v_remaining = 0 then
        raise exception 'cannot remove the last owner of an incident';
      end if;
    end if;
    return old;
  elsif tg_op = 'UPDATE' then
    if new.incident_id <> old.incident_id or new.user_id <> old.user_id then
      raise exception 'incident_id and user_id cannot be changed';
    end if;
    if old.role = 'owner' and new.role <> 'owner' then
      v_incident := old.incident_id;
      perform 1 from public.incidents where id = v_incident for update;
      select count(*) into v_remaining
        from public.incident_members
        where incident_id = v_incident and role = 'owner' and id <> old.id;
      if v_remaining = 0 then
        raise exception 'cannot demote the last owner of an incident';
      end if;
    end if;
    return new;
  end if;
  return new;
end $$;

revoke execute on function private.protect_last_owner() from public, anon, authenticated;

create trigger incident_members_protect_owner before update or delete on public.incident_members
  for each row execute function private.protect_last_owner();
