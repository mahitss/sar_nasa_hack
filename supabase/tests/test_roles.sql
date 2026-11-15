begin;

select plan(10);

insert into auth.users (id, instance_id, aud, role, email, encrypted_password, email_confirmed_at, created_at, updated_at)
values
  ('11111111-1111-1111-1111-111111111111'::uuid, '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'owner@test.local', crypt('pw', gen_salt('bf')), now(), now(), now()),
  ('22222222-2222-2222-2222-222222222222'::uuid, '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'analyst@test.local', crypt('pw', gen_salt('bf')), now(), now(), now()),
  ('33333333-3333-3333-3333-333333333333'::uuid, '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'reviewer@test.local', crypt('pw', gen_salt('bf')), now(), now(), now()),
  ('44444444-4444-4444-4444-444444444444'::uuid, '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'viewer@test.local', crypt('pw', gen_salt('bf')), now(), now(), now())
on conflict (id) do nothing;

-- owner creates incident
select set_config('request.jwt.claim.sub', '11111111-1111-1111-1111-111111111111', true);
select set_config('request.jwt.claims', '{"sub":"11111111-1111-1111-1111-111111111111","role":"authenticated"}', true);
set local role authenticated;
insert into public.incidents (id, title, created_by) values ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid, 'inc', '11111111-1111-1111-1111-111111111111'::uuid);

-- add members with roles
reset role;
insert into public.incident_members (incident_id, user_id, role) values
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid, '22222222-2222-2222-2222-222222222222'::uuid, 'analyst'),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid, '33333333-3333-3333-3333-333333333333'::uuid, 'reviewer'),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid, '44444444-4444-4444-4444-444444444444'::uuid, 'viewer');

-- viewer cannot create evidence
select set_config('request.jwt.claim.sub', '44444444-4444-4444-4444-444444444444', true);
select set_config('request.jwt.claims', '{"sub":"44444444-4444-4444-4444-444444444444","role":"authenticated"}', true);
set local role authenticated;
select throws_ok(
  $$insert into public.evidence_records (incident_id, claim_level, evidence_kind, title, summary, source_path, created_by) values ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid, 'observation', 'observation', 't', 's', 'src', '44444444-4444-4444-4444-444444444444'::uuid)$$,
  null,
  'viewer cannot create evidence'
);

-- analyst can create draft
select set_config('request.jwt.claim.sub', '22222222-2222-2222-2222-222222222222', true);
select set_config('request.jwt.claims', '{"sub":"22222222-2222-2222-2222-222222222222","role":"authenticated"}', true);
set local role authenticated;
select lives_ok(
  $$insert into public.evidence_records (id, incident_id, claim_level, evidence_kind, title, summary, source_path, created_by) values ('eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee'::uuid, 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid, 'observation', 'observation', 't', 's', 'src', '22222222-2222-2222-2222-222222222222'::uuid)$$,
  'analyst can create draft evidence'
);

-- analyst cannot insert decision
select throws_ok(
  $$insert into public.decisions (incident_id, evidence_record_id, reviewer_id, decision) values ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid, 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee'::uuid, '22222222-2222-2222-2222-222222222222'::uuid, 'accept')$$,
  null,
  'analyst cannot insert decision directly'
);

-- direct insert as accepted denied (review_state default draft enforced; accepted not allowed via insert grant? column revoked insert review_state, default draft)
select throws_ok(
  $$insert into public.evidence_records (incident_id, claim_level, evidence_kind, title, summary, source_path, review_state, created_by) values ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid, 'observation', 'observation', 't2', 's2', 'src2', 'accepted', '22222222-2222-2222-2222-222222222222'::uuid)$$,
  null,
  'direct insert as accepted denied'
);

-- reviewer can decide via RPC
select set_config('request.jwt.claim.sub', '33333333-3333-3333-3333-333333333333', true);
select set_config('request.jwt.claims', '{"sub":"33333333-3333-3333-3333-333333333333","role":"authenticated"}', true);
set local role authenticated;
select lives_ok(
  $$select public.submit_evidence_decision('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid, 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee'::uuid, 'accept', 'ok')$$,
  'reviewer can decide'
);

-- self-review rejected
select set_config('request.jwt.claim.sub', '22222222-2222-2222-2222-222222222222', true);
select set_config('request.jwt.claims', '{"sub":"22222222-2222-2222-2222-222222222222","role":"authenticated"}', true);
set local role authenticated;
-- create another evidence owned by analyst2? use existing owned by 222; self-review should fail
select throws_ok(
  $$select public.submit_evidence_decision('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid, 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee'::uuid, 'accept', 'self')$$,
  null,
  'self-review rejected'
);

-- direct review_state update denied
select set_config('request.jwt.claim.sub', '22222222-2222-2222-2222-222222222222', true);
select set_config('request.jwt.claims', '{"sub":"22222222-2222-2222-2222-222222222222","role":"authenticated"}', true);
set local role authenticated;
select throws_ok(
  $$update public.evidence_records set review_state='accepted' where id='eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee'::uuid$$,
  null,
  'direct review_state update denied'
);

-- analyst cannot review evidence via RPC
reset role;
insert into public.evidence_records (id, incident_id, claim_level, evidence_kind, title, summary, source_path, created_by)
values ('ffffffff-ffff-ffff-ffff-ffffffffffff'::uuid, 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid, 'observation', 'observation', 't3', 's3', 'src3', '11111111-1111-1111-1111-111111111111'::uuid);
select set_config('request.jwt.claim.sub', '22222222-2222-2222-2222-222222222222', true);
select set_config('request.jwt.claims', '{"sub":"22222222-2222-2222-2222-222222222222","role":"authenticated"}', true);
set local role authenticated;
select throws_ok(
  $$select public.submit_evidence_decision('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid, 'ffffffff-ffff-ffff-ffff-ffffffffffff'::uuid, 'accept', 'analyst attempt')$$,
  'not authorized to review',
  'analyst cannot review evidence via RPC'
);

-- viewer cannot create report
select set_config('request.jwt.claim.sub', '44444444-4444-4444-4444-444444444444', true);
select set_config('request.jwt.claims', '{"sub":"44444444-4444-4444-4444-444444444444","role":"authenticated"}', true);
set local role authenticated;
select throws_ok(
  $$insert into public.reports (incident_id, title, generated_by) values ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid, 'viewer report', '44444444-4444-4444-4444-444444444444'::uuid)$$,
  null,
  'viewer cannot create report'
);

-- platform admin does not bypass membership (no rows visible)
reset role;
insert into auth.users (id, instance_id, aud, role, email, encrypted_password, email_confirmed_at, created_at, updated_at)
values ('55555555-5555-5555-5555-555555555555'::uuid, '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'admin@test.local', crypt('pw', gen_salt('bf')), now(), now(), now())
on conflict (id) do nothing;
insert into public.user_roles (user_id, role) values ('55555555-5555-5555-5555-555555555555'::uuid, 'platform_admin')
on conflict (user_id, role) do nothing;
select set_config('request.jwt.claim.sub', '55555555-5555-5555-5555-555555555555', true);
select set_config('request.jwt.claims', '{"sub":"55555555-5555-5555-5555-555555555555","role":"authenticated"}', true);
set local role authenticated;
select is(
  (select count(*) from public.incidents where id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid)::int,
  0,
  'platform admin has no implicit incident access'
);

select * from finish();
rollback;
