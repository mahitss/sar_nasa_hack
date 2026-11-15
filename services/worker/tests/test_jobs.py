from worker.jobs import Job

def test_valid_transition():
    j = Job(id="1", incident_id="i", job_type="sweep", idempotency_key="k")
    j.transition("claimed")
    assert j.state == "claimed"

def test_illegal_transition():
    j = Job(id="1", incident_id="i", job_type="sweep", idempotency_key="k")
    try:
        j.transition("succeeded")
        assert False
    except ValueError:
        pass

def test_same_state_noop_blocked():
    j = Job(id="1", incident_id="i", job_type="sweep", idempotency_key="k")
    try:
        j.transition("queued")
        assert False
    except ValueError:
        pass

def test_negative_retry():
    j = Job(id="1", incident_id="i", job_type="sweep", idempotency_key="k", retry_count=-1)
    try:
        j.validate()
        assert False
    except ValueError:
        pass

def test_missing_idempotency():
    j = Job(id="1", incident_id="i", job_type="sweep")
    try:
        j.validate()
        assert False
    except ValueError:
        pass
