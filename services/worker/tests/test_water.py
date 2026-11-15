from worker.processing import water_candidate_allowed

def test_requires_approval():
    params = {"threshold_db": 1, "min_pixels": 1, "max_pixels": 10, "approved_by": "architect", "approved_at": "2026-01-01"}
    assert water_candidate_allowed(params)

def test_unapproved_rejected():
    params = {"threshold_db": 1, "min_pixels": 1, "max_pixels": 10}
    assert not water_candidate_allowed(params)

def test_empty_rejected():
    assert not water_candidate_allowed({})
