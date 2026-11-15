# Go API identity and transaction flow

1. Go verifies the Supabase JWT (signature, expiry, issuer, audience).
2. On success, begin a pgx transaction.
3. Set transaction-local verified JWT claims.
4. `SET LOCAL ROLE authenticated`.
5. Execute application queries under RLS.
6. Commit or rollback (transaction-local settings reset automatically).

Rules:
- Never trust a user id supplied by the browser.
- Never use the service-role key for ordinary requests.
- Never use session-level `SET` for identity.
- RLS remains enabled on every application table.
- Review decisions go through `public.submit_evidence_decision` RPC.
- Processing job state changes are server/worker-only.
