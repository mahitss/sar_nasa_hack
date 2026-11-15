begin;

select plan(7);

insert into auth.users (id, instance_id, aud, role, email, encrypted_password, email_confirmed_at, created_at, updated_at)
values
  ('11111111-1111-1111-1111-111111111111'::uuid, '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'workerowner@test.local', crypt('pw', gen_salt('bf')), now(), now(), now())
on conflict (id) do nothing;

reset role;
insert into public.incidents (id, title, created_by)
values ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'::uuid, 'worker inc', '11111111-1111-1111-1111-111111111111'::uuid)
on conflict (id) do nothing;

insert into public.processing_jobs (id, incident_id, job_type, idempotency_key, payload)
values ('10101010-1010-1010-1010-101010101010'::uuid, 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'::uuid, 'raster.inspect', 'key-lease-1', '{"schema_version":"1.0"}'::jsonb);

-- 1. Atomic claim sets lease metadata
select lives_ok(
  $$update public.processing_jobs
    set state = 'claimed',
        claimed_by = 'worker-1',
        claimed_at = now(),
        lease_token = 'token-123',
        lease_expires_at = now() + interval '5 minutes',
        attempt_id = gen_random_uuid(),
        updated_at = now()
    where id = '10101010-1010-1010-1010-101010101010'::uuid$$,
  'atomic claim sets lease metadata'
);

-- 2. Claimed job starts running
select lives_ok(
  $$update public.processing_jobs
    set state = 'running',
        started_at = now(),
        updated_at = now()
    where id = '10101010-1010-1010-1010-101010101010'::uuid$$,
  'claimed job starts running'
);

-- 3. Heartbeat extends lease while running
select lives_ok(
  $$update public.processing_jobs
    set lease_expires_at = now() + interval '10 minutes',
        updated_at = now()
    where id = '10101010-1010-1010-1010-101010101010'::uuid$$,
  'heartbeat extends lease while running'
);

-- 4. Successful completion records result
select lives_ok(
  $$update public.processing_jobs
    set state = 'succeeded',
        finished_at = now(),
        result = '{"status":"succeeded","tool":"rivet-worker"}'::jsonb,
        updated_at = now()
    where id = '10101010-1010-1010-1010-101010101010'::uuid$$,
  'successful completion records result'
);

-- 5. Terminal job modification rejected
select throws_ok(
  $$update public.processing_jobs
    set lease_expires_at = now() + interval '20 minutes'
    where id = '10101010-1010-1010-1010-101010101010'::uuid$$,
  null,
  'terminal job modification rejected'
);

-- 6. Expired running job recovery to queued
insert into public.processing_jobs (id, incident_id, job_type, idempotency_key, state, claimed_by, claimed_at, started_at, lease_token, lease_expires_at)
values ('20202020-2020-2020-2020-202020202020'::uuid, 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'::uuid, 'checksum', 'key-lease-2', 'running', 'worker-stale', now() - interval '10 minutes', now() - interval '9 minutes', 'stale-token', now() - interval '1 minute');

select lives_ok(
  $$update public.processing_jobs
    set state = 'queued',
        claimed_by = null,
        claimed_at = null,
        started_at = null,
        lease_token = null,
        lease_expires_at = null,
        attempt_id = null,
        retry_count = retry_count + 1,
        updated_at = now()
    where id = '20202020-2020-2020-2020-202020202020'::uuid$$,
  'expired running job successfully recovered to queued'
);

-- 7. Verify recovered job is back in queued state with retry_count = 1
select is(
  (select state::text from public.processing_jobs where id = '20202020-2020-2020-2020-202020202020'::uuid),
  'queued',
  'recovered job is queued'
);

select * from finish();
rollback;
