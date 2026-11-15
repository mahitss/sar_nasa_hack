-- Mission 017.1: append-only audit enforcement and allowlisted snapshots

-- Prevent updates/deletes on audit_events.
create or replace function private.prevent_audit_mutation()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  raise exception 'audit_events is append-only';
end $$;

revoke execute on function private.prevent_audit_mutation() from public, anon, authenticated;

create trigger audit_events_no_update before update on public.audit_events
  for each row execute function private.prevent_audit_mutation();
create trigger audit_events_no_delete before delete on public.audit_events
  for each row execute function private.prevent_audit_mutation();

-- Allowlisted snapshot builder.
create or replace function private.audit_snapshot(p_table text, p_row jsonb)
returns jsonb language plpgsql security definer set search_path = '' as $$
begin
  case p_table
    when 'incidents' then
      return jsonb_build_object(
        'id', p_row->'id',
        'title', p_row->'title',
        'archived_at', p_row->'archived_at',
        'created_by', p_row->'created_by'
      );
    when 'incident_members' then
      return jsonb_build_object(
        'id', p_row->'id',
        'incident_id', p_row->'incident_id',
        'user_id', p_row->'user_id',
        'role', p_row->'role'
      );
    when 'acquisitions' then
      return jsonb_build_object(
        'id', p_row->'id',
        'incident_id', p_row->'incident_id',
        'granule_id', p_row->'granule_id',
        'crid', p_row->'crid',
        'product_maturity', p_row->'product_maturity'
      );
    when 'evidence_records' then
      return jsonb_build_object(
        'id', p_row->'id',
        'incident_id', p_row->'incident_id',
        'acquisition_id', p_row->'acquisition_id',
        'claim_level', p_row->'claim_level',
        'evidence_kind', p_row->'evidence_kind',
        'review_state', p_row->'review_state',
        'source_path', p_row->'source_path',
        'created_by', p_row->'created_by'
      );
    when 'processing_jobs' then
      return jsonb_build_object(
        'id', p_row->'id',
        'incident_id', p_row->'incident_id',
        'job_type', p_row->'job_type',
        'state', p_row->'state',
        'retry_count', p_row->'retry_count'
      );
    when 'decisions' then
      return jsonb_build_object(
        'id', p_row->'id',
        'incident_id', p_row->'incident_id',
        'evidence_record_id', p_row->'evidence_record_id',
        'reviewer_id', p_row->'reviewer_id',
        'decision', p_row->'decision'
      );
    when 'reports' then
      return jsonb_build_object(
        'id', p_row->'id',
        'incident_id', p_row->'incident_id',
        'title', p_row->'title',
        'generated_by', p_row->'generated_by'
      );
    else
      return jsonb_build_object('id', p_row->'id');
  end case;
end $$;

revoke execute on function private.audit_snapshot(text, jsonb) from public, anon, authenticated;

-- Audit writer
create or replace function private.write_audit_event()
returns trigger language plpgsql security definer set search_path = '' as $$
declare
  v_incident_id uuid;
  v_before jsonb;
  v_after jsonb;
  v_entity_id uuid;
begin
  if tg_op = 'DELETE' then
    v_before := private.audit_snapshot(tg_table_name, to_jsonb(old));
    v_after := null;
    v_entity_id := (to_jsonb(old)->>'id')::uuid;
  elsif tg_op = 'INSERT' then
    v_before := null;
    v_after := private.audit_snapshot(tg_table_name, to_jsonb(new));
    v_entity_id := (to_jsonb(new)->>'id')::uuid;
  else
    v_before := private.audit_snapshot(tg_table_name, to_jsonb(old));
    v_after := private.audit_snapshot(tg_table_name, to_jsonb(new));
    v_entity_id := (to_jsonb(new)->>'id')::uuid;
  end if;

  begin
    if tg_table_name = 'incidents' then
      v_incident_id := v_entity_id;
    elsif tg_op in ('INSERT','UPDATE') then
      v_incident_id := (to_jsonb(new)->>'incident_id')::uuid;
    else
      v_incident_id := (to_jsonb(old)->>'incident_id')::uuid;
    end if;
  exception when others then
    v_incident_id := null;
  end;

  insert into public.audit_events (actor_id, action, entity_table, entity_id, incident_id, before_data, after_data)
  values (
    auth.uid(),
    tg_op || '_' || tg_table_name,
    tg_table_name,
    v_entity_id,
    v_incident_id,
    v_before,
    v_after
  );
  if tg_op = 'DELETE' then return old; else return new; end if;
end $$;

revoke execute on function private.write_audit_event() from public, anon, authenticated;

create trigger audit_incidents after insert or update or delete on public.incidents
  for each row execute function private.write_audit_event();
create trigger audit_incident_members after insert or update or delete on public.incident_members
  for each row execute function private.write_audit_event();
create trigger audit_acquisitions after insert or update or delete on public.acquisitions
  for each row execute function private.write_audit_event();
create trigger audit_evidence_records after insert or update or delete on public.evidence_records
  for each row execute function private.write_audit_event();
create trigger audit_processing_jobs after insert or update or delete on public.processing_jobs
  for each row execute function private.write_audit_event();
create trigger audit_decisions after insert or update or delete on public.decisions
  for each row execute function private.write_audit_event();
create trigger audit_reports after insert or update or delete on public.reports
  for each row execute function private.write_audit_event();
