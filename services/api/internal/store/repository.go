package store

import (
	"context"
	"encoding/json"
	"time"
)

type Incident struct {
	ID             string     `json:"id"`
	Title          string     `json:"title"`
	Description    string     `json:"description,omitempty"`
	DiscoveryWest  *float64   `json:"discovery_west,omitempty"`
	DiscoverySouth *float64   `json:"discovery_south,omitempty"`
	DiscoveryEast  *float64   `json:"discovery_east,omitempty"`
	DiscoveryNorth *float64   `json:"discovery_north,omitempty"`
	ArchivedAt     *time.Time `json:"archived_at,omitempty"`
	CreatedBy      string     `json:"created_by"`
	CreatedAt      time.Time  `json:"created_at"`
	UpdatedAt      time.Time  `json:"updated_at,omitempty"`
}

type Acquisition struct {
	ID              string    `json:"id"`
	IncidentID      string    `json:"incident_id"`
	SourceProvider  string    `json:"source_provider"`
	GranuleID       string    `json:"granule_id"`
	CRID            string    `json:"crid"`
	ProductMaturity string    `json:"product_maturity"`
	CreatedAt       time.Time `json:"created_at,omitempty"`
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
	UpdatedAt     time.Time `json:"updated_at,omitempty"`
}

type Decision struct {
	ID         string    `json:"id"`
	IncidentID string    `json:"incident_id"`
	EvidenceID string    `json:"evidence_id"`
	ReviewerID string    `json:"reviewer_id"`
	Decision   string    `json:"decision"`
	Rationale  string    `json:"rationale"`
	CreatedAt  time.Time `json:"created_at,omitempty"`
}

type Job struct {
	ID             string                 `json:"id"`
	IncidentID     string                 `json:"incident_id"`
	JobType        string                 `json:"job_type"`
	State          string                 `json:"state"`
	IdempotencyKey string                 `json:"idempotency_key"`
	ClaimedBy      string                 `json:"claimed_by,omitempty"`
	ClaimedAt      *time.Time             `json:"claimed_at,omitempty"`
	StartedAt      *time.Time             `json:"started_at,omitempty"`
	FinishedAt     *time.Time             `json:"finished_at,omitempty"`
	ErrorMessage   string                 `json:"error_message,omitempty"`
	RetryCount     int                    `json:"retry_count"`
	Payload        map[string]interface{} `json:"payload,omitempty"`
	LeaseToken     string                 `json:"lease_token,omitempty"`
	LeaseExpiresAt *time.Time             `json:"lease_expires_at,omitempty"`
	AttemptID      string                 `json:"attempt_id,omitempty"`
	Result         map[string]interface{} `json:"result,omitempty"`
	CreatedAt      time.Time              `json:"created_at,omitempty"`
	UpdatedAt      time.Time              `json:"updated_at,omitempty"`
}

type Report struct {
	ID          string                 `json:"id"`
	IncidentID  string                 `json:"incident_id"`
	Title       string                 `json:"title"`
	Content     map[string]interface{} `json:"content"`
	GeneratedBy string                 `json:"generated_by"`
	CreatedAt   time.Time              `json:"created_at,omitempty"`
}

type AuditEvent struct {
	ID          string          `json:"id"`
	ActorID     string          `json:"actor_id"`
	Action      string          `json:"action"`
	EntityTable string          `json:"entity_table"`
	EntityID    string          `json:"entity_id"`
	IncidentID  string          `json:"incident_id"`
	BeforeData  json.RawMessage `json:"before_data,omitempty"`
	AfterData   json.RawMessage `json:"after_data,omitempty"`
	OccurredAt  time.Time       `json:"occurred_at"`
}

type Repository interface {
	ListIncidents(ctx context.Context) ([]*Incident, error)
	GetIncident(ctx context.Context, id string) (*Incident, error)
	CreateIncident(ctx context.Context, inc *Incident) (*Incident, error)
	GetIncidentMemberRole(ctx context.Context, incidentID, userID string) (string, error)
	AddIncidentMember(ctx context.Context, incidentID, userID, role string) error

	ListAcquisitions(ctx context.Context, incidentID string) ([]*Acquisition, error)
	GetAcquisition(ctx context.Context, incidentID, id string) (*Acquisition, error)
	CreateAcquisition(ctx context.Context, acq *Acquisition) (*Acquisition, error)

	ListEvidence(ctx context.Context, incidentID string) ([]*Evidence, error)
	GetEvidence(ctx context.Context, incidentID, id string) (*Evidence, error)
	CreateEvidence(ctx context.Context, ev *Evidence) (*Evidence, error)
	PatchEvidence(ctx context.Context, incidentID, id string, title, summary string) (*Evidence, error)

	SubmitEvidenceDecision(ctx context.Context, incidentID, evidenceID, decision, rationale string) (*Decision, error)
	GetDecision(ctx context.Context, id string) (*Decision, error)
	ListDecisionsForEvidence(ctx context.Context, incidentID, evidenceID string) ([]*Decision, error)

	ListJobs(ctx context.Context, incidentID string) ([]*Job, error)
	GetJob(ctx context.Context, incidentID, id string) (*Job, error)
	GetJobByID(ctx context.Context, id string) (*Job, error)
	CreateJob(ctx context.Context, job *Job) (*Job, error)
	ClaimNextJob(ctx context.Context, workerID string, leaseDuration time.Duration) (*Job, error)
	StartJob(ctx context.Context, id, workerID, leaseToken string) (*Job, error)
	HeartbeatJob(ctx context.Context, id, workerID, leaseToken string, extend time.Duration) (*Job, error)
	CompleteJob(ctx context.Context, id, workerID, leaseToken string, result map[string]interface{}) (*Job, error)
	FailJob(ctx context.Context, id, workerID, leaseToken, errorMessage string) (*Job, error)
	RecoverExpiredLeases(ctx context.Context, maxRetries int) (int, error)

	ListReports(ctx context.Context, incidentID string) ([]*Report, error)
	GetReport(ctx context.Context, incidentID, id string) (*Report, error)
	CreateReport(ctx context.Context, rep *Report) (*Report, error)

	ListAuditEvents(ctx context.Context, incidentID string) ([]*AuditEvent, error)
}
