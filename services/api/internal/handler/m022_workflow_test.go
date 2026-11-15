package handler_test

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/mahitss/rivet-api/internal/auth"
	"github.com/mahitss/rivet-api/internal/database"
	"github.com/mahitss/rivet-api/internal/handler"
	"github.com/mahitss/rivet-api/internal/server"
	"github.com/mahitss/rivet-api/internal/store"
	"github.com/mahitss/rivet-api/internal/workerauth"
	"github.com/mahitss/rivet-api/internal/workerhandler"
)

func TestMission022_FullStackWorkflow(t *testing.T) {
	env := setupTestEnv(t)
	defer env.close()

	// Clean jobs table to avoid state contamination
	_, _ = env.pool.Exec(context.Background(), "DELETE FROM public.processing_jobs;")

	t1Owner := env.tokenFor(user1Owner, "investigator_owner@test.local")
	t2Analyst := env.tokenFor(user2Analyst, "analyst@test.local")
	t3Reviewer := env.tokenFor(user3Reviewer, "reviewer@test.local")
	t5Outsider := env.tokenFor(user5Outsider, "outsider@test.local")

	workerPriv := devWorkerPrivKey(t)
	workerID := workerauth.DefaultDevWorkerID
	keyID := workerauth.DefaultDevKeyID

	var incidentID string
	var acquisitionID string
	var evidenceID string
	var jobID string
	var reportID string

	// =========================================================================
	// Scenario A — Authenticated User
	// =========================================================================
	t.Run("Scenario A: Authenticated User & Identity Propagation", func(t *testing.T) {
		// Valid bearer token returns subject
		resp, body := env.req(t, "GET", "/api/v1/whoami", t1Owner, nil)
		if resp.StatusCode != http.StatusOK {
			t.Fatalf("expected 200 from /whoami, got %d: %s", resp.StatusCode, string(body))
		}
		var whoami map[string]string
		_ = json.Unmarshal(body, &whoami)
		if whoami["subject"] != user1Owner {
			t.Fatalf("expected subject %s, got %s", user1Owner, whoami["subject"])
		}

		// Missing token is rejected with 401
		respAnon, _ := env.req(t, "GET", "/api/v1/whoami", "", nil)
		if respAnon.StatusCode != http.StatusUnauthorized {
			t.Fatalf("expected 401 for anonymous /whoami, got %d", respAnon.StatusCode)
		}

		// Invalid token is rejected with 401
		respBad, _ := env.req(t, "GET", "/api/v1/whoami", "invalid.jwt.token", nil)
		if respBad.StatusCode != http.StatusUnauthorized {
			t.Fatalf("expected 401 for invalid token, got %d", respBad.StatusCode)
		}
	})

	// =========================================================================
	// Scenario B — Incident Workflow & Cross-Incident Isolation
	// =========================================================================
	t.Run("Scenario B: Incident Workflow & Role Membership", func(t *testing.T) {
		// 1. Create incident as user1Owner
		createBody := map[string]interface{}{
			"title":          "M022 Kuwari River Landslide Dam E2E",
			"description":    "End-to-end integration test incident",
			"discovery_west": 79.8,
			"discovery_south": 30.0,
			"discovery_east": 80.0,
			"discovery_north": 30.2,
		}
		resp, body := env.req(t, "POST", "/api/v1/incidents", t1Owner, createBody)
		if resp.StatusCode != http.StatusCreated {
			t.Fatalf("expected 201 creating incident, got %d: %s", resp.StatusCode, string(body))
		}
		var inc store.Incident
		_ = json.Unmarshal(body, &inc)
		incidentID = inc.ID

		// 2. Creator automatically has owner role
		respRole, bodyRole := env.req(t, "GET", "/api/v1/incidents/"+incidentID+"/role", t1Owner, nil)
		if respRole.StatusCode != http.StatusOK {
			t.Fatalf("expected 200 checking owner role, got %d: %s", respRole.StatusCode, string(bodyRole))
		}
		var roleMap map[string]string
		_ = json.Unmarshal(bodyRole, &roleMap)
		if roleMap["role"] != "owner" {
			t.Fatalf("expected owner role, got %s", roleMap["role"])
		}

		// 3. User5 (outsider) cannot access private incident
		respOut, _ := env.req(t, "GET", "/api/v1/incidents/"+incidentID, t5Outsider, nil)
		if respOut.StatusCode != http.StatusNotFound {
			t.Fatalf("expected 404 for outsider accessing incident, got %d", respOut.StatusCode)
		}

		// 4. Owner adds user2Analyst and user3Reviewer
		addAnalyst := map[string]string{"user_id": user2Analyst, "role": "analyst"}
		respAddA, _ := env.req(t, "POST", "/api/v1/incidents/"+incidentID+"/members", t1Owner, addAnalyst)
		if respAddA.StatusCode != http.StatusCreated {
			t.Fatalf("expected 201 adding analyst, got %d", respAddA.StatusCode)
		}

		addReviewer := map[string]string{"user_id": user3Reviewer, "role": "reviewer"}
		respAddR, _ := env.req(t, "POST", "/api/v1/incidents/"+incidentID+"/members", t1Owner, addReviewer)
		if respAddR.StatusCode != http.StatusCreated {
			t.Fatalf("expected 201 adding reviewer, got %d", respAddR.StatusCode)
		}

		// 5. Verify user2Analyst now has analyst role
		respA2, bodyA2 := env.req(t, "GET", "/api/v1/incidents/"+incidentID+"/role", t2Analyst, nil)
		if respA2.StatusCode != http.StatusOK {
			t.Fatalf("expected 200 for analyst role, got %d", respA2.StatusCode)
		}
		var roleA2 map[string]string
		_ = json.Unmarshal(bodyA2, &roleA2)
		if roleA2["role"] != "analyst" {
			t.Fatalf("expected analyst role, got %s", roleA2["role"])
		}
	})

	// =========================================================================
	// Scenario C — Evidence & Institutional Review Workflow
	// =========================================================================
	t.Run("Scenario C: Acquisition, Evidence & Conflict-of-Interest Review", func(t *testing.T) {
		// 1. Analyst registers acquisition
		acqBody := map[string]interface{}{
			"source_provider":  "NASA-JPL",
			"granule_id":       "NISAR_L2_PR_GCOV_001_005_D_073_4000_HHHV_A_20260906T132236_M022",
			"crid":             "P05023",
			"product_maturity": "provisional",
		}
		respAcq, bodyAcq := env.req(t, "POST", "/api/v1/incidents/"+incidentID+"/acquisitions", t2Analyst, acqBody)
		if respAcq.StatusCode != http.StatusCreated {
			t.Fatalf("expected 201 registering acquisition, got %d: %s", respAcq.StatusCode, string(bodyAcq))
		}
		var acq store.Acquisition
		_ = json.Unmarshal(bodyAcq, &acq)
		acquisitionID = acq.ID

		// 2. Analyst creates evidence
		evBody := map[string]interface{}{
			"acquisition_id": acquisitionID,
			"claim_level":    "observation",
			"evidence_kind":  "observation",
			"title":          "M022 Backscatter Baseline Observation",
			"summary":        "Provisional GCOV backscatter threshold observation",
			"source_path":    "data/manifests/mission006_sweep.json",
		}
		respEv, bodyEv := env.req(t, "POST", "/api/v1/incidents/"+incidentID+"/evidence", t2Analyst, evBody)
		if respEv.StatusCode != http.StatusCreated {
			t.Fatalf("expected 201 submitting evidence, got %d: %s", respEv.StatusCode, string(bodyEv))
		}
		var ev store.Evidence
		_ = json.Unmarshal(bodyEv, &ev)
		evidenceID = ev.ID
		if ev.ReviewState != "draft" {
			t.Fatalf("expected initial review state 'draft', got %s", ev.ReviewState)
		}

		// 3. Self-review rejected: analyst cannot review their own evidence
		decBody := map[string]string{
			"decision":  "accept",
			"rationale": "Analyst attempting self-review",
		}
		respSelf, _ := env.req(t, "POST", "/api/v1/incidents/"+incidentID+"/evidence/"+evidenceID+"/decisions", t2Analyst, decBody)
		if respSelf.StatusCode != http.StatusForbidden {
			t.Fatalf("expected 403 on self-review attempt, got %d", respSelf.StatusCode)
		}

		// 4. Eligible independent reviewer approves evidence
		revBody := map[string]string{
			"decision":  "accept",
			"rationale": "Independent reviewer verified P05023 Group D40 comparability group.",
		}
		respRev, bodyRev := env.req(t, "POST", "/api/v1/incidents/"+incidentID+"/evidence/"+evidenceID+"/decisions", t3Reviewer, revBody)
		if respRev.StatusCode != http.StatusCreated {
			t.Fatalf("expected 201 on valid review decision, got %d: %s", respRev.StatusCode, string(bodyRev))
		}

		// 5. Verify review state changed to 'accepted'
		respCheck, bodyCheck := env.req(t, "GET", "/api/v1/incidents/"+incidentID+"/evidence/"+evidenceID, t2Analyst, nil)
		if respCheck.StatusCode != http.StatusOK {
			t.Fatalf("expected 200 getting evidence, got %d", respCheck.StatusCode)
		}
		var updatedEv store.Evidence
		_ = json.Unmarshal(bodyCheck, &updatedEv)
		if updatedEv.ReviewState != "accepted" {
			t.Fatalf("expected review state 'accepted', got %s", updatedEv.ReviewState)
		}
	})

	// =========================================================================
	// Scenario D — Processing Workflow (Go API + PostgreSQL + Worker)
	// =========================================================================
	t.Run("Scenario D: End-to-End Processing Workflow & Manifest Persistence", func(t *testing.T) {
		// 1. Analyst submits job request to Go API
		jobReq := map[string]interface{}{
			"job_type":        "checksum",
			"idempotency_key": "m022-e2e-checksum-1",
			"payload": map[string]interface{}{
				"task_type": "checksum",
				"path":      "data/manifests/mission006_sweep.json",
			},
		}
		respJob, bodyJob := env.req(t, "POST", "/api/v1/incidents/"+incidentID+"/jobs", t2Analyst, jobReq)
		if respJob.StatusCode != http.StatusCreated {
			t.Fatalf("expected 201 creating job, got %d: %s", respJob.StatusCode, string(bodyJob))
		}
		var j store.Job
		_ = json.Unmarshal(bodyJob, &j)
		jobID = j.ID
		if j.State != "queued" {
			t.Fatalf("expected initial state 'queued', got %s", j.State)
		}

		// 2. Python worker claims job via /internal/v1/worker/jobs/claim with Ed25519 signature
		claimReq := map[string]interface{}{
			"lease_duration_seconds": 300,
		}
		respClaim, bodyClaim := env.workerReq(t, workerPriv, workerID, keyID, "POST", "/internal/v1/worker/jobs/claim", claimReq)
		if respClaim.StatusCode != http.StatusOK {
			t.Fatalf("expected 200 claiming job, got %d: %s", respClaim.StatusCode, string(bodyClaim))
		}
		var claimWrap struct {
			Job *store.Job `json:"job"`
		}
		_ = json.Unmarshal(bodyClaim, &claimWrap)
		if claimWrap.Job == nil || claimWrap.Job.ID != jobID {
			t.Fatalf("expected claimed job %s, got %+v", jobID, claimWrap.Job)
		}
		leaseToken := claimWrap.Job.LeaseToken

		// 3. Worker starts job -> state becomes 'running'
		startReq := map[string]string{"lease_token": leaseToken}
		respStart, _ := env.workerReq(t, workerPriv, workerID, keyID, "POST", "/internal/v1/worker/jobs/"+jobID+"/start", startReq)
		if respStart.StatusCode != http.StatusOK {
			t.Fatalf("expected 200 starting job, got %d", respStart.StatusCode)
		}

		// 4. Worker sends heartbeat -> extends lease
		hbReq := map[string]interface{}{
			"lease_token":            leaseToken,
			"extend_seconds": 300,
		}
		respHb, _ := env.workerReq(t, workerPriv, workerID, keyID, "POST", "/internal/v1/worker/jobs/"+jobID+"/heartbeat", hbReq)
		if respHb.StatusCode != http.StatusOK {
			t.Fatalf("expected 200 on heartbeat, got %d", respHb.StatusCode)
		}

		// 5. Worker completes job with versioned "1.0" scientific result manifest
		resultManifest := map[string]interface{}{
			"schema_version": "1.0",
			"status":         "succeeded",
			"worker_id":      workerID,
			"task_type":      "checksum",
			"completed_at":   time.Now().UTC().Format(time.RFC3339),
			"duration_ms":    12.4,
			"code_provenance": map[string]string{
				"git_commit":     "b5a4a7e26a53a23d6a6dffa002164ecb9d9a37a6",
				"python_version": "3.12.13",
			},
			"outputs": map[string]interface{}{
				"sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
			},
			"artifacts": []interface{}{},
		}
		completeReq := map[string]interface{}{
			"lease_token": leaseToken,
			"manifest":    resultManifest,
		}
		respComp, bodyComp := env.workerReq(t, workerPriv, workerID, keyID, "POST", "/internal/v1/worker/jobs/"+jobID+"/complete", completeReq)
		if respComp.StatusCode != http.StatusOK {
			t.Fatalf("expected 200 completing job, got %d: %s", respComp.StatusCode, string(bodyComp))
		}

		// 6. User queries job via Go API -> state is 'succeeded' and result manifest is persisted
		respFinal, bodyFinal := env.req(t, "GET", "/api/v1/incidents/"+incidentID+"/jobs/"+jobID, t2Analyst, nil)
		if respFinal.StatusCode != http.StatusOK {
			t.Fatalf("expected 200 getting completed job, got %d", respFinal.StatusCode)
		}
		var completedJob store.Job
		_ = json.Unmarshal(bodyFinal, &completedJob)
		if completedJob.State != "succeeded" {
			t.Fatalf("expected state 'succeeded', got %s", completedJob.State)
		}
		if completedJob.Result == nil || completedJob.Result["schema_version"] != "1.0" {
			t.Fatalf("expected persisted result manifest, got %+v", completedJob.Result)
		}
	})

	// =========================================================================
	// Scenario E — Reports, Audit Events & Traceability
	// =========================================================================
	t.Run("Scenario E: Reports & Immutable Audit Traceability", func(t *testing.T) {
		// 1. Generate report
		repReq := map[string]interface{}{
			"title": "M022 Final Integration Report",
			"content": map[string]interface{}{
				"status":      "reproducible",
				"incident_id": incidentID,
			},
		}
		respRep, bodyRep := env.req(t, "POST", "/api/v1/incidents/"+incidentID+"/reports", t1Owner, repReq)
		if respRep.StatusCode != http.StatusCreated {
			t.Fatalf("expected 201 creating report, got %d: %s", respRep.StatusCode, string(bodyRep))
		}
		var rep store.Report
		_ = json.Unmarshal(bodyRep, &rep)
		reportID = rep.ID

		// 2. Fetch audit trail for incident
		respAudit, bodyAudit := env.req(t, "GET", "/api/v1/incidents/"+incidentID+"/audit", t1Owner, nil)
		if respAudit.StatusCode != http.StatusOK {
			t.Fatalf("expected 200 fetching audit events, got %d", respAudit.StatusCode)
		}
		var auditEvents []*store.AuditEvent
		_ = json.Unmarshal(bodyAudit, &auditEvents)
		if len(auditEvents) == 0 {
			t.Fatalf("expected audit events to be recorded, got 0")
		}

		// Verify audit events recorded our operations
		hasIncidentAudit := false
		hasEvidenceAudit := false
		hasDecisionAudit := false
		for _, ae := range auditEvents {
			if ae.EntityTable == "incidents" {
				hasIncidentAudit = true
			}
			if ae.EntityTable == "evidence_records" {
				hasEvidenceAudit = true
			}
			if ae.EntityTable == "decisions" {
				hasDecisionAudit = true
			}
		}
		if !hasIncidentAudit || !hasEvidenceAudit || !hasDecisionAudit {
			t.Fatalf("missing expected audit events: incident=%v, evidence=%v, decision=%v",
				hasIncidentAudit, hasEvidenceAudit, hasDecisionAudit)
		}
	})

	// =========================================================================
	// Scenario F — Restart Persistence
	// =========================================================================
	t.Run("Scenario F: Persistence across Full Service Restart", func(t *testing.T) {
		// Close existing HTTP server and DB pool
		env.apiServer.Close()
		env.pool.Close()

		// Reopen fresh connection pool to the same PostgreSQL database
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		newPool, err := pgxpool.New(ctx, env.dbURL)
		if err != nil {
			t.Fatalf("reconnecting pool failed: %v", err)
		}
		defer newPool.Close()

		newRepo := database.NewPostgresRepository()
		newTxMgr := database.NewTxManager(newPool)
		newH := handler.New(newRepo, newTxMgr)
		verifier := auth.NewVerifier(env.cfg.JWKSURL, env.cfg.JWTIssuer, env.cfg.JWTAudience, env.cfg.HTTPTimeout, env.cfg.JWTLeeway)
		newWorkerH := workerhandler.New(newRepo, newTxMgr)
		newWorkerRegistry := workerauth.NewKeyRegistry()
		newWorkerRegistry.RegisterDevKey()
		newSrv := server.New(env.cfg, newH, verifier, newWorkerH, newWorkerRegistry)
		newAPIServer := httptest.NewServer(newSrv.Handler)
		defer newAPIServer.Close()

		env.apiServer = newAPIServer
		env.pool = newPool

		// Verify incident survived restart
		respInc, bodyInc := env.req(t, "GET", "/api/v1/incidents/"+incidentID, t1Owner, nil)
		if respInc.StatusCode != http.StatusOK {
			t.Fatalf("expected 200 for incident after restart, got %d: %s", respInc.StatusCode, string(bodyInc))
		}

		// Verify evidence review state 'accepted' survived restart
		respEv, bodyEv := env.req(t, "GET", "/api/v1/incidents/"+incidentID+"/evidence/"+evidenceID, t1Owner, nil)
		if respEv.StatusCode != http.StatusOK {
			t.Fatalf("expected 200 for evidence after restart, got %d", respEv.StatusCode)
		}
		var ev store.Evidence
		_ = json.Unmarshal(bodyEv, &ev)
		if ev.ReviewState != "accepted" {
			t.Fatalf("expected review_state 'accepted' to survive restart, got %s", ev.ReviewState)
		}

		// Verify processing job state 'succeeded' and result manifest survived restart
		respJob, bodyJob := env.req(t, "GET", "/api/v1/incidents/"+incidentID+"/jobs/"+jobID, t1Owner, nil)
		if respJob.StatusCode != http.StatusOK {
			t.Fatalf("expected 200 for job after restart, got %d", respJob.StatusCode)
		}
		var j store.Job
		_ = json.Unmarshal(bodyJob, &j)
		if j.State != "succeeded" {
			t.Fatalf("expected job state 'succeeded' to survive restart, got %s", j.State)
		}
		if j.Result == nil || j.Result["schema_version"] != "1.0" {
			t.Fatalf("expected job result to survive restart, got %+v", j.Result)
		}

		// Verify report survived restart
		respRep, _ := env.req(t, "GET", "/api/v1/incidents/"+incidentID+"/reports/"+reportID, t1Owner, nil)
		if respRep.StatusCode != http.StatusOK {
			t.Fatalf("expected 200 for report after restart, got %d", respRep.StatusCode)
		}

		// Verify outsider is STILL denied access after restart
		respOutsider, _ := env.req(t, "GET", "/api/v1/incidents/"+incidentID, t5Outsider, nil)
		if respOutsider.StatusCode != http.StatusNotFound {
			t.Fatalf("expected 404 for outsider after restart, got %d", respOutsider.StatusCode)
		}
	})
}
