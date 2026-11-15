begin;

select plan(6);

insert into auth.users (id, instance_id, aud, role, email, encrypted_password, email_confirmed_at, created_at, updated_at)
values
  ('11111111-1111-1111-1111-111111111111'::uuid, '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'o@test.local', crypt('pw', gen_salt('bf')), now(), now(), now());

reset role;
insert into public.incidents (id, title, created_by) values ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid, 'inc', '11111111-1111-1111-1111-111111111111'::uuid);
insert into public.incident_members (incident_id, user_id, role) values ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid, '11111111-1111-1111-1111-111111111111'::uuid, 'analyst');

select set_config('request.jwt.claim.sub', '11111111-1111-1111-1111-111111111111', true);
select set_config('request.jwt.claims', '{"sub":"11111111-1111-1111-1111-111111111111","role":"authenticated"}', true);
set local role authenticated;
insert into public.processing_jobs (id, incident_id, job_type, idempotency_key)
values ('99999999-9999-9999-9999-999999999999'::uuid, 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid, 'sweep', 'key1');

-- invalid transition queued->succeeded
select throws_ok(
  $$update public.processing_jobs set state='succeeded', finished_at=now() where id='99999999-9999-9999-9999-999999999999'::uuid$$,
  null,
  'invalid transition blocked'
);

-- negative retry_count
select throws_ok(
  $$update public.processing_jobs set retry_count=-1 where id='99999999-9999-9999-9999-999999999999'::uuid$$,
  null,
  'negative retry_count blocked'
);

-- same-state metadata abuse
select throws_ok(
  $$update public.processing_jobs set claimed_by='x' where id='99999999-9999-9999-9999-999999999999'::uuid$$,
  null,
  'same-state metadata abuse blocked'
);

-- claimed without claimed_by/claimed_at
select throws_ok(
  $$update public.processing_jobs set state='claimed' where id='99999999-9999-9999-9999-999999999999'::uuid$$,
  null,
  'claimed without metadata blocked'
);

-- valid cancellation with finished_at
select lives_ok(
  $$update public.processing_jobs set state='cancelled', finished_at=now() where id='99999999-9999-9999-9999-999999999999'::uuid$$,
  'valid cancellation'
);

-- direct client update of state after terminal? cancelled->running invalid
select throws_ok(
  $$update public.processing_jobs set state='running', started_at=now() where id='99999999-9999-9999-9999-999999999999'::uuid$$,
  null,
  'terminal transition blocked'
);

select * from finish();
rollback;
PY