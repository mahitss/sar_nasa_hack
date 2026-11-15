package handler

import (
	"context"
	"encoding/json"
	"net/http"

	"github.com/go-chi/chi/v5"

	"github.com/mahitss/rivet-api/internal/errors"
	"github.com/mahitss/rivet-api/internal/middleware"
	"github.com/mahitss/rivet-api/internal/store"
	"github.com/mahitss/rivet-api/internal/transaction"
)

type Handler struct {
	Repo store.Repository
	Tx   transaction.TxManager
}

func New(repo store.Repository, tx transaction.TxManager) *Handler {
	return &Handler{
		Repo: repo,
		Tx:   tx,
	}
}

func (h *Handler) Healthz(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte(`{"status":"ok"}`))
}

func (h *Handler) Readyz(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte(`{"status":"ready"}`))
}

func (h *Handler) Whoami(w http.ResponseWriter, r *http.Request) {
	id, ok := middleware.IdentityFromContext(r.Context())
	if !ok {
		writeErr(w, errors.ErrUnauthorized)
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"subject": id.Subject})
}

func writeJSON(w http.ResponseWriter, status int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func writeErr(w http.ResponseWriter, e *errors.APIError) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(e.Status)
	_ = json.NewEncoder(w).Encode(map[string]string{
		"code":    e.Code,
		"message": e.Message,
	})
}

func param(r *http.Request, key string) string {
	if v := chi.URLParam(r, key); v != "" {
		return v
	}
	return r.PathValue(key)
}

// Incidents
func (h *Handler) ListIncidents(w http.ResponseWriter, r *http.Request) {
	id, ok := middleware.IdentityFromContext(r.Context())
	if !ok {
		writeErr(w, errors.ErrUnauthorized)
		return
	}

	var out []*store.Incident
	err := h.Tx.WithinTransaction(r.Context(), id.Subject, func(ctx context.Context) error {
		var err error
		out, err = h.Repo.ListIncidents(ctx)
		return err
	})
	if err != nil {
		writeErr(w, errors.MapDBError(err))
		return
	}
	if out == nil {
		out = []*store.Incident{}
	}
	writeJSON(w, http.StatusOK, out)
}

func (h *Handler) CreateIncident(w http.ResponseWriter, r *http.Request) {
	id, ok := middleware.IdentityFromContext(r.Context())
	if !ok {
		writeErr(w, errors.ErrUnauthorized)
		return
	}

	var body struct {
		Title          string   `json:"title"`
		Description    string   `json:"description"`
		DiscoveryWest  *float64 `json:"discovery_west"`
		DiscoverySouth *float64 `json:"discovery_south"`
		DiscoveryEast  *float64 `json:"discovery_east"`
		DiscoveryNorth *float64 `json:"discovery_north"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil || len(body.Title) < 3 {
		writeErr(w, errors.ErrBadRequest)
		return
	}

	inc := &store.Incident{
		Title:          body.Title,
		Description:    body.Description,
		DiscoveryWest:  body.DiscoveryWest,
		DiscoverySouth: body.DiscoverySouth,
		DiscoveryEast:  body.DiscoveryEast,
		DiscoveryNorth: body.DiscoveryNorth,
		CreatedBy:      id.Subject,
	}

	var created *store.Incident
	err := h.Tx.WithinTransaction(r.Context(), id.Subject, func(ctx context.Context) error {
		var err error
		created, err = h.Repo.CreateIncident(ctx, inc)
		return err
	})
	if err != nil {
		writeErr(w, errors.MapDBError(err))
		return
	}

	writeJSON(w, http.StatusCreated, created)
}

func (h *Handler) GetIncident(w http.ResponseWriter, r *http.Request) {
	id, ok := middleware.IdentityFromContext(r.Context())
	if !ok {
		writeErr(w, errors.ErrUnauthorized)
		return
	}
	incidentID := param(r, "incidentID")

	var inc *store.Incident
	err := h.Tx.WithinTransaction(r.Context(), id.Subject, func(ctx context.Context) error {
		var err error
		inc, err = h.Repo.GetIncident(ctx, incidentID)
		return err
	})
	if err != nil {
		writeErr(w, errors.MapDBError(err))
		return
	}
	writeJSON(w, http.StatusOK, inc)
}

func (h *Handler) GetIncidentRole(w http.ResponseWriter, r *http.Request) {
	id, ok := middleware.IdentityFromContext(r.Context())
	if !ok {
		writeErr(w, errors.ErrUnauthorized)
		return
	}
	incidentID := param(r, "incidentID")

	var role string
	err := h.Tx.WithinTransaction(r.Context(), id.Subject, func(ctx context.Context) error {
		var err error
		role, err = h.Repo.GetIncidentMemberRole(ctx, incidentID, id.Subject)
		return err
	})
	if err != nil {
		writeErr(w, errors.MapDBError(err))
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{
		"incident_id": incidentID,
		"user_id":     id.Subject,
		"role":        role,
	})
}

func (h *Handler) AddIncidentMember(w http.ResponseWriter, r *http.Request) {
	id, ok := middleware.IdentityFromContext(r.Context())
	if !ok {
		writeErr(w, errors.ErrUnauthorized)
		return
	}
	incidentID := param(r, "incidentID")

	var body struct {
		UserID string `json:"user_id"`
		Role   string `json:"role"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil || body.UserID == "" || body.Role == "" {
		writeErr(w, errors.ErrBadRequest)
		return
	}

	err := h.Tx.WithinTransaction(r.Context(), id.Subject, func(ctx context.Context) error {
		return h.Repo.AddIncidentMember(ctx, incidentID, body.UserID, body.Role)
	})
	if err != nil {
		writeErr(w, errors.MapDBError(err))
		return
	}
	writeJSON(w, http.StatusCreated, map[string]string{
		"incident_id": incidentID,
		"user_id":     body.UserID,
		"role":        body.Role,
	})
}

func (h *Handler) ListAuditEvents(w http.ResponseWriter, r *http.Request) {
	id, ok := middleware.IdentityFromContext(r.Context())
	if !ok {
		writeErr(w, errors.ErrUnauthorized)
		return
	}
	incidentID := param(r, "incidentID")

	var out []*store.AuditEvent
	err := h.Tx.WithinTransaction(r.Context(), id.Subject, func(ctx context.Context) error {
		var err error
		out, err = h.Repo.ListAuditEvents(ctx, incidentID)
		return err
	})
	if err != nil {
		writeErr(w, errors.MapDBError(err))
		return
	}
	if out == nil {
		out = []*store.AuditEvent{}
	}
	writeJSON(w, http.StatusOK, out)
}

// Acquisitions
func (h *Handler) ListAcquisitions(w http.ResponseWriter, r *http.Request) {
	id, ok := middleware.IdentityFromContext(r.Context())
	if !ok {
		writeErr(w, errors.ErrUnauthorized)
		return
	}
	incidentID := param(r, "incidentID")

	var out []*store.Acquisition
	err := h.Tx.WithinTransaction(r.Context(), id.Subject, func(ctx context.Context) error {
		if _, err := h.Repo.GetIncident(ctx, incidentID); err != nil {
			return err
		}
		var err error
		out, err = h.Repo.ListAcquisitions(ctx, incidentID)
		return err
	})
	if err != nil {
		writeErr(w, errors.MapDBError(err))
		return
	}
	if out == nil {
		out = []*store.Acquisition{}
	}
	writeJSON(w, http.StatusOK, out)
}

func (h *Handler) CreateAcquisition(w http.ResponseWriter, r *http.Request) {
	id, ok := middleware.IdentityFromContext(r.Context())
	if !ok {
		writeErr(w, errors.ErrUnauthorized)
		return
	}
	incidentID := param(r, "incidentID")

	var body struct {
		SourceProvider  string `json:"source_provider"`
		GranuleID       string `json:"granule_id"`
		CRID            string `json:"crid"`
		ProductMaturity string `json:"product_maturity"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil || body.SourceProvider == "" || body.GranuleID == "" || body.CRID == "" {
		writeErr(w, errors.ErrBadRequest)
		return
	}

	acq := &store.Acquisition{
		IncidentID:      incidentID,
		SourceProvider:  body.SourceProvider,
		GranuleID:       body.GranuleID,
		CRID:            body.CRID,
		ProductMaturity: body.ProductMaturity,
	}

	var created *store.Acquisition
	err := h.Tx.WithinTransaction(r.Context(), id.Subject, func(ctx context.Context) error {
		if _, err := h.Repo.GetIncident(ctx, incidentID); err != nil {
			return err
		}
		var err error
		created, err = h.Repo.CreateAcquisition(ctx, acq)
		return err
	})
	if err != nil {
		writeErr(w, errors.MapDBError(err))
		return
	}
	writeJSON(w, http.StatusCreated, created)
}

// Evidence
func (h *Handler) ListEvidence(w http.ResponseWriter, r *http.Request) {
	id, ok := middleware.IdentityFromContext(r.Context())
	if !ok {
		writeErr(w, errors.ErrUnauthorized)
		return
	}
	incidentID := param(r, "incidentID")

	var out []*store.Evidence
	err := h.Tx.WithinTransaction(r.Context(), id.Subject, func(ctx context.Context) error {
		if _, err := h.Repo.GetIncident(ctx, incidentID); err != nil {
			return err
		}
		var err error
		out, err = h.Repo.ListEvidence(ctx, incidentID)
		return err
	})
	if err != nil {
		writeErr(w, errors.MapDBError(err))
		return
	}
	if out == nil {
		out = []*store.Evidence{}
	}
	writeJSON(w, http.StatusOK, out)
}

func (h *Handler) CreateEvidence(w http.ResponseWriter, r *http.Request) {
	id, ok := middleware.IdentityFromContext(r.Context())
	if !ok {
		writeErr(w, errors.ErrUnauthorized)
		return
	}
	incidentID := param(r, "incidentID")

	var body struct {
		AcquisitionID string `json:"acquisition_id"`
		ClaimLevel    string `json:"claim_level"`
		EvidenceKind  string `json:"evidence_kind"`
		Title         string `json:"title"`
		Summary       string `json:"summary"`
		SourcePath    string `json:"source_path"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil || body.Title == "" || body.Summary == "" || body.SourcePath == "" {
		writeErr(w, errors.ErrBadRequest)
		return
	}

	ev := &store.Evidence{
		IncidentID:    incidentID,
		AcquisitionID: body.AcquisitionID,
		ClaimLevel:    body.ClaimLevel,
		EvidenceKind:  body.EvidenceKind,
		Title:         body.Title,
		Summary:       body.Summary,
		SourcePath:    body.SourcePath,
		CreatedBy:     id.Subject,
	}

	var created *store.Evidence
	err := h.Tx.WithinTransaction(r.Context(), id.Subject, func(ctx context.Context) error {
		if _, err := h.Repo.GetIncident(ctx, incidentID); err != nil {
			return err
		}
		var err error
		created, err = h.Repo.CreateEvidence(ctx, ev)
		return err
	})
	if err != nil {
		writeErr(w, errors.MapDBError(err))
		return
	}
	writeJSON(w, http.StatusCreated, created)
}

func (h *Handler) GetEvidence(w http.ResponseWriter, r *http.Request) {
	id, ok := middleware.IdentityFromContext(r.Context())
	if !ok {
		writeErr(w, errors.ErrUnauthorized)
		return
	}
	incidentID := param(r, "incidentID")
	evidenceID := param(r, "evidenceID")

	var ev *store.Evidence
	err := h.Tx.WithinTransaction(r.Context(), id.Subject, func(ctx context.Context) error {
		var err error
		ev, err = h.Repo.GetEvidence(ctx, incidentID, evidenceID)
		return err
	})
	if err != nil {
		writeErr(w, errors.MapDBError(err))
		return
	}
	writeJSON(w, http.StatusOK, ev)
}

func (h *Handler) PatchEvidence(w http.ResponseWriter, r *http.Request) {
	id, ok := middleware.IdentityFromContext(r.Context())
	if !ok {
		writeErr(w, errors.ErrUnauthorized)
		return
	}
	incidentID := param(r, "incidentID")
	evidenceID := param(r, "evidenceID")

	var patch struct {
		Title   *string `json:"title"`
		Summary *string `json:"summary"`
	}
	if err := json.NewDecoder(r.Body).Decode(&patch); err != nil {
		writeErr(w, errors.ErrBadRequest)
		return
	}

	var title, summary string
	if patch.Title != nil {
		title = *patch.Title
	}
	if patch.Summary != nil {
		summary = *patch.Summary
	}

	var updated *store.Evidence
	err := h.Tx.WithinTransaction(r.Context(), id.Subject, func(ctx context.Context) error {
		var err error
		updated, err = h.Repo.PatchEvidence(ctx, incidentID, evidenceID, title, summary)
		return err
	})
	if err != nil {
		writeErr(w, errors.MapDBError(err))
		return
	}
	writeJSON(w, http.StatusOK, updated)
}

// Decisions
func (h *Handler) CreateDecision(w http.ResponseWriter, r *http.Request) {
	id, ok := middleware.IdentityFromContext(r.Context())
	if !ok {
		writeErr(w, errors.ErrUnauthorized)
		return
	}
	incidentID := param(r, "incidentID")
	evidenceID := param(r, "evidenceID")

	var body struct {
		Decision  string `json:"decision"`
		Rationale string `json:"rationale"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeErr(w, errors.ErrBadRequest)
		return
	}
	if body.Decision != "accept" && body.Decision != "reject" && body.Decision != "needs_investigation" {
		writeErr(w, errors.ErrBadRequest)
		return
	}

	var dec *store.Decision
	err := h.Tx.WithinTransaction(r.Context(), id.Subject, func(ctx context.Context) error {
		var err error
		dec, err = h.Repo.SubmitEvidenceDecision(ctx, incidentID, evidenceID, body.Decision, body.Rationale)
		return err
	})
	if err != nil {
		writeErr(w, errors.MapDBError(err))
		return
	}
	writeJSON(w, http.StatusCreated, dec)
}

// Jobs
func (h *Handler) ListJobs(w http.ResponseWriter, r *http.Request) {
	id, ok := middleware.IdentityFromContext(r.Context())
	if !ok {
		writeErr(w, errors.ErrUnauthorized)
		return
	}
	incidentID := param(r, "incidentID")

	var out []*store.Job
	err := h.Tx.WithinTransaction(r.Context(), id.Subject, func(ctx context.Context) error {
		if _, err := h.Repo.GetIncident(ctx, incidentID); err != nil {
			return err
		}
		var err error
		out, err = h.Repo.ListJobs(ctx, incidentID)
		return err
	})
	if err != nil {
		writeErr(w, errors.MapDBError(err))
		return
	}
	if out == nil {
		out = []*store.Job{}
	}
	writeJSON(w, http.StatusOK, out)
}

func (h *Handler) CreateJob(w http.ResponseWriter, r *http.Request) {
	id, ok := middleware.IdentityFromContext(r.Context())
	if !ok {
		writeErr(w, errors.ErrUnauthorized)
		return
	}
	incidentID := param(r, "incidentID")

	var body struct {
		JobType        string                 `json:"job_type"`
		IdempotencyKey string                 `json:"idempotency_key"`
		Payload        map[string]interface{} `json:"payload"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil || body.JobType == "" || body.IdempotencyKey == "" {
		writeErr(w, errors.ErrBadRequest)
		return
	}

	job := &store.Job{
		IncidentID:     incidentID,
		JobType:        body.JobType,
		IdempotencyKey: body.IdempotencyKey,
		Payload:        body.Payload,
	}

	var created *store.Job
	err := h.Tx.WithinTransaction(r.Context(), id.Subject, func(ctx context.Context) error {
		if _, err := h.Repo.GetIncident(ctx, incidentID); err != nil {
			return err
		}
		var err error
		created, err = h.Repo.CreateJob(ctx, job)
		return err
	})
	if err != nil {
		writeErr(w, errors.MapDBError(err))
		return
	}
	writeJSON(w, http.StatusCreated, created)
}

func (h *Handler) GetJob(w http.ResponseWriter, r *http.Request) {
	id, ok := middleware.IdentityFromContext(r.Context())
	if !ok {
		writeErr(w, errors.ErrUnauthorized)
		return
	}
	incidentID := param(r, "incidentID")
	jobID := param(r, "jobID")

	var job *store.Job
	err := h.Tx.WithinTransaction(r.Context(), id.Subject, func(ctx context.Context) error {
		var err error
		job, err = h.Repo.GetJob(ctx, incidentID, jobID)
		return err
	})
	if err != nil {
		writeErr(w, errors.MapDBError(err))
		return
	}
	writeJSON(w, http.StatusOK, job)
}

// Reports
func (h *Handler) ListReports(w http.ResponseWriter, r *http.Request) {
	id, ok := middleware.IdentityFromContext(r.Context())
	if !ok {
		writeErr(w, errors.ErrUnauthorized)
		return
	}
	incidentID := param(r, "incidentID")

	var out []*store.Report
	err := h.Tx.WithinTransaction(r.Context(), id.Subject, func(ctx context.Context) error {
		if _, err := h.Repo.GetIncident(ctx, incidentID); err != nil {
			return err
		}
		var err error
		out, err = h.Repo.ListReports(ctx, incidentID)
		return err
	})
	if err != nil {
		writeErr(w, errors.MapDBError(err))
		return
	}
	if out == nil {
		out = []*store.Report{}
	}
	writeJSON(w, http.StatusOK, out)
}

func (h *Handler) CreateReport(w http.ResponseWriter, r *http.Request) {
	id, ok := middleware.IdentityFromContext(r.Context())
	if !ok {
		writeErr(w, errors.ErrUnauthorized)
		return
	}
	incidentID := param(r, "incidentID")

	var body struct {
		Title   string                 `json:"title"`
		Content map[string]interface{} `json:"content"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil || body.Title == "" {
		writeErr(w, errors.ErrBadRequest)
		return
	}

	rep := &store.Report{
		IncidentID:  incidentID,
		Title:       body.Title,
		Content:     body.Content,
		GeneratedBy: id.Subject,
	}

	var created *store.Report
	err := h.Tx.WithinTransaction(r.Context(), id.Subject, func(ctx context.Context) error {
		if _, err := h.Repo.GetIncident(ctx, incidentID); err != nil {
			return err
		}
		var err error
		created, err = h.Repo.CreateReport(ctx, rep)
		return err
	})
	if err != nil {
		writeErr(w, errors.MapDBError(err))
		return
	}
	writeJSON(w, http.StatusCreated, created)
}

func (h *Handler) GetReport(w http.ResponseWriter, r *http.Request) {
	id, ok := middleware.IdentityFromContext(r.Context())
	if !ok {
		writeErr(w, errors.ErrUnauthorized)
		return
	}
	incidentID := param(r, "incidentID")
	reportID := param(r, "reportID")

	var rep *store.Report
	err := h.Tx.WithinTransaction(r.Context(), id.Subject, func(ctx context.Context) error {
		var err error
		rep, err = h.Repo.GetReport(ctx, incidentID, reportID)
		return err
	})
	if err != nil {
		writeErr(w, errors.MapDBError(err))
		return
	}
	writeJSON(w, http.StatusOK, rep)
}
