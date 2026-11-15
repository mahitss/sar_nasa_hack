begin;

select plan(6);

insert into auth.users (id, instance_id, aud, role, email, encrypted_password, email_confirmed_at, created_at, updated_at)
values
  ('11111111-1111-1111-1111-111111111111'::uuid, '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'o@test.local', crypt('pw', gen_salt('bf')), now(), now(), now()),
  ('22222222-2222-2222-2222-222222222222'::uuid, '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'a@test.local', crypt('pw', gen_salt('bf')), now(), now(), now())
on conflict (id) do nothing;

-- two incidents
reset role;
insert into public.incidents (id, title, created_by) values
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid, 'inc1', '11111111-1111-1111-1111-111111111111'::uuid),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'::uuid, 'inc2', '11111111-1111-1111-1111-111111111111'::uuid);
insert into public.incident_members (incident_id, user_id, role) values
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid, '22222222-2222-2222-2222-222222222222'::uuid, 'analyst'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'::uuid, '22222222-2222-2222-2222-222222222222'::uuid, 'analyst');

-- acquisition in inc2
insert into public.acquisitions (id, incident_id, source_provider, granule_id, crid) values
  ('cccccccc-cccc-cccc-cccc-cccccccccccc'::uuid, 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'::uuid, 'NISAR', 'g', 'P05023');

-- cross-incident acquisition reference should fail
select set_config('request.jwt.claim.sub', '22222222-2222-2222-2222-222222222222', true);
select set_config('request.jwt.claims', '{"sub":"22222222-2222-2222-2222-222222222222","role":"authenticated"}', true);
set local role authenticated;
select throws_ok(
  $$insert into public.evidence_records (incident_id, acquisition_id, claim_level, evidence_kind, title, summary, source_path, created_by) values ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid, 'cccccccc-cccc-cccc-cccc-cccccccccccc'::uuid, 'observation', 'observation', 't', 's', 'src', '22222222-2222-2222-2222-222222222222'::uuid)$$,
  null,
  'cross-incident acquisition reference fails'
);

-- evidence in inc1
reset role;
insert into public.evidence_records (id, incident_id, claim_level, evidence_kind, title, summary, source_path, created_by)
values ('eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee'::uuid, 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid, 'observation', 'observation', 't', 's', 'src', '22222222-2222-2222-2222-222222222222'::uuid);

-- cross-incident decision reference should fail
select set_config('request.jwt.claim.sub', '22222222-2222-2222-2222-222222222222', true);
select set_config('request.jwt.claims', '{"sub":"22222222-2222-2222-2222-222222222222","role":"authenticated"}', true);
set local role authenticated;
select throws_ok(
  $$insert into public.decisions (incident_id, evidence_record_id, reviewer_id, decision) values ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'::uuid, 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee'::uuid, '22222222-2222-2222-2222-222222222222'::uuid, 'accept')$$,
  null,
  'cross-incident decision reference fails'
);

-- authenticated user cannot delete evidence record
select throws_ok(
  $$delete from public.evidence_records where id='eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee'::uuid$$,
  null,
  'authenticated user cannot delete evidence record'
);

-- authenticated user cannot delete acquisition
select throws_ok(
  $$delete from public.acquisitions where id='cccccccc-cccc-cccc-cccc-cccccccccccc'::uuid$$,
  null,
  'authenticated user cannot delete acquisition'
);

-- valid composite incident and acquisition reference succeeds
select lives_ok(
  $$insert into public.evidence_records (incident_id, acquisition_id, claim_level, evidence_kind, title, summary, source_path, created_by) values ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'::uuid, 'cccccccc-cccc-cccc-cccc-cccccccccccc'::uuid, 'observation', 'observation', 'valid', 'summary', 'path', '22222222-2222-2222-2222-222222222222'::uuid)$$,
  'valid composite incident and acquisition succeeds'
);

select ok(true, 'composite foreign-key and evidence integrity confirmed');

select * from finish();
rollback;
