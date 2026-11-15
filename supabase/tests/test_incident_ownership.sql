begin;

select plan(8);

-- create two synthetic users
insert into auth.users (id, instance_id, aud, role, email, encrypted_password, email_confirmed_at, created_at, updated_at)
values
  ('11111111-1111-1111-1111-111111111111'::uuid, '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'u1@test.local', crypt('pw', gen_salt('bf')), now(), now(), now()),
  ('22222222-2222-2222-2222-222222222222'::uuid, '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'u2@test.local', crypt('pw', gen_salt('bf')), now(), now(), now());

-- act as user1
select set_config('request.jwt.claim.sub', '11111111-1111-1111-1111-111111111111', true);
select set_config('request.jwt.claims', '{"sub":"11111111-1111-1111-1111-111111111111","role":"authenticated"}', true);
set local role authenticated;

insert into public.incidents (id, title, created_by)
values ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid, 'test incident', '11111111-1111-1111-1111-111111111111'::uuid);

-- creator gets owner membership
select ok(
  exists (select 1 from public.incident_members where incident_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid and user_id='11111111-1111-1111-1111-111111111111'::uuid and role='owner'),
  'creator receives owner membership'
);

-- creator can read
select ok(
  exists (select 1 from public.incidents where id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid),
  'creator can read incident'
);

-- switch to user2
select set_config('request.jwt.claim.sub', '22222222-2222-2222-2222-222222222222', true);
select set_config('request.jwt.claims', '{"sub":"22222222-2222-2222-2222-222222222222","role":"authenticated"}', true);
set local role authenticated;

-- non-member cannot read
select is(
  (select count(*) from public.incidents where id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid)::int,
  0,
  'non-member cannot read incident'
);

-- non-member cannot self-assign owner
select throws_ok(
  $$insert into public.incident_members (incident_id, user_id, role) values ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid, '22222222-2222-2222-2222-222222222222'::uuid, 'owner')$$,
  null,
  'non-owner cannot insert membership'
);

-- switch back to owner for last-owner protection tests
select set_config('request.jwt.claim.sub', '11111111-1111-1111-1111-111111111111', true);
select set_config('request.jwt.claims', '{"sub":"11111111-1111-1111-1111-111111111111","role":"authenticated"}', true);
set local role authenticated;

-- demote last owner should fail
select throws_ok(
  $$update public.incident_members set role='viewer' where incident_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid and user_id='11111111-1111-1111-1111-111111111111'::uuid$$,
  null,
  'cannot demote last owner'
);

-- delete last owner should fail
select throws_ok(
  $$delete from public.incident_members where incident_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid and user_id='11111111-1111-1111-1111-111111111111'::uuid$$,
  null,
  'cannot delete last owner'
);

-- change incident_id/user_id blocked
select throws_ok(
  $$update public.incident_members set user_id='22222222-2222-2222-2222-222222222222'::uuid where incident_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid and user_id='11111111-1111-1111-1111-111111111111'::uuid$$,
  null,
  'cannot reassign membership user_id'
);

select * from finish();
rollback;
PY