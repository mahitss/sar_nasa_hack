package handler

import (
	"encoding/json"
	"fmt"
	"net/http"
	"sync/atomic"
	"time"

	"github.com/mahitss/rivet-api/internal/errors"
	"github.com/mahitss/rivet-api/internal/middleware"
	"github.com/mahitss/rivet-api/internal/store"
	"github.com/mahitss/rivet-api/internal/transaction"
)

type Handler struct {
	Store *store.Store
	Tx    *transaction.Manager
}

func New(st *store.Store) *Handler {
	return &Handler{Store: st}
}

func (h *Handler) Healthz(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(200)
	_, _ = w.Write([]byte(`{"status":"ok"}`))
}

func (h *Handler) Readyz(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(200)
	_, _ = w.Write([]byte(`{"status":"ready"}`))
}

func (h *Handler) Whoami(w http.ResponseWriter, r *http.Request) {
	id, _ := middleware.IdentityFromContext(r.Context())
	writeJSON(w, 200, map[string]string{"subject": id.Subject})
}

func writeJSON(w http.ResponseWriter, status int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func writeErr(w http.ResponseWriter, e *errors.APIError) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(e.Status)
	_ = json.NewEncoder(w).Encode(map[string]string{"code": e.Code, "message": e.Message})
}

func newID() string {
	var n uint64
	atomic.AddUint64(&n, 1)
	return fmt.Sprintf("id-%d-%d", time.Now().UnixNano(), n)
}

// Incidents
func (h *Handler) ListIncidents(w http.ResponseWriter, r *http.Request) {
	id, _ := middleware.IdentityFromContext(r.Context())
	h.Store.RLock()
	defer h.Store.RUnlock()
	out := []store.Incident{}
	for _, inc := range h.Store.Incidents() {
		if h.Store.IsMember(inc.ID, id.Subject) {
			out = append(out, *inc)
		}
	}
	writeJSON(w, 200, out)
}

func (h *Handler) CreateIncident(w http.ResponseWriter, r *http.Request) {
	id, _ := middleware.IdentityFromContext(r.Context())
	var body struct {
		Title       string `json:"title"`
		Description string `json:"description"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil || body.Title == "" {
		writeErr(w, errors.ErrBadRequest)
		return
	}
	inc := &store.Incident{ID: newID(), Title: body.Title, Description: body.Description, CreatedBy: id.Subject, CreatedAt: time.Now()}
	h.Store.Lock()
	defer h.Store.Unlock()
	h.Store.IncidentsSet(inc)
	// auto owner membership
	h.Store.SetMember(inc.ID, id.Subject, "owner")
	writeJSON(w, 201, inc)
}

func (h *Handler) GetIncident(w http.ResponseWriter, r *http.Request) {
	id, _ := middleware.IdentityFromContext(r.Context())
	incidentID := r.PathValue("incidentID")
	if !h.Store.IsMember(incidentID, id.Subject) {
		writeErr(w, errors.ErrNotFound)
		return
	}
	h.Store.RLock()
	defer h.Store.RUnlock()
	inc, ok := h.Store.IncidentsGet(incidentID)
	if !ok {
		writeErr(w, errors.ErrNotFound)
		return
	}
	writeJSON(w, 200, inc)
}

// Acquisitions
func (h *Handler) ListAcquisitions(w http.ResponseWriter, r *http.Request) {
	id, _ := middleware.IdentityFromContext(r.Context())
	incidentID := r.PathValue("incidentID")
	if !h.Store.IsMember(incidentID, id.Subject) {
		writeErr(w, errors.ErrNotFound)
		return
	}
	h.Store.RLock()
	defer h.Store.RUnlock()
	out := []store.Acquisition{}
	for _, a := range h.Store.Acquisitions() {
		if a.IncidentID == incidentID {
			out = append(out, *a)
		}
	}
	writeJSON(w, 200, out)
}

func (h *Handler) CreateAcquisition(w http.ResponseWriter, r *http.Request) {
	id, _ := middleware.IdentityFromContext(r.Context())
	incidentID := r.PathValue("incidentID")
	if !h.Store.IsMember(incidentID, id.Subject) {
		writeErr(w, errors.ErrForbidden)
		return
	}
	var body store.Acquisition
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil || body.SourceProvider == "" || body.GranuleID == "" || body.CRID == "" {
		writeErr(w, errors.ErrBadRequest)
		return
	}
	body.ID = newID()
	body.IncidentID = incidentID
	if body.ProductMaturity == "" {
		body.ProductMaturity = "provisional"
	}
	h.Store.Lock()
	defer h.Store.Unlock()
	h.Store.AcquisitionsSet(&body)
	writeJSON(w, 201, body)
}

// Evidence
func (h *Handler) ListEvidence(w http.ResponseWriter, r *http.Request) {
	id, _ := middleware.IdentityFromContext(r.Context())
	incidentID := r.PathValue("incidentID")
	if !h.Store.IsMember(incidentID, id.Subject) {
		writeErr(w, errors.ErrNotFound)
		return
	}
	h.Store.RLock()
	defer h.Store.RUnlock()
	out := []store.Evidence{}
	for _, e := range h.Store.Evidence() {
		if e.IncidentID == incidentID {
			out = append(out, *e)
		}
	}
	writeJSON(w, 200, out)
}

func (h *Handler) CreateEvidence(w http.ResponseWriter, r *http.Request) {
	id, _ := middleware.IdentityFromContext(r.Context())
	incidentID := r.PathValue("incidentID")
	if !h.Store.IsMember(incidentID, id.Subject) {
		writeErr(w, errors.ErrForbidden)
		return
	}
	var body store.Evidence
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil || body.Title == "" || body.Summary == "" || body.SourcePath == "" {
		writeErr(w, errors.ErrBadRequest)
		return
	}
	body.ID = newID()
	body.IncidentID = incidentID
	body.ReviewState = "draft"
	body.CreatedBy = id.Subject
	body.CreatedAt = time.Now()
	h.Store.Lock()
	defer h.Store.Unlock()
	h.Store.EvidenceSet(&body)
	writeJSON(w, 201, body)
}

func (h *Handler) GetEvidence(w http.ResponseWriter, r *http.Request) {
	id, _ := middleware.IdentityFromContext(r.Context())
	incidentID := r.PathValue("incidentID")
	evidenceID := r.PathValue("evidenceID")
	if !h.Store.IsMember(incidentID, id.Subject) {
		writeErr(w, errors.ErrNotFound)
		return
	}
	h.Store.RLock()
	defer h.Store.RUnlock()
	e, ok := h.Store.EvidenceGet(evidenceID)
	if !ok || e.IncidentID != incidentID {
		writeErr(w, errors.ErrNotFound)
		return
	}
	writeJSON(w, 200, e)
}

func (h *Handler) PatchEvidence(w http.ResponseWriter, r *http.Request) {
	id, _ := middleware.IdentityFromContext(r.Context())
	incidentID := r.PathValue("incidentID")
	evidenceID := r.PathValue("evidenceID")
	if !h.Store.IsMember(incidentID, id.Subject) {
		writeErr(w, errors.ErrNotFound)
		return
	}
	h.Store.Lock()
	defer h.Store.Unlock()
	e, ok := h.Store.EvidenceGet(evidenceID)
	if !ok || e.IncidentID != incidentID {
		writeErr(w, errors.ErrNotFound)
		return
	}
	// block direct review_state mutation: ignore review_state in patch
	var patch map[string]interface{}
	if err := json.NewDecoder(r.Body).Decode(&patch); err != nil {
		writeErr(w, errors.ErrBadRequest)
		return
	}
	if v, ok := patch["title"].(string); ok {
		e.Title = v
	}
	if v, ok := patch["summary"].(string); ok {
		e.Summary = v
	}
	h.Store.EvidenceSet(e)
	writeJSON(w, 200, e)
}

// Decisions
func (h *Handler) CreateDecision(w http.ResponseWriter, r *http.Request) {
	id, _ := middleware.IdentityFromContext(r.Context())
	incidentID := r.PathValue("incidentID")
	evidenceID := r.PathValue("evidenceID")
	if !h.Store.IsMember(incidentID, id.Subject) {
		writeErr(w, errors.ErrForbidden)
		return
	}
	// role check: owner or reviewer
	role := h.Store.Role(incidentID, id.Subject)
	if role != "owner" && role != "reviewer" {
		writeErr(w, errors.ErrForbidden)
		return
	}
	// self-review check
	h.Store.RLock()
	e, ok := h.Store.EvidenceGet(evidenceID)
	h.Store.RUnlock()
	if !ok || e.IncidentID != incidentID {
		writeErr(w, errors.ErrNotFound)
		return
	}
	if e.CreatedBy == id.Subject {
		writeErr(w, errors.ErrForbidden)
		return
	}
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
	state := body.Decision
	if state == "accept" {
		state = "accepted"
	} else if state == "reject" {
		state = "rejected"
	} else {
		state = "needs_investigation"
	}
	d := &store.Decision{ID: newID(), IncidentID: incidentID, EvidenceID: evidenceID, ReviewerID: id.Subject, Decision: body.Decision, Rationale: body.Rationale}
	h.Store.Lock()
	defer h.Store.Unlock()
	h.Store.DecisionsSet(d)
	// update evidence review_state
	if ev, ok := h.Store.EvidenceGet(evidenceID); ok {
		ev.ReviewState = state
		h.Store.EvidenceSet(ev)
	}
	writeJSON(w, 201, d)
}

// Jobs
func (h *Handler) ListJobs(w http.ResponseWriter, r *http.Request) {
	id, _ := middleware.IdentityFromContext(r.Context())
	incidentID := r.PathValue("incidentID")
	if !h.Store.IsMember(incidentID, id.Subject) {
		writeErr(w, errors.ErrNotFound)
		return
	}
	h.Store.RLock()
	defer h.Store.RUnlock()
	out := []store.Job{}
	for _, j := range h.Store.Jobs() {
		if j.IncidentID == incidentID {
			out = append(out, *j)
		}
	}
	writeJSON(w, 200, out)
}

func (h *Handler) CreateJob(w http.ResponseWriter, r *http.Request) {
	id, _ := middleware.IdentityFromContext(r.Context())
	incidentID := r.PathValue("incidentID")
	if !h.Store.IsMember(incidentID, id.Subject) {
		writeErr(w, errors.ErrForbidden)
		return
	}
	role := h.Store.Role(incidentID, id.Subject)
	if role != "owner" && role != "analyst" {
		writeErr(w, errors.ErrForbidden)
		return
	}
	var body struct {
		JobType        string `json:"job_type"`
		IdempotencyKey string `json:"idempotency_key"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil || body.JobType == "" || body.IdempotencyKey == "" {
		writeErr(w, errors.ErrBadRequest)
		return
	}
	j := &store.Job{ID: newID(), IncidentID: incidentID, JobType: body.JobType, State: "queued", IdempotencyKey: body.IdempotencyKey}
	h.Store.Lock()
	defer h.Store.Unlock()
	h.Store.JobsSet(j)
	writeJSON(w, 201, j)
}

func (h *Handler) GetJob(w http.ResponseWriter, r *http.Request) {
	id, _ := middleware.IdentityFromContext(r.Context())
	incidentID := r.PathValue("incidentID")
	jobID := r.PathValue("jobID")
	if !h.Store.IsMember(incidentID, id.Subject) {
		writeErr(w, errors.ErrNotFound)
		return
	}
	h.Store.RLock()
	defer h.Store.RUnlock()
	j, ok := h.Store.JobsGet(jobID)
	if !ok || j.IncidentID != incidentID {
		writeErr(w, errors.ErrNotFound)
		return
	}
	writeJSON(w, 200, j)
}

// Reports
func (h *Handler) ListReports(w http.ResponseWriter, r *http.Request) {
	id, _ := middleware.IdentityFromContext(r.Context())
	incidentID := r.PathValue("incidentID")
	if !h.Store.IsMember(incidentID, id.Subject) {
		writeErr(w, errors.ErrNotFound)
		return
	}
	h.Store.RLock()
	defer h.Store.RUnlock()
	out := []store.Report{}
	for _, rep := range h.Store.Reports() {
		if rep.IncidentID == incidentID {
			out = append(out, *rep)
		}
	}
	writeJSON(w, 200, out)
}

func (h *Handler) CreateReport(w http.ResponseWriter, r *http.Request) {
	id, _ := middleware.IdentityFromContext(r.Context())
	incidentID := r.PathValue("incidentID")
	if !h.Store.IsMember(incidentID, id.Subject) {
		writeErr(w, errors.ErrForbidden)
		return
	}
	role := h.Store.Role(incidentID, id.Subject)
	if role != "owner" && role != "analyst" {
		writeErr(w, errors.ErrForbidden)
		return
	}
	var body struct {
		Title   string                 `json:"title"`
		Content map[string]interface{} `json:"content"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil || body.Title == "" {
		writeErr(w, errors.ErrBadRequest)
		return
	}
	rep := &store.Report{ID: newID(), IncidentID: incidentID, Title: body.Title, Content: body.Content, GeneratedBy: id.Subject}
	h.Store.Lock()
	defer h.Store.Unlock()
	h.Store.ReportsSet(rep)
	writeJSON(w, 201, rep)
}

func (h *Handler) GetReport(w http.ResponseWriter, r *http.Request) {
	id, _ := middleware.IdentityFromContext(r.Context())
	incidentID := r.PathValue("incidentID")
	reportID := r.PathValue("reportID")
	if !h.Store.IsMember(incidentID, id.Subject) {
		writeErr(w, errors.ErrNotFound)
		return
	}
	h.Store.RLock()
	defer h.Store.RUnlock()
	rep, ok := h.Store.ReportsGet(reportID)
	if !ok || rep.IncidentID != incidentID {
		writeErr(w, errors.ErrNotFound)
		return
	}
	writeJSON(w, 200, rep)
}
