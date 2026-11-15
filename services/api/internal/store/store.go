package store

import (
	"context"
	"fmt"
	"sync"
	"sync/atomic"
	"time"

	"github.com/mahitss/rivet-api/internal/errors"
)

type Store struct {
	mu        sync.RWMutex
	incidents map[string]*Incident
	members   map[string]map[string]string // incident -> user -> role
	acq       map[string]*Acquisition
	evidence  map[string]*Evidence
	decisions map[string]*Decision
	jobs      map[string]*Job
	reports   map[string]*Report
	audit     map[string][]*AuditEvent
	seq       uint64
}

var _ Repository = (*Store)(nil)

func New() *Store {
	return &Store{
		incidents: map[string]*Incident{},
		members:   map[string]map[string]string{},
		acq:       map[string]*Acquisition{},
		evidence:  map[string]*Evidence{},
		decisions: map[string]*Decision{},
		jobs:      map[string]*Job{},
		reports:   map[string]*Report{},
		audit:     map[string][]*AuditEvent{},
	}
}

func (s *Store) newID() string {
	n := atomic.AddUint64(&s.seq, 1)
	return fmt.Sprintf("00000000-0000-0000-0000-%012d", n)
}

func (s *Store) ListIncidents(ctx context.Context) ([]*Incident, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := make([]*Incident, 0, len(s.incidents))
	for _, inc := range s.incidents {
		out = append(out, inc)
	}
	return out, nil
}

func (s *Store) GetIncident(ctx context.Context, id string) (*Incident, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	inc, ok := s.incidents[id]
	if !ok {
		return nil, errors.ErrNotFound
	}
	return inc, nil
}

func (s *Store) CreateIncident(ctx context.Context, inc *Incident) (*Incident, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if inc.ID == "" {
		inc.ID = s.newID()
	}
	if inc.CreatedAt.IsZero() {
		inc.CreatedAt = time.Now()
	}
	s.incidents[inc.ID] = inc
	if s.members[inc.ID] == nil {
		s.members[inc.ID] = map[string]string{}
	}
	s.members[inc.ID][inc.CreatedBy] = "owner"
	return inc, nil
}

func (s *Store) GetIncidentMemberRole(ctx context.Context, incidentID, userID string) (string, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	if m, ok := s.members[incidentID]; ok {
		if r, ok := m[userID]; ok {
			return r, nil
		}
	}
	return "", errors.ErrNotFound
}

func (s *Store) AddIncidentMember(ctx context.Context, incidentID, userID, role string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.members[incidentID] == nil {
		s.members[incidentID] = map[string]string{}
	}
	s.members[incidentID][userID] = role
	return nil
}

func (s *Store) ListAcquisitions(ctx context.Context, incidentID string) ([]*Acquisition, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := []*Acquisition{}
	for _, a := range s.acq {
		if a.IncidentID == incidentID {
			out = append(out, a)
		}
	}
	return out, nil
}

func (s *Store) GetAcquisition(ctx context.Context, incidentID, id string) (*Acquisition, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	a, ok := s.acq[id]
	if !ok || a.IncidentID != incidentID {
		return nil, errors.ErrNotFound
	}
	return a, nil
}

func (s *Store) CreateAcquisition(ctx context.Context, acq *Acquisition) (*Acquisition, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if acq.ID == "" {
		acq.ID = s.newID()
	}
	if acq.ProductMaturity == "" {
		acq.ProductMaturity = "provisional"
	}
	if acq.CreatedAt.IsZero() {
		acq.CreatedAt = time.Now()
	}
	s.acq[acq.ID] = acq
	return acq, nil
}

func (s *Store) ListEvidence(ctx context.Context, incidentID string) ([]*Evidence, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := []*Evidence{}
	for _, e := range s.evidence {
		if e.IncidentID == incidentID {
			out = append(out, e)
		}
	}
	return out, nil
}

func (s *Store) GetEvidence(ctx context.Context, incidentID, id string) (*Evidence, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	e, ok := s.evidence[id]
	if !ok || e.IncidentID != incidentID {
		return nil, errors.ErrNotFound
	}
	return e, nil
}

func (s *Store) CreateEvidence(ctx context.Context, ev *Evidence) (*Evidence, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if ev.ID == "" {
		ev.ID = s.newID()
	}
	if ev.ReviewState == "" {
		ev.ReviewState = "draft"
	}
	if ev.CreatedAt.IsZero() {
		ev.CreatedAt = time.Now()
	}
	s.evidence[ev.ID] = ev
	return ev, nil
}

func (s *Store) PatchEvidence(ctx context.Context, incidentID, id string, title, summary string) (*Evidence, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	e, ok := s.evidence[id]
	if !ok || e.IncidentID != incidentID {
		return nil, errors.ErrNotFound
	}
	if title != "" {
		e.Title = title
	}
	if summary != "" {
		e.Summary = summary
	}
	e.UpdatedAt = time.Now()
	return e, nil
}

func (s *Store) SubmitEvidenceDecision(ctx context.Context, incidentID, evidenceID, decision, rationale string) (*Decision, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	e, ok := s.evidence[evidenceID]
	if !ok || e.IncidentID != incidentID {
		return nil, errors.ErrNotFound
	}
	state := decision
	if state == "accept" {
		state = "accepted"
	} else if state == "reject" {
		state = "rejected"
	}
	e.ReviewState = state
	e.UpdatedAt = time.Now()

	d := &Decision{
		ID:         s.newID(),
		IncidentID: incidentID,
		EvidenceID: evidenceID,
		Decision:   decision,
		Rationale:  rationale,
		CreatedAt:  time.Now(),
	}
	s.decisions[d.ID] = d
	return d, nil
}

func (s *Store) GetDecision(ctx context.Context, id string) (*Decision, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	d, ok := s.decisions[id]
	if !ok {
		return nil, errors.ErrNotFound
	}
	return d, nil
}

func (s *Store) ListDecisionsForEvidence(ctx context.Context, incidentID, evidenceID string) ([]*Decision, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := []*Decision{}
	for _, d := range s.decisions {
		if d.IncidentID == incidentID && d.EvidenceID == evidenceID {
			out = append(out, d)
		}
	}
	return out, nil
}

func (s *Store) ListJobs(ctx context.Context, incidentID string) ([]*Job, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := []*Job{}
	for _, j := range s.jobs {
		if j.IncidentID == incidentID {
			out = append(out, j)
		}
	}
	return out, nil
}

func (s *Store) GetJob(ctx context.Context, incidentID, id string) (*Job, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	j, ok := s.jobs[id]
	if !ok || j.IncidentID != incidentID {
		return nil, errors.ErrNotFound
	}
	return j, nil
}

func (s *Store) CreateJob(ctx context.Context, job *Job) (*Job, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if job.ID == "" {
		job.ID = s.newID()
	}
	if job.State == "" {
		job.State = "queued"
	}
	if job.CreatedAt.IsZero() {
		job.CreatedAt = time.Now()
	}
	s.jobs[job.ID] = job
	return job, nil
}

func (s *Store) GetJobByID(ctx context.Context, id string) (*Job, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	j, ok := s.jobs[id]
	if !ok {
		return nil, errors.ErrNotFound
	}
	return j, nil
}

func (s *Store) ClaimNextJob(ctx context.Context, workerID string, leaseDuration time.Duration) (*Job, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	for _, j := range s.jobs {
		if j.State == "queued" {
			now := time.Now()
			exp := now.Add(leaseDuration)
			token := fmt.Sprintf("token-%d", now.UnixNano())
			j.State = "claimed"
			j.ClaimedBy = workerID
			j.ClaimedAt = &now
			j.LeaseToken = token
			j.LeaseExpiresAt = &exp
			j.AttemptID = fmt.Sprintf("att-%d", now.UnixNano())
			j.RetryCount++
			j.UpdatedAt = now
			return j, nil
		}
	}
	return nil, errors.ErrNotFound
}

func (s *Store) StartJob(ctx context.Context, id, workerID, leaseToken string) (*Job, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	j, ok := s.jobs[id]
	if !ok {
		return nil, errors.ErrNotFound
	}
	if j.ClaimedBy != workerID || j.LeaseToken != leaseToken || j.State != "claimed" {
		return nil, errors.ErrForbidden
	}
	now := time.Now()
	j.State = "running"
	j.StartedAt = &now
	j.UpdatedAt = now
	return j, nil
}

func (s *Store) HeartbeatJob(ctx context.Context, id, workerID, leaseToken string, extend time.Duration) (*Job, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	j, ok := s.jobs[id]
	if !ok {
		return nil, errors.ErrNotFound
	}
	if j.ClaimedBy != workerID || j.LeaseToken != leaseToken {
		return nil, errors.ErrForbidden
	}
	now := time.Now()
	exp := now.Add(extend)
	j.LeaseExpiresAt = &exp
	j.UpdatedAt = now
	return j, nil
}

func (s *Store) CompleteJob(ctx context.Context, id, workerID, leaseToken string, result map[string]interface{}) (*Job, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	j, ok := s.jobs[id]
	if !ok {
		return nil, errors.ErrNotFound
	}
	if j.ClaimedBy != workerID || j.LeaseToken != leaseToken || j.State != "running" {
		return nil, errors.ErrForbidden
	}
	now := time.Now()
	j.State = "succeeded"
	j.FinishedAt = &now
	j.Result = result
	j.UpdatedAt = now
	return j, nil
}

func (s *Store) FailJob(ctx context.Context, id, workerID, leaseToken, errorMessage string) (*Job, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	j, ok := s.jobs[id]
	if !ok {
		return nil, errors.ErrNotFound
	}
	if j.ClaimedBy != workerID || j.LeaseToken != leaseToken {
		return nil, errors.ErrForbidden
	}
	now := time.Now()
	j.State = "failed"
	if j.StartedAt == nil {
		j.StartedAt = &now
	}
	j.FinishedAt = &now
	j.ErrorMessage = errorMessage
	j.UpdatedAt = now
	return j, nil
}

func (s *Store) RecoverExpiredLeases(ctx context.Context, maxRetries int) (int, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	now := time.Now()
	count := 0
	for _, j := range s.jobs {
		if (j.State == "claimed" || j.State == "running") && j.LeaseExpiresAt != nil && j.LeaseExpiresAt.Before(now) {
			count++
			if j.RetryCount >= maxRetries {
				j.State = "failed"
				if j.StartedAt == nil {
					j.StartedAt = &now
				}
				j.FinishedAt = &now
				j.ErrorMessage = "lease expired and max retries exceeded"
			} else {
				j.State = "queued"
				j.ClaimedBy = ""
				j.ClaimedAt = nil
				j.StartedAt = nil
				j.LeaseToken = ""
				j.LeaseExpiresAt = nil
				j.AttemptID = ""
			}
			j.UpdatedAt = now
		}
	}
	return count, nil
}

func (s *Store) ListReports(ctx context.Context, incidentID string) ([]*Report, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := []*Report{}
	for _, r := range s.reports {
		if r.IncidentID == incidentID {
			out = append(out, r)
		}
	}
	return out, nil
}

func (s *Store) GetReport(ctx context.Context, incidentID, id string) (*Report, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	r, ok := s.reports[id]
	if !ok || r.IncidentID != incidentID {
		return nil, errors.ErrNotFound
	}
	return r, nil
}

func (s *Store) CreateReport(ctx context.Context, rep *Report) (*Report, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if rep.ID == "" {
		rep.ID = s.newID()
	}
	if rep.CreatedAt.IsZero() {
		rep.CreatedAt = time.Now()
	}
	s.reports[rep.ID] = rep
	return rep, nil
}

func (s *Store) ListAuditEvents(ctx context.Context, incidentID string) ([]*AuditEvent, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.audit[incidentID], nil
}

// Helper methods for in-memory membership check
func (s *Store) SetMember(incidentID, userID, role string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.members[incidentID] == nil {
		s.members[incidentID] = map[string]string{}
	}
	s.members[incidentID][userID] = role
}

func (s *Store) IsMember(incidentID, userID string) bool {
	s.mu.RLock()
	defer s.mu.RUnlock()
	if m, ok := s.members[incidentID]; ok {
		_, ok := m[userID]
		return ok
	}
	return false
}

func (s *Store) Role(incidentID, userID string) string {
	s.mu.RLock()
	defer s.mu.RUnlock()
	if m, ok := s.members[incidentID]; ok {
		return m[userID]
	}
	return ""
}
