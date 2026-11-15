package handler_test

import (
	"bytes"
	"context"
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"testing"
	"time"

	"github.com/mahitss/rivet-api/internal/store"
	"github.com/mahitss/rivet-api/internal/workerauth"
)

func devWorkerPrivKey(t *testing.T) ed25519.PrivateKey {
	seed, err := hex.DecodeString(workerauth.DefaultDevPrivSeed)
	if err != nil {
		t.Fatalf("invalid dev priv seed: %v", err)
	}
	return ed25519.NewKeyFromSeed(seed)
}

func (e *testEnv) workerReq(t *testing.T, priv ed25519.PrivateKey, workerID, keyID, method, path string, body interface{}) (*http.Response, []byte) {
	var bodyBytes []byte
	if body != nil {
		bodyBytes, _ = json.Marshal(body)
	} else {
		bodyBytes = []byte("{}")
	}

	ts := time.Now().Unix()
	b := make([]byte, 16)
	_, _ = rand.Read(b)
	nonce := hex.EncodeToString(b)
	h := sha256.Sum256(bodyBytes)
	bodySHA := hex.EncodeToString(h[:])
	canonical := workerauth.CanonicalString(method, path, workerID, keyID, fmt.Sprintf("%d", ts), nonce, bodySHA)
	sig := hex.EncodeToString(ed25519.Sign(priv, []byte(canonical)))

	req, err := http.NewRequest(method, e.apiServer.URL+path, bytes.NewReader(bodyBytes))
	if err != nil {
		t.Fatalf("failed to create req: %v", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set(workerauth.HeaderWorkerID, workerID)
	req.Header.Set(workerauth.HeaderKeyID, keyID)
	req.Header.Set(workerauth.HeaderTimestamp, fmt.Sprintf("%d", ts))
	req.Header.Set(workerauth.HeaderNonce, nonce)
	req.Header.Set(workerauth.HeaderSignature, sig)

	client := &http.Client{Timeout: 5 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		t.Fatalf("req failed: %v", err)
	}
	defer resp.Body.Close()
	resBody, _ := io.ReadAll(resp.Body)
	return resp, resBody
}

func TestMission021_WorkerIntegration(t *testing.T) {
	env := setupTestEnv(t)
	defer env.close()

	// Ensure clean queue state for integration test
	_, _ = env.pool.Exec(context.Background(), "DELETE FROM public.processing_jobs;")

	t1Owner := env.tokenFor(user1Owner, "owner@test.local")
	workerPriv := devWorkerPrivKey(t)
	workerID := workerauth.DefaultDevWorkerID
	keyID := workerauth.DefaultDevKeyID

	// Create an incident as authenticated user
	incResp, incBody := env.req(t, "POST", "/api/v1/incidents", t1Owner, map[string]interface{}{
		"title": "Mission 021 Scientific Incident",
	})
	if incResp.StatusCode != http.StatusCreated {
		t.Fatalf("failed to create incident: %s", string(incBody))
	}
	var inc store.Incident
	_ = json.Unmarshal(incBody, &inc)

	var claimedJobID string
	var activeLeaseToken string

	t.Run("Scenario A: Atomic Job Claim & Lease Ownership", func(t *testing.T) {
		// 1. Submit a processing job as human user
		jobResp, jobBody := env.req(t, "POST", fmt.Sprintf("/api/v1/incidents/%s/jobs", inc.ID), t1Owner, map[string]interface{}{
			"job_type":        "raster.inspect",
			"idempotency_key": "m021-job-1",
			"payload": map[string]interface{}{
				"schema_version": "1.0",
				"task_type":      "raster.inspect",
				"input_path":     "fixtures/sample.tif",
			},
		})
		if jobResp.StatusCode != http.StatusCreated {
			t.Fatalf("failed to create job: %s", string(jobBody))
		}
		var job store.Job
		_ = json.Unmarshal(jobBody, &job)
		if job.State != "queued" {
			t.Fatalf("expected state queued, got %s", job.State)
		}

		// 2. Worker claims next job
		claimResp, claimBody := env.workerReq(t, workerPriv, workerID, keyID, "POST", "/internal/v1/worker/jobs/claim", nil)
		if claimResp.StatusCode != http.StatusOK {
			t.Fatalf("expected 200, got %d: %s", claimResp.StatusCode, string(claimBody))
		}
		var claimResult struct {
			Job *store.Job `json:"job"`
		}
		_ = json.Unmarshal(claimBody, &claimResult)
		if claimResult.Job == nil || claimResult.Job.ID != job.ID {
			t.Fatalf("expected claimed job %s, got %+v", job.ID, claimResult.Job)
		}
		if claimResult.Job.State != "claimed" || claimResult.Job.ClaimedBy != workerID || claimResult.Job.LeaseToken == "" {
			t.Fatalf("invalid claim state: %+v", claimResult.Job)
		}

		claimedJobID = claimResult.Job.ID
		activeLeaseToken = claimResult.Job.LeaseToken

		// 3. Second claim returns no job (queue is empty, row locked via SKIP LOCKED)
		claim2Resp, claim2Body := env.workerReq(t, workerPriv, workerID, keyID, "POST", "/internal/v1/worker/jobs/claim", nil)
		if claim2Resp.StatusCode != http.StatusOK {
			t.Fatalf("expected 200, got %d", claim2Resp.StatusCode)
		}
		var claim2Result struct {
			Job *store.Job `json:"job"`
		}
		_ = json.Unmarshal(claim2Body, &claim2Result)
		if claim2Result.Job != nil {
			t.Fatalf("expected nil job for second worker, got %+v", claim2Result.Job)
		}
	})

	t.Run("Scenario B: Execution Lifecycle & Manifest Persistence", func(t *testing.T) {
		// 1. Worker transitions job to running
		startResp, startBody := env.workerReq(t, workerPriv, workerID, keyID, "POST", fmt.Sprintf("/internal/v1/worker/jobs/%s/start", claimedJobID), map[string]string{
			"lease_token": activeLeaseToken,
		})
		if startResp.StatusCode != http.StatusOK {
			t.Fatalf("expected 200 on start, got %d: %s", startResp.StatusCode, string(startBody))
		}
		var startResult struct {
			Job *store.Job `json:"job"`
		}
		_ = json.Unmarshal(startBody, &startResult)
		if startResult.Job.State != "running" {
			t.Fatalf("expected running state, got %s", startResult.Job.State)
		}

		// 2. Worker heartbeats
		hbResp, hbBody := env.workerReq(t, workerPriv, workerID, keyID, "POST", fmt.Sprintf("/internal/v1/worker/jobs/%s/heartbeat", claimedJobID), map[string]interface{}{
			"lease_token":    activeLeaseToken,
			"extend_seconds": 600,
		})
		if hbResp.StatusCode != http.StatusOK {
			t.Fatalf("expected 200 on heartbeat, got %d: %s", hbResp.StatusCode, string(hbBody))
		}

		// 3. Worker completes job with verifiable result manifest
		manifest := map[string]interface{}{
			"schema_version": "1.0",
			"status":         "succeeded",
			"job_id":         claimedJobID,
			"worker_id":      workerID,
			"task_type":      "raster.inspect",
			"tool_versions": map[string]string{
				"worker": "0.1.0",
				"gdal":   "3.8.0",
			},
			"summary": map[string]interface{}{
				"bands":  1,
				"width":  512,
				"height": 512,
				"crs":    "EPSG:4326",
			},
		}
		compResp, compBody := env.workerReq(t, workerPriv, workerID, keyID, "POST", fmt.Sprintf("/internal/v1/worker/jobs/%s/complete", claimedJobID), map[string]interface{}{
			"lease_token": activeLeaseToken,
			"manifest":    manifest,
		})
		if compResp.StatusCode != http.StatusOK {
			t.Fatalf("expected 200 on complete, got %d: %s", compResp.StatusCode, string(compBody))
		}

		// 4. Verify PostgreSQL persistence via User API
		getResp, getBody := env.req(t, "GET", fmt.Sprintf("/api/v1/incidents/%s/jobs/%s", inc.ID, claimedJobID), t1Owner, nil)
		if getResp.StatusCode != http.StatusOK {
			t.Fatalf("failed to retrieve job as owner: %s", string(getBody))
		}
		var retrievedJob store.Job
		_ = json.Unmarshal(getBody, &retrievedJob)
		if retrievedJob.State != "succeeded" {
			t.Fatalf("expected succeeded in postgres, got %s", retrievedJob.State)
		}
		if retrievedJob.Result == nil || retrievedJob.Result["schema_version"] != "1.0" {
			t.Fatalf("persisted result manifest missing or corrupted: %+v", retrievedJob.Result)
		}
	})

	t.Run("Scenario C: Expired Lease Recovery & Requeuing", func(t *testing.T) {
		// 1. Create a second job and claim it
		job2Resp, job2Body := env.req(t, "POST", fmt.Sprintf("/api/v1/incidents/%s/jobs", inc.ID), t1Owner, map[string]interface{}{
			"job_type":        "checksum",
			"idempotency_key": "m021-job-2",
		})
		if job2Resp.StatusCode != http.StatusCreated {
			t.Fatalf("failed to create job2: %s", string(job2Body))
		}
		var job2 store.Job
		_ = json.Unmarshal(job2Body, &job2)

		_, claimBody := env.workerReq(t, workerPriv, workerID, keyID, "POST", "/internal/v1/worker/jobs/claim", nil)
		var claimResult struct {
			Job *store.Job `json:"job"`
		}
		_ = json.Unmarshal(claimBody, &claimResult)
		staleToken := claimResult.Job.LeaseToken

		// 2. Simulate expired lease by directly setting lease_expires_at in past
		ctx := context.Background()
		_, err := env.pool.Exec(ctx, `
			UPDATE public.processing_jobs
			SET lease_expires_at = now() - interval '5 minutes'
			WHERE id = $1;
		`, claimResult.Job.ID)
		if err != nil {
			t.Fatalf("failed to simulate expired lease: %v", err)
		}

		// 3. Stale worker trying to heartbeat or complete is rejected
		hbResp, _ := env.workerReq(t, workerPriv, workerID, keyID, "POST", fmt.Sprintf("/internal/v1/worker/jobs/%s/heartbeat", claimResult.Job.ID), map[string]interface{}{
			"lease_token": staleToken,
		})
		if hbResp.StatusCode != http.StatusForbidden {
			t.Fatalf("expected 403 on expired lease heartbeat, got %d", hbResp.StatusCode)
		}

		// 4. Run lease recovery
		recResp, recBody := env.workerReq(t, workerPriv, workerID, keyID, "POST", "/internal/v1/worker/leases/recover", nil)
		if recResp.StatusCode != http.StatusOK {
			t.Fatalf("expected 200 on lease recovery, got %d: %s", recResp.StatusCode, string(recBody))
		}

		// 5. Verify the job is back in queued state and retry_count = 1
		getResp, getBody := env.req(t, "GET", fmt.Sprintf("/api/v1/incidents/%s/jobs/%s", inc.ID, claimResult.Job.ID), t1Owner, nil)
		if getResp.StatusCode != http.StatusOK {
			t.Fatalf("expected 200 retrieving recovered job, got %d", getResp.StatusCode)
		}
		var recoveredJob store.Job
		_ = json.Unmarshal(getBody, &recoveredJob)
		if recoveredJob.State != "queued" {
			t.Fatalf("expected recovered job to be queued, got %s", recoveredJob.State)
		}
		if recoveredJob.RetryCount != 1 {
			t.Fatalf("expected retry_count = 1, got %d", recoveredJob.RetryCount)
		}
	})

	t.Run("Scenario D: Security & Boundary Enforcement", func(t *testing.T) {
		// 1. Human bearer token rejected on internal worker endpoint
		req, _ := http.NewRequest("POST", env.apiServer.URL+"/internal/v1/worker/jobs/claim", bytes.NewReader([]byte("{}")))
		req.Header.Set("Authorization", "Bearer "+t1Owner)
		client := &http.Client{Timeout: 5 * time.Second}
		resp, _ := client.Do(req)
		if resp.StatusCode != http.StatusUnauthorized {
			t.Fatalf("expected 401 when human token hits worker route, got %d", resp.StatusCode)
		}

		// 2. Worker signature rejected on user API route
		resp2, body2 := env.workerReq(t, workerPriv, workerID, keyID, "GET", "/api/v1/incidents", nil)
		if resp2.StatusCode != http.StatusUnauthorized {
			t.Fatalf("expected 401 when worker hits user API route, got %d: %s", resp2.StatusCode, string(body2))
		}

		// 3. Worker signature with unregistered key rejected
		_, unregisteredPriv, _ := ed25519.GenerateKey(nil)
		resp3, _ := env.workerReq(t, unregisteredPriv, "unknown-worker", "unknown-key", "POST", "/internal/v1/worker/jobs/claim", nil)
		if resp3.StatusCode != http.StatusUnauthorized {
			t.Fatalf("expected 401 for unregistered worker, got %d", resp3.StatusCode)
		}
	})
}
