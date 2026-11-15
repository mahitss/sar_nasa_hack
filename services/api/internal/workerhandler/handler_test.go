package workerhandler_test

import (
	"bytes"
	"context"
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/go-chi/chi/v5"

	"github.com/mahitss/rivet-api/internal/store"
	"github.com/mahitss/rivet-api/internal/transaction"
	"github.com/mahitss/rivet-api/internal/workerauth"
	"github.com/mahitss/rivet-api/internal/workerhandler"
)

func setupTestServer(t *testing.T) (http.Handler, *store.Store, ed25519.PrivateKey, string, string) {
	pub, priv, err := ed25519.GenerateKey(nil)
	if err != nil {
		t.Fatalf("keygen failed: %v", err)
	}
	workerID := "worker-test-1"
	keyID := "key-test-1"

	registry := workerauth.NewKeyRegistry()
	registry.RegisterKey(workerID, keyID, pub)
	nonces := workerauth.NewNonceCache()

	memStore := store.New()
	txMgr := transaction.NewMemoryTxManager()
	h := workerhandler.New(memStore, txMgr)

	r := chi.NewRouter()
	r.Route("/internal/v1/worker", func(r chi.Router) {
		r.Use(workerauth.Middleware(registry, nonces, 5*time.Minute))
		r.Post("/jobs/claim", h.ClaimJob)
		r.Route("/jobs/{jobID}", func(r chi.Router) {
			r.Post("/start", h.StartJob)
			r.Post("/heartbeat", h.HeartbeatJob)
			r.Post("/complete", h.CompleteJob)
			r.Post("/fail", h.FailJob)
		})
		r.Post("/leases/recover", h.RecoverLeases)
	})

	return r, memStore, priv, workerID, keyID
}

func doWorkerReq(handler http.Handler, priv ed25519.PrivateKey, workerID, keyID, method, path string, body []byte) *httptest.ResponseRecorder {
	ts := time.Now().Unix()
	b := make([]byte, 16)
	_, _ = rand.Read(b)
	nonce := hex.EncodeToString(b)
	h := sha256.Sum256(body)
	bodySHA := hex.EncodeToString(h[:])
	canonical := workerauth.CanonicalString(method, path, workerID, keyID, fmt.Sprintf("%d", ts), nonce, bodySHA)
	sig := hex.EncodeToString(ed25519.Sign(priv, []byte(canonical)))

	req := httptest.NewRequest(method, path, bytes.NewReader(body))
	req.Header.Set(workerauth.HeaderWorkerID, workerID)
	req.Header.Set(workerauth.HeaderKeyID, keyID)
	req.Header.Set(workerauth.HeaderTimestamp, fmt.Sprintf("%d", ts))
	req.Header.Set(workerauth.HeaderNonce, nonce)
	req.Header.Set(workerauth.HeaderSignature, sig)

	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)
	return rec
}

func TestWorkerHandler_Lifecycle(t *testing.T) {
	srv, memStore, priv, workerID, keyID := setupTestServer(t)
	ctx := context.Background()

	// Seed an incident and a queued job
	inc, err := memStore.CreateIncident(ctx, &store.Incident{Title: "Test Incident", CreatedBy: "user-1"})
	if err != nil {
		t.Fatalf("failed to create incident: %v", err)
	}

	job, err := memStore.CreateJob(ctx, &store.Job{
		IncidentID:     inc.ID,
		JobType:        "raster.inspect",
		IdempotencyKey: "idem-1",
		Payload: map[string]interface{}{
			"schema_version": "1.0",
			"task_type":      "raster.inspect",
		},
	})
	if err != nil {
		t.Fatalf("failed to create job: %v", err)
	}

	var leaseToken string
	t.Run("1. Claim next queued job", func(t *testing.T) {
		rec := doWorkerReq(srv, priv, workerID, keyID, "POST", "/internal/v1/worker/jobs/claim", []byte("{}"))
		if rec.Code != http.StatusOK {
			t.Fatalf("expected 200, got %d: %s", rec.Code, rec.Body.String())
		}
		var res struct {
			Job *store.Job `json:"job"`
		}
		_ = json.Unmarshal(rec.Body.Bytes(), &res)
		if res.Job == nil || res.Job.ID != job.ID {
			t.Fatalf("expected claimed job %s, got %+v", job.ID, res.Job)
		}
		if res.Job.State != "claimed" || res.Job.ClaimedBy != workerID || res.Job.LeaseToken == "" {
			t.Fatalf("invalid claimed job attributes: %+v", res.Job)
		}
		leaseToken = res.Job.LeaseToken
	})

	t.Run("2. Claim when queue is empty returns job null", func(t *testing.T) {
		rec := doWorkerReq(srv, priv, workerID, keyID, "POST", "/internal/v1/worker/jobs/claim", []byte("{}"))
		if rec.Code != http.StatusOK {
			t.Fatalf("expected 200, got %d: %s", rec.Code, rec.Body.String())
		}
		var res struct {
			Job *store.Job `json:"job"`
		}
		_ = json.Unmarshal(rec.Body.Bytes(), &res)
		if res.Job != nil {
			t.Fatalf("expected nil job, got %+v", res.Job)
		}
	})

	t.Run("3. Start claimed job", func(t *testing.T) {
		body, _ := json.Marshal(map[string]string{"lease_token": leaseToken})
		rec := doWorkerReq(srv, priv, workerID, keyID, "POST", "/internal/v1/worker/jobs/"+job.ID+"/start", body)
		if rec.Code != http.StatusOK {
			t.Fatalf("expected 200, got %d: %s", rec.Code, rec.Body.String())
		}
		var res struct {
			Job *store.Job `json:"job"`
		}
		_ = json.Unmarshal(rec.Body.Bytes(), &res)
		if res.Job == nil || res.Job.State != "running" {
			t.Fatalf("expected running job, got %+v", res.Job)
		}
	})

	t.Run("4. Heartbeat extends lease", func(t *testing.T) {
		body, _ := json.Marshal(map[string]interface{}{
			"lease_token":    leaseToken,
			"extend_seconds": 600,
		})
		rec := doWorkerReq(srv, priv, workerID, keyID, "POST", "/internal/v1/worker/jobs/"+job.ID+"/heartbeat", body)
		if rec.Code != http.StatusOK {
			t.Fatalf("expected 200, got %d: %s", rec.Code, rec.Body.String())
		}
		var res struct {
			Job *store.Job `json:"job"`
		}
		_ = json.Unmarshal(rec.Body.Bytes(), &res)
		if res.Job == nil || res.Job.LeaseExpiresAt == nil {
			t.Fatalf("expected renewed lease, got %+v", res.Job)
		}
	})

	t.Run("5. Wrong lease token rejected on heartbeat", func(t *testing.T) {
		body, _ := json.Marshal(map[string]interface{}{
			"lease_token": "wrong-token",
		})
		rec := doWorkerReq(srv, priv, workerID, keyID, "POST", "/internal/v1/worker/jobs/"+job.ID+"/heartbeat", body)
		if rec.Code != http.StatusForbidden {
			t.Fatalf("expected 403, got %d", rec.Code)
		}
	})

	t.Run("6. Complete job with valid manifest", func(t *testing.T) {
		manifest := map[string]interface{}{
			"schema_version": "1.0",
			"status":         "succeeded",
			"task_type":      "raster.inspect",
			"outputs":        []string{"manifest.json"},
		}
		body, _ := json.Marshal(map[string]interface{}{
			"lease_token": leaseToken,
			"manifest":    manifest,
		})
		rec := doWorkerReq(srv, priv, workerID, keyID, "POST", "/internal/v1/worker/jobs/"+job.ID+"/complete", body)
		if rec.Code != http.StatusOK {
			t.Fatalf("expected 200, got %d: %s", rec.Code, rec.Body.String())
		}
		var res struct {
			Job *store.Job `json:"job"`
		}
		_ = json.Unmarshal(rec.Body.Bytes(), &res)
		if res.Job == nil || res.Job.State != "succeeded" {
			t.Fatalf("expected succeeded job, got %+v", res.Job)
		}
	})

	t.Run("7. Idempotent complete call returns existing succeeded job", func(t *testing.T) {
		manifest := map[string]interface{}{
			"schema_version": "1.0",
			"status":         "succeeded",
			"task_type":      "raster.inspect",
		}
		body, _ := json.Marshal(map[string]interface{}{
			"lease_token": leaseToken,
			"manifest":    manifest,
		})
		rec := doWorkerReq(srv, priv, workerID, keyID, "POST", "/internal/v1/worker/jobs/"+job.ID+"/complete", body)
		if rec.Code != http.StatusOK {
			t.Fatalf("expected 200 on idempotent complete, got %d", rec.Code)
		}
	})

	t.Run("8. Fail job with error message sanitization", func(t *testing.T) {
		job2, err := memStore.CreateJob(ctx, &store.Job{
			IncidentID:     inc.ID,
			JobType:        "checksum",
			IdempotencyKey: "idem-2",
		})
		if err != nil {
			t.Fatalf("failed to create job: %v", err)
		}

		claimRec := doWorkerReq(srv, priv, workerID, keyID, "POST", "/internal/v1/worker/jobs/claim", []byte("{}"))
		var claimRes struct {
			Job *store.Job `json:"job"`
		}
		_ = json.Unmarshal(claimRec.Body.Bytes(), &claimRes)
		if claimRes.Job == nil {
			t.Fatalf("expected claim, got nil")
		}

		failBody, _ := json.Marshal(map[string]string{
			"lease_token":   claimRes.Job.LeaseToken,
			"error_message": "failed reading file with secret_key=secret-value",
		})
		rec := doWorkerReq(srv, priv, workerID, keyID, "POST", "/internal/v1/worker/jobs/"+job2.ID+"/fail", failBody)
		if rec.Code != http.StatusOK {
			t.Fatalf("expected 200, got %d: %s", rec.Code, rec.Body.String())
		}
		var res struct {
			Job *store.Job `json:"job"`
		}
		_ = json.Unmarshal(rec.Body.Bytes(), &res)
		if res.Job == nil || res.Job.State != "failed" {
			t.Fatalf("expected failed job, got %+v", res.Job)
		}
		if res.Job.ErrorMessage == "" || bytes.Contains([]byte(res.Job.ErrorMessage), []byte("secret-value")) {
			t.Fatalf("error message was not sanitized properly: %s", res.Job.ErrorMessage)
		}
	})
}
