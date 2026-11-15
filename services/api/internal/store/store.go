package store

import (
	"sync"
	"time"

	"github.com/mahitss/rivet-api/internal/auth"
)

type Incident struct {
	ID          string    `json:"id"`
	Title       string    `json:"title"`
	Description string    `json:"description"`
	CreatedBy   string    `json:"created_by"`
	CreatedAt   time.Time `json:"created_at"`
}

type Acquisition struct {
	ID              string `json:"id"`
	IncidentID      string `json:"incident_id"`
	SourceProvider  string `json:"source_provider"`
	GranuleID       string `json:"granule_id"`
	CRID            string `json:"crid"`
	ProductMaturity string `json:"product_maturity"`
}

type Evidence struct {
	ID            string    `json:"id"`
	IncidentID    string    `json:"incident_id"`
	AcquisitionID string    `json:"acquisition_id,omitempty"`
	ClaimLevel    string    `json:"claim_level"`
	EvidenceKind  string    `json:"evidence_kind"`
	Title         string    `json:"title"`
	Summary       string    `json:"summary"`
	SourcePath    string    `json:"source_path"`
	ReviewState   string    `json:"review_state"`
	CreatedBy     string    `json:"created_by"`
	CreatedAt     time.Time `json:"created_at"`
}

type Decision struct {
	ID         string `json:"id"`
	IncidentID string `json:"incident_id"`
	EvidenceID string `json:"evidence_id"`
	ReviewerID string `json:"reviewer_id"`
	Decision   string `json:"decision"`
	Rationale  string `json:"rationale"`
}

type Job struct {
	ID             string `json:"id"`
	IncidentID     string `json:"incident_id"`
	JobType        string `json:"job_type"`
	State          string `json:"state"`
	IdempotencyKey string `json:"idempotency_key"`
}

type Report struct {
	ID          string                 `json:"id"`
	IncidentID  string                 `json:"incident_id"`
	Title       string                 `json:"title"`
	Content     map[string]interface{} `json:"content"`
	GeneratedBy string                 `json:"generated_by"`
}

type Store struct {
	mu        sync.RWMutex
	incidents map[string]*Incident
	members   map[string]map[string]string // incident -> user -> role
	acq       map[string]*Acquisition
	evidence  map[string]*Evidence
	decisions map[string]*Decision
	jobs      map[string]*Job
	reports   map[string]*Report
}

func New() *Store {
	return &Store{
		incidents: map[string]*Incident{},
		members:   map[string]map[string]string{},
		acq:       map[string]*Acquisition{},
		evidence:  map[string]*Evidence{},
		decisions: map[string]*Decision{},
		jobs:      map[string]*Job{},
		reports:   map[string]*Report{},
	}
}

// Accessors
func (s *Store) Incidents() []*Incident {
	out := []*Incident{}
	for _, v := range s.incidents {
		out = append(out, v)
	}
	return out
}
func (s *Store) IncidentsGet(id string) (*Incident, bool) {
	v, ok := s.incidents[id]
	return v, ok
}
func (s *Store) IncidentsSet(v *Incident) { s.incidents[v.ID] = v }
func (s *Store) Acquisitions() []*Acquisition {
	out := []*Acquisition{}
	for _, v := range s.acq {
		out = append(out, v)
	}
	return out
}
func (s *Store) AcquisitionsSet(v *Acquisition) { s.acq[v.ID] = v }
func (s *Store) Evidence() []*Evidence {
	out := []*Evidence{}
	for _, v := range s.evidence {
		out = append(out, v)
	}
	return out
}
func (s *Store) EvidenceGet(id string) (*Evidence, bool) {
	v, ok := s.evidence[id]
	return v, ok
}
func (s *Store) EvidenceSet(v *Evidence)  { s.evidence[v.ID] = v }
func (s *Store) DecisionsSet(v *Decision) { s.decisions[v.ID] = v }
func (s *Store) Jobs() []*Job {
	out := []*Job{}
	for _, v := range s.jobs {
		out = append(out, v)
	}
	return out
}
func (s *Store) JobsGet(id string) (*Job, bool) {
	v, ok := s.jobs[id]
	return v, ok
}
func (s *Store) JobsSet(v *Job) { s.jobs[v.ID] = v }
func (s *Store) Reports() []*Report {
	out := []*Report{}
	for _, v := range s.reports {
		out = append(out, v)
	}
	return out
}
func (s *Store) ReportsGet(id string) (*Report, bool) {
	v, ok := s.reports[id]
	return v, ok
}
func (s *Store) ReportsSet(v *Report) { s.reports[v.ID] = v }

func (s *Store) Lock()    { s.mu.Lock() }
func (s *Store) Unlock()  { s.mu.Unlock() }
func (s *Store) RLock()   { s.mu.RLock() }
func (s *Store) RUnlock() { s.mu.RUnlock() }
func (s *Store) SetMember(incidentID, userID, role string) {
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

var _ = auth.Identity{}
