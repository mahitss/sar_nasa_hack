begin;

select plan(5);

-- anon cannot read incidents
set local role anon;
select is(
  (select count(*) from public.incidents)::int,
  0,
  'anon cannot read incidents (RLS hides all)'
);

-- anon cannot insert
select throws_ok(
  $$insert into public.incidents (title, created_by) values ('x', '11111111-1111-1111-1111-111111111111'::uuid)$$,
  null,
  'anon cannot insert incidents'
);

-- private schema not in search path exposed: function not callable by anon
set local role anon;
select throws_ok(
  $$select private.is_incident_member('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid)$$,
  null,
  'private helper not callable by anon'
);

-- authenticated can call submit_evidence_decision (function exists and granted)
reset role;
insert into auth.users (id, instance_id, aud, role, email, encrypted_password, email_confirmed_at, created_at, updated_at)
values ('11111111-1111-1111-1111-111111111111'::uuid, '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'o@test.local', crypt('pw', gen_salt('bf')), now(), now(), now());
select set_config('request.jwt.claim.sub', '11111111-1111-1111-1111-111111111111', true);
select set_config('request.jwt.claims', '{"sub":"11111111-1111-1111-1111-111111111111","role":"authenticated"}', true);
set local role authenticated;
select ok(
  has_function_privilege('authenticated', 'public.submit_evidence_decision(uuid,uuid,text,text)', 'EXECUTE'),
  'authenticated can execute review RPC'
);

-- anon cannot execute review RPC
set local role anon;
select ok(
  not has_function_privilege('anon', 'public.submit_evidence_decision(uuid,uuid,text,text)', 'EXECUTE'),
  'anon cannot execute review RPC'
);

select * from finish();
rollback;
PY