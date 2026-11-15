package database

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgtype"

	"github.com/mahitss/rivet-api/internal/database/db"
	"github.com/mahitss/rivet-api/internal/store"
)

type PostgresRepository struct{}

var _ store.Repository = (*PostgresRepository)(nil)

func NewPostgresRepository() *PostgresRepository {
	return &PostgresRepository{}
}

func getQueries(ctx context.Context) (*db.Queries, error) {
	tx, ok := TxFromContext(ctx)
	if !ok {
		return nil, errors.New("user-scoped operation requires an active transaction")
	}
	return db.New(tx), nil
}

func parseUUID(s string) (pgtype.UUID, error) {
	if s == "" {
		return pgtype.UUID{}, nil
	}
	var u pgtype.UUID
	if err := u.Scan(s); err != nil {
		return pgtype.UUID{}, err
	}
	return u, nil
}

func formatUUID(u pgtype.UUID) string {
	if !u.Valid {
		return ""
	}
	src := u.Bytes
	return fmt.Sprintf("%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-%02x%02x%02x%02x%02x%02x",
		src[0], src[1], src[2], src[3],
		src[4], src[5],
		src[6], src[7],
		src[8], src[9],
		src[10], src[11], src[12], src[13], src[14], src[15])
}

func newUUID() pgtype.UUID {
	var b [16]byte
	_, _ = rand.Read(b[:])
	b[6] = (b[6] & 0x0f) | 0x40
	b[8] = (b[8] & 0x3f) | 0x80
	return pgtype.UUID{Bytes: b, Valid: true}
}

func textToString(t pgtype.Text) string {
	if t.Valid {
		return t.String
	}
	return ""
}

func stringToText(s string) pgtype.Text {
	return pgtype.Text{String: s, Valid: s != ""}
}

func timestamptzToTime(t pgtype.Timestamptz) time.Time {
	if t.Valid {
		return t.Time
	}
	return time.Time{}
}

func timestamptzToPtr(t pgtype.Timestamptz) *time.Time {
	if t.Valid {
		return &t.Time
	}
	return nil
}

func float8ToPtr(f pgtype.Float8) *float64 {
	if f.Valid {
		return &f.Float64
	}
	return nil
}

func ptrToFloat8(f *float64) pgtype.Float8 {
	if f != nil {
		return pgtype.Float8{Float64: *f, Valid: true}
	}
	return pgtype.Float8{}
}

func timeToTimestamptz(t time.Time) pgtype.Timestamptz {
	return pgtype.Timestamptz{Time: t, Valid: true}
}

func newRandomToken() string {
	b := make([]byte, 16)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}

func bytesToMap(b []byte) map[string]interface{} {
	if len(b) == 0 {
		return nil
	}
	var m map[string]interface{}
	if err := json.Unmarshal(b, &m); err != nil {
		return nil
	}
	return m
}

func mapToBytes(m map[string]interface{}) []byte {
	if m == nil {
		return []byte("{}")
	}
	b, err := json.Marshal(m)
	if err != nil {
		return []byte("{}")
	}
	return b
}

// Incidents
func (r *PostgresRepository) ListIncidents(ctx context.Context) ([]*store.Incident, error) {
	q, err := getQueries(ctx)
	if err != nil {
		return nil, err
	}
	rows, err := q.ListIncidents(ctx)
	if err != nil {
		return nil, err
	}
	out := make([]*store.Incident, 0, len(rows))
	for _, row := range rows {
		out = append(out, toStoreIncident(row))
	}
	return out, nil
}

func (r *PostgresRepository) GetIncident(ctx context.Context, id string) (*store.Incident, error) {
	q, err := getQueries(ctx)
	if err != nil {
		return nil, err
	}
	uid, err := parseUUID(id)
	if err != nil || !uid.Valid {
		return nil, pgx.ErrNoRows
	}
	row, err := q.GetIncident(ctx, uid)
	if err != nil {
		return nil, err
	}
	return toStoreIncident(row), nil
}

func (r *PostgresRepository) CreateIncident(ctx context.Context, inc *store.Incident) (*store.Incident, error) {
	q, err := getQueries(ctx)
	if err != nil {
		return nil, err
	}
	uid, err := parseUUID(inc.ID)
	if err != nil || !uid.Valid {
		uid = newUUID()
	}
	creatorUID, err := parseUUID(inc.CreatedBy)
	if err != nil {
		return nil, err
	}
	arg := db.CreateIncidentParams{
		ID:             uid,
		Title:          inc.Title,
		Description:    stringToText(inc.Description),
		DiscoveryWest:  ptrToFloat8(inc.DiscoveryWest),
		DiscoverySouth: ptrToFloat8(inc.DiscoverySouth),
		DiscoveryEast:  ptrToFloat8(inc.DiscoveryEast),
		DiscoveryNorth: ptrToFloat8(inc.DiscoveryNorth),
		CreatedBy:      creatorUID,
	}
	row, err := q.CreateIncident(ctx, arg)
	if err != nil {
		return nil, err
	}
	return toStoreIncident(row), nil
}

func (r *PostgresRepository) GetIncidentMemberRole(ctx context.Context, incidentID, userID string) (string, error) {
	q, err := getQueries(ctx)
	if err != nil {
		return "", err
	}
	incUID, err := parseUUID(incidentID)
	if err != nil || !incUID.Valid {
		return "", pgx.ErrNoRows
	}
	userUID, err := parseUUID(userID)
	if err != nil || !userUID.Valid {
		return "", pgx.ErrNoRows
	}
	role, err := q.GetIncidentMemberRole(ctx, db.GetIncidentMemberRoleParams{
		IncidentID: incUID,
		UserID:     userUID,
	})
	if err != nil {
		return "", err
	}
	return fmt.Sprint(role), nil
}

func (r *PostgresRepository) AddIncidentMember(ctx context.Context, incidentID, userID, role string) error {
	q, err := getQueries(ctx)
	if err != nil {
		return err
	}
	incUID, err := parseUUID(incidentID)
	if err != nil || !incUID.Valid {
		return pgx.ErrNoRows
	}
	userUID, err := parseUUID(userID)
	if err != nil || !userUID.Valid {
		return pgx.ErrNoRows
	}
	_, err = q.AddIncidentMember(ctx, db.AddIncidentMemberParams{
		IncidentID: incUID,
		UserID:     userUID,
		Role:       role,
	})
	return err
}

func toStoreIncident(row db.Incident) *store.Incident {
	return &store.Incident{
		ID:             formatUUID(row.ID),
		Title:          row.Title,
		Description:    textToString(row.Description),
		DiscoveryWest:  float8ToPtr(row.DiscoveryWest),
		DiscoverySouth: float8ToPtr(row.DiscoverySouth),
		DiscoveryEast:  float8ToPtr(row.DiscoveryEast),
		DiscoveryNorth: float8ToPtr(row.DiscoveryNorth),
		ArchivedAt:     timestamptzToPtr(row.ArchivedAt),
		CreatedBy:      formatUUID(row.CreatedBy),
		CreatedAt:      timestamptzToTime(row.CreatedAt),
		UpdatedAt:      timestamptzToTime(row.UpdatedAt),
	}
}

// Acquisitions
func (r *PostgresRepository) ListAcquisitions(ctx context.Context, incidentID string) ([]*store.Acquisition, error) {
	q, err := getQueries(ctx)
	if err != nil {
		return nil, err
	}
	incUID, err := parseUUID(incidentID)
	if err != nil || !incUID.Valid {
		return nil, pgx.ErrNoRows
	}
	rows, err := q.ListAcquisitions(ctx, incUID)
	if err != nil {
		return nil, err
	}
	out := make([]*store.Acquisition, 0, len(rows))
	for _, row := range rows {
		out = append(out, toStoreAcquisition(row))
	}
	return out, nil
}

func (r *PostgresRepository) GetAcquisition(ctx context.Context, incidentID, id string) (*store.Acquisition, error) {
	q, err := getQueries(ctx)
	if err != nil {
		return nil, err
	}
	incUID, err := parseUUID(incidentID)
	if err != nil || !incUID.Valid {
		return nil, pgx.ErrNoRows
	}
	acqUID, err := parseUUID(id)
	if err != nil || !acqUID.Valid {
		return nil, pgx.ErrNoRows
	}
	row, err := q.GetAcquisition(ctx, db.GetAcquisitionParams{
		IncidentID: incUID,
		ID:         acqUID,
	})
	if err != nil {
		return nil, err
	}
	return toStoreAcquisition(row), nil
}

func (r *PostgresRepository) CreateAcquisition(ctx context.Context, acq *store.Acquisition) (*store.Acquisition, error) {
	q, err := getQueries(ctx)
	if err != nil {
		return nil, err
	}
	uid, err := parseUUID(acq.ID)
	if err != nil || !uid.Valid {
		uid = newUUID()
	}
	incUID, err := parseUUID(acq.IncidentID)
	if err != nil || !incUID.Valid {
		return nil, pgx.ErrNoRows
	}
	maturity := acq.ProductMaturity
	if maturity == "" {
		maturity = "provisional"
	}
	row, err := q.CreateAcquisition(ctx, db.CreateAcquisitionParams{
		ID:              uid,
		IncidentID:      incUID,
		SourceProvider:  acq.SourceProvider,
		GranuleID:       acq.GranuleID,
		Crid:            acq.CRID,
		ProductMaturity: maturity,
	})
	if err != nil {
		return nil, err
	}
	return toStoreAcquisition(row), nil
}

func toStoreAcquisition(row db.Acquisition) *store.Acquisition {
	return &store.Acquisition{
		ID:              formatUUID(row.ID),
		IncidentID:      formatUUID(row.IncidentID),
		SourceProvider:  row.SourceProvider,
		GranuleID:       row.GranuleID,
		CRID:            row.Crid,
		ProductMaturity: fmt.Sprint(row.ProductMaturity),
		CreatedAt:       timestamptzToTime(row.CreatedAt),
	}
}

// Evidence
func (r *PostgresRepository) ListEvidence(ctx context.Context, incidentID string) ([]*store.Evidence, error) {
	q, err := getQueries(ctx)
	if err != nil {
		return nil, err
	}
	incUID, err := parseUUID(incidentID)
	if err != nil || !incUID.Valid {
		return nil, pgx.ErrNoRows
	}
	rows, err := q.ListEvidence(ctx, incUID)
	if err != nil {
		return nil, err
	}
	out := make([]*store.Evidence, 0, len(rows))
	for _, row := range rows {
		out = append(out, toStoreEvidence(row))
	}
	return out, nil
}

func (r *PostgresRepository) GetEvidence(ctx context.Context, incidentID, id string) (*store.Evidence, error) {
	q, err := getQueries(ctx)
	if err != nil {
		return nil, err
	}
	incUID, err := parseUUID(incidentID)
	if err != nil || !incUID.Valid {
		return nil, pgx.ErrNoRows
	}
	evUID, err := parseUUID(id)
	if err != nil || !evUID.Valid {
		return nil, pgx.ErrNoRows
	}
	row, err := q.GetEvidence(ctx, db.GetEvidenceParams{
		IncidentID: incUID,
		ID:         evUID,
	})
	if err != nil {
		return nil, err
	}
	return toStoreEvidence(row), nil
}

func (r *PostgresRepository) CreateEvidence(ctx context.Context, ev *store.Evidence) (*store.Evidence, error) {
	q, err := getQueries(ctx)
	if err != nil {
		return nil, err
	}
	uid, err := parseUUID(ev.ID)
	if err != nil || !uid.Valid {
		uid = newUUID()
	}
	incUID, err := parseUUID(ev.IncidentID)
	if err != nil || !incUID.Valid {
		return nil, pgx.ErrNoRows
	}
	var acqUID pgtype.UUID
	if ev.AcquisitionID != "" {
		acqUID, _ = parseUUID(ev.AcquisitionID)
	}
	creatorUID, err := parseUUID(ev.CreatedBy)
	if err != nil || !creatorUID.Valid {
		return nil, errors.New("invalid created_by uuid")
	}
	claimLevel := ev.ClaimLevel
	if claimLevel == "" {
		claimLevel = "observation"
	}
	evidenceKind := ev.EvidenceKind
	if evidenceKind == "" {
		evidenceKind = "observation"
	}

	row, err := q.CreateEvidence(ctx, db.CreateEvidenceParams{
		ID:            uid,
		IncidentID:    incUID,
		AcquisitionID: acqUID,
		Title:         ev.Title,
		Summary:       ev.Summary,
		SourcePath:    ev.SourcePath,
		CreatedBy:     creatorUID,
		ClaimLevel:    claimLevel,
		EvidenceKind:  evidenceKind,
	})
	if err != nil {
		return nil, err
	}
	return toStoreEvidence(row), nil
}

func (r *PostgresRepository) PatchEvidence(ctx context.Context, incidentID, id string, title, summary string) (*store.Evidence, error) {
	q, err := getQueries(ctx)
	if err != nil {
		return nil, err
	}
	incUID, err := parseUUID(incidentID)
	if err != nil || !incUID.Valid {
		return nil, pgx.ErrNoRows
	}
	evUID, err := parseUUID(id)
	if err != nil || !evUID.Valid {
		return nil, pgx.ErrNoRows
	}
	row, err := q.PatchEvidence(ctx, db.PatchEvidenceParams{
		IncidentID: incUID,
		ID:         evUID,
		Title:      title,
		Summary:    summary,
	})
	if err != nil {
		return nil, err
	}
	return toStoreEvidence(row), nil
}

func toStoreEvidence(row db.EvidenceRecord) *store.Evidence {
	var acqID string
	if row.AcquisitionID.Valid {
		acqID = formatUUID(row.AcquisitionID)
	}
	return &store.Evidence{
		ID:            formatUUID(row.ID),
		IncidentID:    formatUUID(row.IncidentID),
		AcquisitionID: acqID,
		ClaimLevel:    fmt.Sprint(row.ClaimLevel),
		EvidenceKind:  fmt.Sprint(row.EvidenceKind),
		Title:         row.Title,
		Summary:       row.Summary,
		SourcePath:    row.SourcePath,
		ReviewState:   fmt.Sprint(row.ReviewState),
		CreatedBy:     formatUUID(row.CreatedBy),
		CreatedAt:     timestamptzToTime(row.CreatedAt),
		UpdatedAt:     timestamptzToTime(row.UpdatedAt),
	}
}

// Decisions
func (r *PostgresRepository) SubmitEvidenceDecision(ctx context.Context, incidentID, evidenceID, decision, rationale string) (*store.Decision, error) {
	q, err := getQueries(ctx)
	if err != nil {
		return nil, err
	}
	incUID, err := parseUUID(incidentID)
	if err != nil || !incUID.Valid {
		return nil, pgx.ErrNoRows
	}
	evUID, err := parseUUID(evidenceID)
	if err != nil || !evUID.Valid {
		return nil, pgx.ErrNoRows
	}
	decID, err := q.SubmitEvidenceDecision(ctx, db.SubmitEvidenceDecisionParams{
		PIncidentID:       incUID,
		PEvidenceRecordID: evUID,
		PDecision:         decision,
		PRationale:        rationale,
	})
	if err != nil {
		return nil, err
	}
	row, err := q.GetDecision(ctx, decID)
	if err != nil {
		return nil, err
	}
	return toStoreDecision(row), nil
}

func (r *PostgresRepository) GetDecision(ctx context.Context, id string) (*store.Decision, error) {
	q, err := getQueries(ctx)
	if err != nil {
		return nil, err
	}
	decUID, err := parseUUID(id)
	if err != nil || !decUID.Valid {
		return nil, pgx.ErrNoRows
	}
	row, err := q.GetDecision(ctx, decUID)
	if err != nil {
		return nil, err
	}
	return toStoreDecision(row), nil
}

func (r *PostgresRepository) ListDecisionsForEvidence(ctx context.Context, incidentID, evidenceID string) ([]*store.Decision, error) {
	q, err := getQueries(ctx)
	if err != nil {
		return nil, err
	}
	incUID, err := parseUUID(incidentID)
	if err != nil || !incUID.Valid {
		return nil, pgx.ErrNoRows
	}
	evUID, err := parseUUID(evidenceID)
	if err != nil || !evUID.Valid {
		return nil, pgx.ErrNoRows
	}
	rows, err := q.ListDecisionsForEvidence(ctx, db.ListDecisionsForEvidenceParams{
		IncidentID:       incUID,
		EvidenceRecordID: evUID,
	})
	if err != nil {
		return nil, err
	}
	out := make([]*store.Decision, 0, len(rows))
	for _, row := range rows {
		out = append(out, toStoreDecision(row))
	}
	return out, nil
}

func toStoreDecision(row db.Decision) *store.Decision {
	return &store.Decision{
		ID:         formatUUID(row.ID),
		IncidentID: formatUUID(row.IncidentID),
		EvidenceID: formatUUID(row.EvidenceRecordID),
		ReviewerID: formatUUID(row.ReviewerID),
		Decision:   row.Decision,
		Rationale:  textToString(row.Rationale),
		CreatedAt:  timestamptzToTime(row.CreatedAt),
	}
}

// Processing Jobs
func (r *PostgresRepository) ListJobs(ctx context.Context, incidentID string) ([]*store.Job, error) {
	q, err := getQueries(ctx)
	if err != nil {
		return nil, err
	}
	incUID, err := parseUUID(incidentID)
	if err != nil || !incUID.Valid {
		return nil, pgx.ErrNoRows
	}
	rows, err := q.ListJobs(ctx, incUID)
	if err != nil {
		return nil, err
	}
	out := make([]*store.Job, 0, len(rows))
	for _, row := range rows {
		out = append(out, toStoreJob(row.ID, row.IncidentID, row.JobType, row.State, row.ClaimedBy, row.ClaimedAt, row.StartedAt, row.FinishedAt, row.ErrorMessage, row.RetryCount, row.IdempotencyKey, row.Payload, row.LeaseToken, row.LeaseExpiresAt, row.AttemptID, row.Result, row.CreatedAt, row.UpdatedAt))
	}
	return out, nil
}

func (r *PostgresRepository) GetJob(ctx context.Context, incidentID, id string) (*store.Job, error) {
	q, err := getQueries(ctx)
	if err != nil {
		return nil, err
	}
	incUID, err := parseUUID(incidentID)
	if err != nil || !incUID.Valid {
		return nil, pgx.ErrNoRows
	}
	jobUID, err := parseUUID(id)
	if err != nil || !jobUID.Valid {
		return nil, pgx.ErrNoRows
	}
	row, err := q.GetJob(ctx, db.GetJobParams{
		IncidentID: incUID,
		ID:         jobUID,
	})
	if err != nil {
		return nil, err
	}
	return toStoreJob(row.ID, row.IncidentID, row.JobType, row.State, row.ClaimedBy, row.ClaimedAt, row.StartedAt, row.FinishedAt, row.ErrorMessage, row.RetryCount, row.IdempotencyKey, row.Payload, row.LeaseToken, row.LeaseExpiresAt, row.AttemptID, row.Result, row.CreatedAt, row.UpdatedAt), nil
}

func (r *PostgresRepository) GetJobByID(ctx context.Context, id string) (*store.Job, error) {
	q, err := getQueries(ctx)
	if err != nil {
		return nil, err
	}
	jobUID, err := parseUUID(id)
	if err != nil || !jobUID.Valid {
		return nil, pgx.ErrNoRows
	}
	row, err := q.GetJobByID(ctx, jobUID)
	if err != nil {
		return nil, err
	}
	return toStoreJob(row.ID, row.IncidentID, row.JobType, row.State, row.ClaimedBy, row.ClaimedAt, row.StartedAt, row.FinishedAt, row.ErrorMessage, row.RetryCount, row.IdempotencyKey, row.Payload, row.LeaseToken, row.LeaseExpiresAt, row.AttemptID, row.Result, row.CreatedAt, row.UpdatedAt), nil
}

func (r *PostgresRepository) CreateJob(ctx context.Context, job *store.Job) (*store.Job, error) {
	q, err := getQueries(ctx)
	if err != nil {
		return nil, err
	}
	uid, err := parseUUID(job.ID)
	if err != nil || !uid.Valid {
		uid = newUUID()
	}
	incUID, err := parseUUID(job.IncidentID)
	if err != nil || !incUID.Valid {
		return nil, pgx.ErrNoRows
	}
	payloadBytes := mapToBytes(job.Payload)
	row, err := q.CreateJob(ctx, db.CreateJobParams{
		ID:             uid,
		IncidentID:     incUID,
		JobType:        job.JobType,
		IdempotencyKey: job.IdempotencyKey,
		Payload:        payloadBytes,
	})
	if err != nil {
		return nil, err
	}
	return toStoreJob(row.ID, row.IncidentID, row.JobType, row.State, row.ClaimedBy, row.ClaimedAt, row.StartedAt, row.FinishedAt, row.ErrorMessage, row.RetryCount, row.IdempotencyKey, row.Payload, row.LeaseToken, row.LeaseExpiresAt, row.AttemptID, row.Result, row.CreatedAt, row.UpdatedAt), nil
}

func (r *PostgresRepository) ClaimNextJob(ctx context.Context, workerID string, leaseDuration time.Duration) (*store.Job, error) {
	q, err := getQueries(ctx)
	if err != nil {
		return nil, err
	}
	leaseToken := newRandomToken()
	attemptID := newUUID()
	expiresAt := timeToTimestamptz(time.Now().Add(leaseDuration))
	row, err := q.ClaimNextJob(ctx, db.ClaimNextJobParams{
		ClaimedBy:      stringToText(workerID),
		LeaseToken:     stringToText(leaseToken),
		LeaseExpiresAt: expiresAt,
		AttemptID:      attemptID,
	})
	if err != nil {
		return nil, err
	}
	return toStoreJob(row.ID, row.IncidentID, row.JobType, row.State, row.ClaimedBy, row.ClaimedAt, row.StartedAt, row.FinishedAt, row.ErrorMessage, row.RetryCount, row.IdempotencyKey, row.Payload, row.LeaseToken, row.LeaseExpiresAt, row.AttemptID, row.Result, row.CreatedAt, row.UpdatedAt), nil
}

func (r *PostgresRepository) StartJob(ctx context.Context, id, workerID, leaseToken string) (*store.Job, error) {
	q, err := getQueries(ctx)
	if err != nil {
		return nil, err
	}
	uid, err := parseUUID(id)
	if err != nil || !uid.Valid {
		return nil, pgx.ErrNoRows
	}
	row, err := q.StartJob(ctx, db.StartJobParams{
		ID:         uid,
		ClaimedBy:  stringToText(workerID),
		LeaseToken: stringToText(leaseToken),
	})
	if err != nil {
		return nil, err
	}
	return toStoreJob(row.ID, row.IncidentID, row.JobType, row.State, row.ClaimedBy, row.ClaimedAt, row.StartedAt, row.FinishedAt, row.ErrorMessage, row.RetryCount, row.IdempotencyKey, row.Payload, row.LeaseToken, row.LeaseExpiresAt, row.AttemptID, row.Result, row.CreatedAt, row.UpdatedAt), nil
}

func (r *PostgresRepository) HeartbeatJob(ctx context.Context, id, workerID, leaseToken string, extend time.Duration) (*store.Job, error) {
	q, err := getQueries(ctx)
	if err != nil {
		return nil, err
	}
	uid, err := parseUUID(id)
	if err != nil || !uid.Valid {
		return nil, pgx.ErrNoRows
	}
	expiresAt := timeToTimestamptz(time.Now().Add(extend))
	row, err := q.HeartbeatJob(ctx, db.HeartbeatJobParams{
		ID:             uid,
		ClaimedBy:      stringToText(workerID),
		LeaseExpiresAt: expiresAt,
		LeaseToken:     stringToText(leaseToken),
	})
	if err != nil {
		return nil, err
	}
	return toStoreJob(row.ID, row.IncidentID, row.JobType, row.State, row.ClaimedBy, row.ClaimedAt, row.StartedAt, row.FinishedAt, row.ErrorMessage, row.RetryCount, row.IdempotencyKey, row.Payload, row.LeaseToken, row.LeaseExpiresAt, row.AttemptID, row.Result, row.CreatedAt, row.UpdatedAt), nil
}

func (r *PostgresRepository) CompleteJob(ctx context.Context, id, workerID, leaseToken string, result map[string]interface{}) (*store.Job, error) {
	q, err := getQueries(ctx)
	if err != nil {
		return nil, err
	}
	uid, err := parseUUID(id)
	if err != nil || !uid.Valid {
		return nil, pgx.ErrNoRows
	}
	resultBytes := mapToBytes(result)
	row, err := q.CompleteJob(ctx, db.CompleteJobParams{
		ID:         uid,
		ClaimedBy:  stringToText(workerID),
		LeaseToken: stringToText(leaseToken),
		Result:     resultBytes,
	})
	if err != nil {
		return nil, err
	}
	return toStoreJob(row.ID, row.IncidentID, row.JobType, row.State, row.ClaimedBy, row.ClaimedAt, row.StartedAt, row.FinishedAt, row.ErrorMessage, row.RetryCount, row.IdempotencyKey, row.Payload, row.LeaseToken, row.LeaseExpiresAt, row.AttemptID, row.Result, row.CreatedAt, row.UpdatedAt), nil
}

func (r *PostgresRepository) FailJob(ctx context.Context, id, workerID, leaseToken, errorMessage string) (*store.Job, error) {
	q, err := getQueries(ctx)
	if err != nil {
		return nil, err
	}
	uid, err := parseUUID(id)
	if err != nil || !uid.Valid {
		return nil, pgx.ErrNoRows
	}
	row, err := q.FailJob(ctx, db.FailJobParams{
		ID:           uid,
		ClaimedBy:    stringToText(workerID),
		LeaseToken:   stringToText(leaseToken),
		ErrorMessage: stringToText(errorMessage),
	})
	if err != nil {
		return nil, err
	}
	return toStoreJob(row.ID, row.IncidentID, row.JobType, row.State, row.ClaimedBy, row.ClaimedAt, row.StartedAt, row.FinishedAt, row.ErrorMessage, row.RetryCount, row.IdempotencyKey, row.Payload, row.LeaseToken, row.LeaseExpiresAt, row.AttemptID, row.Result, row.CreatedAt, row.UpdatedAt), nil
}

func (r *PostgresRepository) RecoverExpiredLeases(ctx context.Context, maxRetries int) (int, error) {
	q, err := getQueries(ctx)
	if err != nil {
		return 0, err
	}
	requeued, err := q.RecoverExpiredLeasesToQueued(ctx, int32(maxRetries))
	if err != nil {
		return 0, err
	}
	failed, err := q.FailExhaustedExpiredLeases(ctx, int32(maxRetries))
	if err != nil {
		return len(requeued), err
	}
	return len(requeued) + len(failed), nil
}

func toStoreJob(
	id pgtype.UUID,
	incidentID pgtype.UUID,
	jobType string,
	state interface{},
	claimedBy pgtype.Text,
	claimedAt pgtype.Timestamptz,
	startedAt pgtype.Timestamptz,
	finishedAt pgtype.Timestamptz,
	errorMessage pgtype.Text,
	retryCount int32,
	idempotencyKey string,
	payload []byte,
	leaseToken pgtype.Text,
	leaseExpiresAt pgtype.Timestamptz,
	attemptID pgtype.UUID,
	result []byte,
	createdAt pgtype.Timestamptz,
	updatedAt pgtype.Timestamptz,
) *store.Job {
	return &store.Job{
		ID:             formatUUID(id),
		IncidentID:     formatUUID(incidentID),
		JobType:        jobType,
		State:          fmt.Sprint(state),
		IdempotencyKey: idempotencyKey,
		ClaimedBy:      textToString(claimedBy),
		ClaimedAt:      timestamptzToPtr(claimedAt),
		StartedAt:      timestamptzToPtr(startedAt),
		FinishedAt:     timestamptzToPtr(finishedAt),
		ErrorMessage:   textToString(errorMessage),
		RetryCount:     int(retryCount),
		Payload:        bytesToMap(payload),
		LeaseToken:     textToString(leaseToken),
		LeaseExpiresAt: timestamptzToPtr(leaseExpiresAt),
		AttemptID:      formatUUID(attemptID),
		Result:         bytesToMap(result),
		CreatedAt:      timestamptzToTime(createdAt),
		UpdatedAt:      timestamptzToTime(updatedAt),
	}
}

// Reports
func (r *PostgresRepository) ListReports(ctx context.Context, incidentID string) ([]*store.Report, error) {
	q, err := getQueries(ctx)
	if err != nil {
		return nil, err
	}
	incUID, err := parseUUID(incidentID)
	if err != nil || !incUID.Valid {
		return nil, pgx.ErrNoRows
	}
	rows, err := q.ListReports(ctx, incUID)
	if err != nil {
		return nil, err
	}
	out := make([]*store.Report, 0, len(rows))
	for _, row := range rows {
		out = append(out, toStoreReport(row))
	}
	return out, nil
}

func (r *PostgresRepository) GetReport(ctx context.Context, incidentID, id string) (*store.Report, error) {
	q, err := getQueries(ctx)
	if err != nil {
		return nil, err
	}
	incUID, err := parseUUID(incidentID)
	if err != nil || !incUID.Valid {
		return nil, pgx.ErrNoRows
	}
	repUID, err := parseUUID(id)
	if err != nil || !repUID.Valid {
		return nil, pgx.ErrNoRows
	}
	row, err := q.GetReport(ctx, db.GetReportParams{
		IncidentID: incUID,
		ID:         repUID,
	})
	if err != nil {
		return nil, err
	}
	return toStoreReport(row), nil
}

func (r *PostgresRepository) CreateReport(ctx context.Context, rep *store.Report) (*store.Report, error) {
	q, err := getQueries(ctx)
	if err != nil {
		return nil, err
	}
	uid, err := parseUUID(rep.ID)
	if err != nil || !uid.Valid {
		uid = newUUID()
	}
	incUID, err := parseUUID(rep.IncidentID)
	if err != nil || !incUID.Valid {
		return nil, pgx.ErrNoRows
	}
	genUID, err := parseUUID(rep.GeneratedBy)
	if err != nil || !genUID.Valid {
		return nil, errors.New("invalid generated_by uuid")
	}
	var contentBytes []byte
	if rep.Content != nil {
		contentBytes, _ = json.Marshal(rep.Content)
	} else {
		contentBytes = []byte("{}")
	}
	row, err := q.CreateReport(ctx, db.CreateReportParams{
		ID:          uid,
		IncidentID:  incUID,
		Title:       rep.Title,
		Content:     contentBytes,
		GeneratedBy: genUID,
	})
	if err != nil {
		return nil, err
	}
	return toStoreReport(row), nil
}

func toStoreReport(row db.Report) *store.Report {
	var content map[string]interface{}
	if len(row.Content) > 0 {
		_ = json.Unmarshal(row.Content, &content)
	}
	return &store.Report{
		ID:          formatUUID(row.ID),
		IncidentID:  formatUUID(row.IncidentID),
		Title:       row.Title,
		Content:     content,
		GeneratedBy: formatUUID(row.GeneratedBy),
		CreatedAt:   timestamptzToTime(row.CreatedAt),
	}
}

// Audit Events
func (r *PostgresRepository) ListAuditEvents(ctx context.Context, incidentID string) ([]*store.AuditEvent, error) {
	q, err := getQueries(ctx)
	if err != nil {
		return nil, err
	}
	incUID, err := parseUUID(incidentID)
	if err != nil || !incUID.Valid {
		return nil, pgx.ErrNoRows
	}
	rows, err := q.ListAuditEvents(ctx, incUID)
	if err != nil {
		return nil, err
	}
	out := make([]*store.AuditEvent, 0, len(rows))
	for _, row := range rows {
		out = append(out, &store.AuditEvent{
			ID:          formatUUID(row.ID),
			ActorID:     formatUUID(row.ActorID),
			Action:      row.Action,
			EntityTable: row.EntityTable,
			EntityID:    formatUUID(row.EntityID),
			IncidentID:  formatUUID(row.IncidentID),
			OccurredAt:  timestamptzToTime(row.OccurredAt),
		})
	}
	return out, nil
}
