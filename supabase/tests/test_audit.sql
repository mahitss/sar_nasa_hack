begin;

select plan(6);

insert into auth.users (id, instance_id, aud, role, email, encrypted_password, email_confirmed_at, created_at, updated_at)
values
  ('11111111-1111-1111-1111-111111111111'::uuid, '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'o@test.local', crypt('pw', gen_salt('bf')), now(), now(), now()),
  ('22222222-2222-2222-2222-222222222222'::uuid, '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'm@test.local', crypt('pw', gen_salt('bf')), now(), now(), now());

reset role;
insert into public.incidents (id, title, created_by) values ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid, 'inc', '11111111-1111-1111-1111-111111111111'::uuid);
insert into public.incident_members (incident_id, user_id, role) values ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid, '22222222-2222-2222-2222-222222222222'::uuid, 'viewer');

-- audit row created on incident insert
select ok(
  exists (select 1 from public.audit_events where entity_table='incidents' and entity_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid),
  'audit row created on incident insert'
);

-- member can read audit
select set_config('request.jwt.claim.sub', '22222222-2222-2222-2222-222222222222', true);
select set_config('request.jwt.claims', '{"sub":"22222222-2222-2222-2222-222222222222","role":"authenticated"}', true);
set local role authenticated;
select ok(
  exists (select 1 from public.audit_events where entity_table='incidents'),
  'member can read incident audit'
);

-- audit snapshot does not contain arbitrary details
select ok(
  not exists (select 1 from public.audit_events where after_data ? 'description' and entity_table='incidents'),
  'audit snapshot excludes unrestricted fields'
);

-- ordinary user cannot update audit
select throws_ok(
  $$update public.audit_events set action='x' where entity_table='incidents'$$,
  null,
  'audit update denied'
);

-- ordinary user cannot delete audit
select throws_ok(
  $$delete from public.audit_events where entity_table='incidents'$$,
  null,
  'audit delete denied'
);

-- null-incident audit row not visible to ordinary member
reset role;
insert into public.audit_events (id, actor_id, action, entity_table, entity_id, incident_id)
values ('77777777-7777-7777-7777-777777777777'::uuid, null, 'SYSTEM', 'system', null, null);
select set_config('request.jwt.claim.sub', '22222222-2222-2222-2222-222222222222', true);
select set_config('request.jwt.claims', '{"sub":"22222222-2222-2222-2222-222222222222","role":"authenticated"}', true);
set local role authenticated;
select is(
  (select count(*) from public.audit_events where id='77777777-7777-7777-7777-777777777777'::uuid)::int,
  0,
  'null-incident audit row not visible to ordinary member'
);

select * from finish();
rollback;
PY