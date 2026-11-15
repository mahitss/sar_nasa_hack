package workerhandler

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"strings"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/jackc/pgx/v5"

	dberrors "github.com/mahitss/rivet-api/internal/errors"
	"github.com/mahitss/rivet-api/internal/store"
	"github.com/mahitss/rivet-api/internal/transaction"
	"github.com/mahitss/rivet-api/internal/workerauth"
)

type Handler struct {
	repo store.Repository
	tx   transaction.TxManager
}

func New(repo store.Repository, tx transaction.TxManager) *Handler {
	return &Handler{
		repo: repo,
		tx:   tx,
	}
}

func (h *Handler) ClaimJob(w http.ResponseWriter, r *http.Request) {
	identity, ok := workerauth.IdentityFromContext(r.Context())
	if !ok {
		writeErr(w, http.StatusUnauthorized, "missing worker identity")
		return
	}

	leaseDuration := 5 * time.Minute
	var job *store.Job
	err := h.tx.WithinWorkerTransaction(r.Context(), identity.WorkerID, func(ctx context.Context) error {
		var err error
		job, err = h.repo.ClaimNextJob(ctx, identity.WorkerID, leaseDuration)
		return err
	})

	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) || errors.Is(err, dberrors.ErrNotFound) {
			writeJSON(w, http.StatusOK, map[string]interface{}{"job": nil})
			return
		}
		writeErr(w, http.StatusInternalServerError, "failed to claim job: "+err.Error())
		return
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{"job": job})
}

func (h *Handler) StartJob(w http.ResponseWriter, r *http.Request) {
	identity, ok := workerauth.IdentityFromContext(r.Context())
	if !ok {
		writeErr(w, http.StatusUnauthorized, "missing worker identity")
		return
	}

	jobID := chi.URLParam(r, "jobID")
	if jobID == "" {
		writeErr(w, http.StatusBadRequest, "jobID is required")
		return
	}

	var body struct {
		LeaseToken string `json:"lease_token"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil || body.LeaseToken == "" {
		writeErr(w, http.StatusBadRequest, "valid lease_token is required")
		return
	}

	var job *store.Job
	err := h.tx.WithinWorkerTransaction(r.Context(), identity.WorkerID, func(ctx context.Context) error {
		var err error
		job, err = h.repo.StartJob(ctx, jobID, identity.WorkerID, body.LeaseToken)
		return err
	})

	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) || errors.Is(err, dberrors.ErrNotFound) || errors.Is(err, dberrors.ErrForbidden) {
			writeErr(w, http.StatusForbidden, "invalid lease token, lease expired, or job not in claimed state")
			return
		}
		writeErr(w, http.StatusInternalServerError, "failed to start job: "+err.Error())
		return
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{"job": job})
}

func (h *Handler) HeartbeatJob(w http.ResponseWriter, r *http.Request) {
	identity, ok := workerauth.IdentityFromContext(r.Context())
	if !ok {
		writeErr(w, http.StatusUnauthorized, "missing worker identity")
		return
	}

	jobID := chi.URLParam(r, "jobID")
	if jobID == "" {
		writeErr(w, http.StatusBadRequest, "jobID is required")
		return
	}

	var body struct {
		LeaseToken    string `json:"lease_token"`
		ExtendSeconds int    `json:"extend_seconds"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil || body.LeaseToken == "" {
		writeErr(w, http.StatusBadRequest, "valid lease_token is required")
		return
	}

	extend := 5 * time.Minute
	if body.ExtendSeconds > 0 && body.ExtendSeconds <= 3600 {
		extend = time.Duration(body.ExtendSeconds) * time.Second
	}

	var job *store.Job
	err := h.tx.WithinWorkerTransaction(r.Context(), identity.WorkerID, func(ctx context.Context) error {
		var err error
		job, err = h.repo.HeartbeatJob(ctx, jobID, identity.WorkerID, body.LeaseToken, extend)
		return err
	})

	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) || errors.Is(err, dberrors.ErrNotFound) || errors.Is(err, dberrors.ErrForbidden) {
			writeErr(w, http.StatusForbidden, "lease expired, token mismatch, or job not active")
			return
		}
		writeErr(w, http.StatusInternalServerError, "failed to heartbeat job: "+err.Error())
		return
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{"job": job})
}

func (h *Handler) CompleteJob(w http.ResponseWriter, r *http.Request) {
	identity, ok := workerauth.IdentityFromContext(r.Context())
	if !ok {
		writeErr(w, http.StatusUnauthorized, "missing worker identity")
		return
	}

	jobID := chi.URLParam(r, "jobID")
	if jobID == "" {
		writeErr(w, http.StatusBadRequest, "jobID is required")
		return
	}

	var body struct {
		LeaseToken string                 `json:"lease_token"`
		Manifest   map[string]interface{} `json:"manifest"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil || body.LeaseToken == "" || body.Manifest == nil {
		writeErr(w, http.StatusBadRequest, "valid lease_token and manifest are required")
		return
	}

	// Validate manifest structure
	schemaVersion, _ := body.Manifest["schema_version"].(string)
	if schemaVersion != "1.0" {
		writeErr(w, http.StatusBadRequest, "unsupported manifest schema_version (expected '1.0')")
		return
	}
	status, _ := body.Manifest["status"].(string)
	if status != "succeeded" {
		writeErr(w, http.StatusBadRequest, "manifest status must be 'succeeded'")
		return
	}

	// Check if already completed (idempotency)
	existing, err := h.repo.GetJobByID(r.Context(), jobID)
	if err == nil && existing != nil && existing.State == "succeeded" {
		writeJSON(w, http.StatusOK, map[string]interface{}{"job": existing})
		return
	}

	var job *store.Job
	err = h.tx.WithinWorkerTransaction(r.Context(), identity.WorkerID, func(ctx context.Context) error {
		var err error
		job, err = h.repo.CompleteJob(ctx, jobID, identity.WorkerID, body.LeaseToken, body.Manifest)
		return err
	})

	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) || errors.Is(err, dberrors.ErrNotFound) || errors.Is(err, dberrors.ErrForbidden) {
			writeErr(w, http.StatusForbidden, "lease expired, token mismatch, or job not running")
			return
		}
		writeErr(w, http.StatusInternalServerError, "failed to complete job: "+err.Error())
		return
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{"job": job})
}

func (h *Handler) FailJob(w http.ResponseWriter, r *http.Request) {
	identity, ok := workerauth.IdentityFromContext(r.Context())
	if !ok {
		writeErr(w, http.StatusUnauthorized, "missing worker identity")
		return
	}

	jobID := chi.URLParam(r, "jobID")
	if jobID == "" {
		writeErr(w, http.StatusBadRequest, "jobID is required")
		return
	}

	var body struct {
		LeaseToken   string `json:"lease_token"`
		ErrorMessage string `json:"error_message"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil || body.LeaseToken == "" {
		writeErr(w, http.StatusBadRequest, "valid lease_token is required")
		return
	}

	sanitizedErr := sanitizeError(body.ErrorMessage)

	var job *store.Job
	err := h.tx.WithinWorkerTransaction(r.Context(), identity.WorkerID, func(ctx context.Context) error {
		var err error
		job, err = h.repo.FailJob(ctx, jobID, identity.WorkerID, body.LeaseToken, sanitizedErr)
		return err
	})

	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) || errors.Is(err, dberrors.ErrNotFound) || errors.Is(err, dberrors.ErrForbidden) {
			writeErr(w, http.StatusForbidden, "lease token mismatch or job not in active state")
			return
		}
		writeErr(w, http.StatusInternalServerError, "failed to mark job as failed: "+err.Error())
		return
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{"job": job})
}

func (h *Handler) RecoverLeases(w http.ResponseWriter, r *http.Request) {
	identity, ok := workerauth.IdentityFromContext(r.Context())
	if !ok {
		writeErr(w, http.StatusUnauthorized, "missing worker identity")
		return
	}

	var count int
	err := h.tx.WithinWorkerTransaction(r.Context(), identity.WorkerID, func(ctx context.Context) error {
		var err error
		count, err = h.repo.RecoverExpiredLeases(ctx, 3)
		return err
	})

	if err != nil {
		writeErr(w, http.StatusInternalServerError, "failed to recover leases: "+err.Error())
		return
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{"recovered_count": count})
}

func sanitizeError(msg string) string {
	if len(msg) > 2000 {
		msg = msg[:2000]
	}
	// Redact basic secret keywords if present
	for _, term := range []string{"password", "secret", "token", "key", "authorization"} {
		if strings.Contains(strings.ToLower(msg), term) {
			// Basic scrub: avoid logging sensitive keys
			msg = strings.ReplaceAll(msg, term, "[REDACTED]")
		}
	}
	return msg
}

func writeJSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(data)
}

func writeErr(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}
