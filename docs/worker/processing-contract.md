# Worker processing contract

Job types and payloads are typed in `services/worker/src/worker/jobs.py`.

State machine: queued -> claimed -> running -> succeeded/failed/cancelled.

Users cannot directly mutate worker claim metadata or state. Trusted worker path owns transitions.

Idempotency key required per incident.

Unapproved water-candidate parameters are rejected.
