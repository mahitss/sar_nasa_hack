package handler_test

import (
	"bytes"
	"context"
	"crypto/rand"
	"crypto/rsa"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/mahitss/rivet-api/internal/auth"
	"github.com/mahitss/rivet-api/internal/config"
	"github.com/mahitss/rivet-api/internal/database"
	"github.com/mahitss/rivet-api/internal/handler"
	"github.com/mahitss/rivet-api/internal/server"
	"github.com/mahitss/rivet-api/internal/store"
	"github.com/mahitss/rivet-api/internal/workerauth"
	"github.com/mahitss/rivet-api/internal/workerhandler"
)

const (
	testIssuer   = "http://test.supabase.local/auth/v1"
	testAudience = "authenticated"
	testKID      = "test-key-id"

	user1Owner    = "11111111-1111-1111-1111-111111111111"
	user2Analyst  = "22222222-2222-2222-2222-222222222222"
	user3Reviewer = "33333333-3333-3333-3333-333333333333"
	user4Viewer   = "44444444-4444-4444-4444-444444444444"
	user5Outsider = "55555555-5555-5555-5555-555555555555"
)

type testEnv struct {
	pool       *pgxpool.Pool
	privKey    *rsa.PrivateKey
	jwksServer *httptest.Server
	apiServer  *httptest.Server
	cfg        config.Config
	dbURL      string
}

func setupTestEnv(t *testing.T) *testEnv {
	dbURL := os.Getenv("DATABASE_URL")
	if dbURL == "" {
		dbURL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	pool, err := pgxpool.New(ctx, dbURL)
	if err != nil {
		t.Skipf("skipping integration test: database not available: %v", err)
	}
	if err := pool.Ping(ctx); err != nil {
		pool.Close()
		t.Skipf("skipping integration test: database ping failed: %v", err)
	}

	// Seed test users in auth.users
	users := []struct {
		id    string
		email string
	}{
		{user1Owner, "owner@test.local"},
		{user2Analyst, "analyst@test.local"},
		{user3Reviewer, "reviewer@test.local"},
		{user4Viewer, "viewer@test.local"},
		{user5Outsider, "outsider@test.local"},
	}
	for _, u := range users {
		_, err := pool.Exec(ctx, `
			INSERT INTO auth.users (id, instance_id, aud, role, email, encrypted_password, email_confirmed_at, created_at, updated_at)
			VALUES ($1, '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', $2, 'dummy', now(), now(), now())
			ON CONFLICT (id) DO NOTHING;
		`, u.id, u.email)
		if err != nil {
			t.Fatalf("failed to seed test user %s: %v", u.email, err)
		}
	}

	privKey, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		t.Fatalf("failed to generate rsa key: %v", err)
	}

	pub := &privKey.PublicKey
	n := base64.RawURLEncoding.EncodeToString(pub.N.Bytes())
	eBytes := []byte{byte(pub.E >> 16), byte(pub.E >> 8), byte(pub.E)}
	for len(eBytes) > 1 && eBytes[0] == 0 {
		eBytes = eBytes[1:]
	}
	e := base64.RawURLEncoding.EncodeToString(eBytes)

	doc := map[string]interface{}{
		"keys": []map[string]string{{
			"kty": "RSA", "kid": testKID, "use": "sig", "alg": "RS256",
			"n": n, "e": e,
		}},
	}
	docBytes, _ := json.Marshal(doc)
	jwksServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write(docBytes)
	}))

	cfg := config.Config{
		Env:         "test",
		SupabaseURL: jwksServer.URL,
		JWKSURL:     jwksServer.URL,
		JWTIssuer:   testIssuer,
		JWTAudience: testAudience,
		DatabaseURL: dbURL,
		JWTLeeway:   30 * time.Second,
		HTTPTimeout: 10 * time.Second,
	}

	repo := database.NewPostgresRepository()
	txMgr := database.NewTxManager(pool)
	h := handler.New(repo, txMgr)
	workerH := workerhandler.New(repo, txMgr)
	workerRegistry := workerauth.NewKeyRegistry()
	workerRegistry.RegisterDevKey()
	verifier := auth.NewVerifier(cfg.JWKSURL, cfg.JWTIssuer, cfg.JWTAudience, cfg.HTTPTimeout, cfg.JWTLeeway)
	srv := server.New(cfg, h, verifier, workerH, workerRegistry)
	apiServer := httptest.NewServer(srv.Handler)

	return &testEnv{
		pool:       pool,
		privKey:    privKey,
		jwksServer: jwksServer,
		apiServer:  apiServer,
		cfg:        cfg,
		dbURL:      dbURL,
	}
}

func (e *testEnv) close() {
	if e.pool != nil {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		_, _ = e.pool.Exec(ctx, `
			DELETE FROM public.incidents WHERE created_by IN (
				'11111111-1111-1111-1111-111111111111'::uuid,
				'22222222-2222-2222-2222-222222222222'::uuid,
				'33333333-3333-3333-3333-333333333333'::uuid,
				'44444444-4444-4444-4444-444444444444'::uuid,
				'55555555-5555-5555-5555-555555555555'::uuid
			);
		`)
		cancel()
	}
	if e.apiServer != nil {
		e.apiServer.Close()
	}
	if e.jwksServer != nil {
		e.jwksServer.Close()
	}
	if e.pool != nil {
		e.pool.Close()
	}
}

func (e *testEnv) tokenFor(sub, email string) string {
	claims := jwt.MapClaims{
		"sub":   sub,
		"iss":   testIssuer,
		"aud":   testAudience,
		"exp":   time.Now().Add(2 * time.Hour).Unix(),
		"email": email,
		"role":  "authenticated",
	}
	tok := jwt.NewWithClaims(jwt.SigningMethodRS256, claims)
	tok.Header["kid"] = testKID
	s, _ := tok.SignedString(e.privKey)
	return s
}

func (e *testEnv) req(t *testing.T, method, path, token string, body interface{}) (*http.Response, []byte) {
	var bodyReader io.Reader
	if body != nil {
		b, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("json marshal: %v", err)
		}
		bodyReader = bytes.NewReader(b)
	}

	req, err := http.NewRequest(method, e.apiServer.URL+path, bodyReader)
	if err != nil {
		t.Fatalf("http.NewRequest: %v", err)
	}
	req.Header.Set("Content-Type", "application/json")
	if token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("http.Do: %v", err)
	}
	respBytes, err := io.ReadAll(resp.Body)
	_ = resp.Body.Close()
	if err != nil {
		t.Fatalf("read body: %v", err)
	}
	return resp, respBytes
}

func TestMission019_EndToEndAPIIntegration(t *testing.T) {
	env := setupTestEnv(t)
	defer env.close()

	t1Owner := env.tokenFor(user1Owner, "owner@test.local")
	t2Analyst := env.tokenFor(user2Analyst, "analyst@test.local")
	t3Reviewer := env.tokenFor(user3Reviewer, "reviewer@test.local")
	t4Viewer := env.tokenFor(user4Viewer, "viewer@test.local")
	t5Outsider := env.tokenFor(user5Outsider, "outsider@test.local")

	var incidentID string
	var acqID string
	var evidenceID string
	var decisionID string
	var jobID string
	var reportID string

	// 1. Create incident as User 1 (Creator)
	t.Run("1. Create incident", func(t *testing.T) {
		resp, body := env.req(t, "POST", "/api/v1/incidents", t1Owner, map[string]interface{}{
			"title":       "Kuwari Valley Landslide Dam",
			"description": "Integration test incident for synthetic NISAR validation",
		})
		if resp.StatusCode != http.StatusCreated {
			t.Fatalf("expected 201, got %d: %s", resp.StatusCode, string(body))
		}
		var inc store.Incident
		if err := json.Unmarshal(body, &inc); err != nil {
			t.Fatalf("unmarshal incident: %v", err)
		}
		if inc.ID == "" || inc.Title != "Kuwari Valley Landslide Dam" || inc.CreatedBy != user1Owner {
			t.Fatalf("unexpected incident payload: %+v", inc)
		}
		incidentID = inc.ID
	})

	// 2. Verify automatic owner membership
	t.Run("2. Automatic owner membership", func(t *testing.T) {
		var role string
		err := env.pool.QueryRow(context.Background(), `
			SELECT role FROM public.incident_members WHERE incident_id = $1 AND user_id = $2
		`, incidentID, user1Owner).Scan(&role)
		if err != nil {
			t.Fatalf("failed to query owner membership: %v", err)
		}
		if role != "owner" {
			t.Fatalf("expected owner role, got %s", role)
		}
	})

	// 3. Retrieve incident as creator
	t.Run("3. Retrieve incident as creator", func(t *testing.T) {
		resp, body := env.req(t, "GET", "/api/v1/incidents/"+incidentID, t1Owner, nil)
		if resp.StatusCode != http.StatusOK {
			t.Fatalf("expected 200, got %d: %s", resp.StatusCode, string(body))
		}
		var inc store.Incident
		if err := json.Unmarshal(body, &inc); err != nil {
			t.Fatalf("unmarshal incident: %v", err)
		}
		if inc.ID != incidentID {
			t.Fatalf("incident id mismatch: got %s, want %s", inc.ID, incidentID)
		}
	})

	// 4. Reject retrieval as non-member
	t.Run("4. Reject retrieval as non-member", func(t *testing.T) {
		resp, _ := env.req(t, "GET", "/api/v1/incidents/"+incidentID, t5Outsider, nil)
		if resp.StatusCode != http.StatusNotFound {
			t.Fatalf("expected 404 for non-member, got %d", resp.StatusCode)
		}
	})

	// Add incident members (Analyst, Reviewer, Viewer)
	t.Run("Add incident members", func(t *testing.T) {
		ctx := context.Background()
		_, err := env.pool.Exec(ctx, `
			INSERT INTO public.incident_members (incident_id, user_id, role)
			VALUES
				($1, $2, 'analyst'),
				($1, $3, 'reviewer'),
				($1, $4, 'viewer')
		`, incidentID, user2Analyst, user3Reviewer, user4Viewer)
		if err != nil {
			t.Fatalf("failed to add incident members: %v", err)
		}
	})

	// 5. Create acquisition
	t.Run("5. Create acquisition", func(t *testing.T) {
		// Viewer must be forbidden
		resp, _ := env.req(t, "POST", "/api/v1/incidents/"+incidentID+"/acquisitions", t4Viewer, map[string]string{
			"source_provider":  "ISRO-NASA",
			"granule_id":       "NISAR_L2_PR_GCOV_001_002_A_040_2000_D_20260906T120000",
			"crid":             "P05023",
			"product_maturity": "provisional",
		})
		if resp.StatusCode != http.StatusForbidden {
			t.Fatalf("expected 403 for viewer creating acquisition, got %d", resp.StatusCode)
		}

		// Analyst succeeds
		resp, body := env.req(t, "POST", "/api/v1/incidents/"+incidentID+"/acquisitions", t2Analyst, map[string]string{
			"source_provider":  "ISRO-NASA",
			"granule_id":       "NISAR_L2_PR_GCOV_001_002_A_040_2000_D_20260906T120000",
			"crid":             "P05023",
			"product_maturity": "provisional",
		})
		if resp.StatusCode != http.StatusCreated {
			t.Fatalf("expected 201, got %d: %s", resp.StatusCode, string(body))
		}
		var acq store.Acquisition
		if err := json.Unmarshal(body, &acq); err != nil {
			t.Fatalf("unmarshal acquisition: %v", err)
		}
		if acq.ID == "" || acq.GranuleID != "NISAR_L2_PR_GCOV_001_002_A_040_2000_D_20260906T120000" {
			t.Fatalf("unexpected acquisition payload: %+v", acq)
		}
		acqID = acq.ID
	})

	// 6. Create draft evidence
	t.Run("6. Create draft evidence", func(t *testing.T) {
		// Viewer forbidden
		resp, _ := env.req(t, "POST", "/api/v1/incidents/"+incidentID+"/evidence", t4Viewer, map[string]string{
			"acquisition_id": acqID,
			"claim_level":    "observation",
			"evidence_kind":  "observation",
			"title":          "Viewer attempt",
			"summary":        "Forbidden attempt",
			"source_path":    "data/raw/attempt.h5",
		})
		if resp.StatusCode != http.StatusForbidden {
			t.Fatalf("expected 403 for viewer, got %d", resp.StatusCode)
		}

		// Analyst creates draft evidence
		resp, body := env.req(t, "POST", "/api/v1/incidents/"+incidentID+"/evidence", t2Analyst, map[string]string{
			"acquisition_id": acqID,
			"claim_level":    "observation",
			"evidence_kind":  "observation",
			"title":          "GCOV backscatter extract",
			"summary":        "Provisional 40 MHz backscatter dual-pol tile extract",
			"source_path":    "data/manifests/gcov_tile.h5",
		})
		if resp.StatusCode != http.StatusCreated {
			t.Fatalf("expected 201, got %d: %s", resp.StatusCode, string(body))
		}
		var ev store.Evidence
		if err := json.Unmarshal(body, &ev); err != nil {
			t.Fatalf("unmarshal evidence: %v", err)
		}
		if ev.ID == "" || ev.ReviewState != "draft" || ev.CreatedBy != user2Analyst {
			t.Fatalf("unexpected evidence payload: %+v", ev)
		}
		evidenceID = ev.ID
	})

	// 7. Reject analyst review decision & Reject author self-review
	t.Run("7. Reject analyst review decision & self-review", func(t *testing.T) {
		// User 2 (Analyst & Creator) attempts review -> Forbidden (both role & self-review)
		resp, _ := env.req(t, "POST", "/api/v1/incidents/"+incidentID+"/evidence/"+evidenceID+"/decisions", t2Analyst, map[string]string{
			"decision":  "accept",
			"rationale": "Analyst self-approving",
		})
		if resp.StatusCode != http.StatusForbidden {
			t.Fatalf("expected 403 for analyst review attempt, got %d", resp.StatusCode)
		}

		// User 1 creates evidence E2, User 2 (Analyst) attempts review on E2 -> Forbidden (analyst cannot review)
		respE2, bodyE2 := env.req(t, "POST", "/api/v1/incidents/"+incidentID+"/evidence", t1Owner, map[string]string{
			"acquisition_id": acqID,
			"claim_level":    "observation",
			"evidence_kind":  "observation",
			"title":          "Owner evidence E2",
			"summary":        "Summary E2",
			"source_path":    "data/manifests/e2.h5",
		})
		if respE2.StatusCode != http.StatusCreated {
			t.Fatalf("failed to create E2: %d", respE2.StatusCode)
		}
		var e2 store.Evidence
		_ = json.Unmarshal(bodyE2, &e2)

		resp, _ = env.req(t, "POST", "/api/v1/incidents/"+incidentID+"/evidence/"+e2.ID+"/decisions", t2Analyst, map[string]string{
			"decision":  "accept",
			"rationale": "Analyst cannot review",
		})
		if resp.StatusCode != http.StatusForbidden {
			t.Fatalf("expected 403 for analyst role reviewing evidence, got %d", resp.StatusCode)
		}

		// User 1 (Owner & Creator of E2) attempts self-review on E2 -> Forbidden
		resp, _ = env.req(t, "POST", "/api/v1/incidents/"+incidentID+"/evidence/"+e2.ID+"/decisions", t1Owner, map[string]string{
			"decision":  "accept",
			"rationale": "Self review on E2",
		})
		if resp.StatusCode != http.StatusForbidden {
			t.Fatalf("expected 403 for owner reviewing own evidence, got %d", resp.StatusCode)
		}
	})

	// 8. Accept review by authorized reviewer
	t.Run("8. Accept review by authorized reviewer", func(t *testing.T) {
		// User 3 (Reviewer) approves User 2's evidence
		resp, body := env.req(t, "POST", "/api/v1/incidents/"+incidentID+"/evidence/"+evidenceID+"/decisions", t3Reviewer, map[string]string{
			"decision":  "accept",
			"rationale": "Verified acquisition comparability and CRID match P05023.",
		})
		if resp.StatusCode != http.StatusCreated {
			t.Fatalf("expected 201, got %d: %s", resp.StatusCode, string(body))
		}
		var dec store.Decision
		if err := json.Unmarshal(body, &dec); err != nil {
			t.Fatalf("unmarshal decision: %v", err)
		}
		if dec.ID == "" || dec.Decision != "accept" || dec.ReviewerID != user3Reviewer {
			t.Fatalf("unexpected decision payload: %+v", dec)
		}
		decisionID = dec.ID
	})

	// 9. Verify review state and decision persistence
	t.Run("9. Verify review state and decision persistence", func(t *testing.T) {
		// Retrieve evidence and check review_state is "accepted"
		resp, body := env.req(t, "GET", "/api/v1/incidents/"+incidentID+"/evidence/"+evidenceID, t1Owner, nil)
		if resp.StatusCode != http.StatusOK {
			t.Fatalf("expected 200, got %d: %s", resp.StatusCode, string(body))
		}
		var ev store.Evidence
		if err := json.Unmarshal(body, &ev); err != nil {
			t.Fatalf("unmarshal evidence: %v", err)
		}
		if ev.ReviewState != "accepted" {
			t.Fatalf("expected review_state 'accepted', got %s", ev.ReviewState)
		}

		// Direct patch attempt on review_state must be ignored
		respPatch, bodyPatch := env.req(t, "PATCH", "/api/v1/incidents/"+incidentID+"/evidence/"+evidenceID, t1Owner, map[string]interface{}{
			"title":        "Updated GCOV backscatter extract",
			"review_state": "draft",
		})
		if respPatch.StatusCode != http.StatusOK {
			t.Fatalf("expected 200 on patch, got %d: %s", respPatch.StatusCode, string(bodyPatch))
		}
		var evPatched store.Evidence
		if err := json.Unmarshal(bodyPatch, &evPatched); err != nil {
			t.Fatalf("unmarshal patched: %v", err)
		}
		if evPatched.Title != "Updated GCOV backscatter extract" {
			t.Fatalf("title not updated: %s", evPatched.Title)
		}
		if evPatched.ReviewState != "accepted" {
			t.Fatalf("review_state was mutated directly! got %s", evPatched.ReviewState)
		}
	})

	// 10. Create and retrieve processing job
	t.Run("10. Create and retrieve processing job", func(t *testing.T) {
		idempotencyKey := fmt.Sprintf("job-idemp-%d", time.Now().UnixNano())

		// Viewer forbidden
		resp, _ := env.req(t, "POST", "/api/v1/incidents/"+incidentID+"/jobs", t4Viewer, map[string]string{
			"job_type":        "water_candidate_extract",
			"idempotency_key": idempotencyKey,
		})
		if resp.StatusCode != http.StatusForbidden {
			t.Fatalf("expected 403 for viewer job creation, got %d", resp.StatusCode)
		}

		// Analyst succeeds
		resp, body := env.req(t, "POST", "/api/v1/incidents/"+incidentID+"/jobs", t2Analyst, map[string]string{
			"job_type":        "water_candidate_extract",
			"idempotency_key": idempotencyKey,
		})
		if resp.StatusCode != http.StatusCreated {
			t.Fatalf("expected 201, got %d: %s", resp.StatusCode, string(body))
		}
		var job store.Job
		if err := json.Unmarshal(body, &job); err != nil {
			t.Fatalf("unmarshal job: %v", err)
		}
		if job.ID == "" || job.State != "queued" || job.IdempotencyKey != idempotencyKey {
			t.Fatalf("unexpected job payload: %+v", job)
		}
		jobID = job.ID

		// Duplicate idempotency key returns 409 Conflict
		respDup, _ := env.req(t, "POST", "/api/v1/incidents/"+incidentID+"/jobs", t2Analyst, map[string]string{
			"job_type":        "water_candidate_extract",
			"idempotency_key": idempotencyKey,
		})
		if respDup.StatusCode != http.StatusConflict {
			t.Fatalf("expected 409 Conflict on duplicate idempotency key, got %d", respDup.StatusCode)
		}

		// Retrieve job
		respGet, bodyGet := env.req(t, "GET", "/api/v1/incidents/"+incidentID+"/jobs/"+jobID, t1Owner, nil)
		if respGet.StatusCode != http.StatusOK {
			t.Fatalf("expected 200, got %d: %s", respGet.StatusCode, string(bodyGet))
		}
		var getJob store.Job
		_ = json.Unmarshal(bodyGet, &getJob)
		if getJob.ID != jobID {
			t.Fatalf("job id mismatch: %s vs %s", getJob.ID, jobID)
		}
	})

	// 11. Generate and retrieve report
	t.Run("11. Generate and retrieve report", func(t *testing.T) {
		// Viewer forbidden
		resp, _ := env.req(t, "POST", "/api/v1/incidents/"+incidentID+"/reports", t4Viewer, map[string]interface{}{
			"title":   "Viewer report",
			"content": map[string]interface{}{"note": "illegal"},
		})
		if resp.StatusCode != http.StatusForbidden {
			t.Fatalf("expected 403 for viewer, got %d", resp.StatusCode)
		}

		// Analyst generates report
		resp, body := env.req(t, "POST", "/api/v1/incidents/"+incidentID+"/reports", t2Analyst, map[string]interface{}{
			"title": "Kuwari Mission 019 Report",
			"content": map[string]interface{}{
				"methodology": "Two-scene water candidate GCOV backscatter",
				"crid":        "P05023",
				"status":      "provisional",
			},
		})
		if resp.StatusCode != http.StatusCreated {
			t.Fatalf("expected 201, got %d: %s", resp.StatusCode, string(body))
		}
		var rep store.Report
		if err := json.Unmarshal(body, &rep); err != nil {
			t.Fatalf("unmarshal report: %v", err)
		}
		if rep.ID == "" || rep.Title != "Kuwari Mission 019 Report" || rep.GeneratedBy != user2Analyst {
			t.Fatalf("unexpected report payload: %+v", rep)
		}
		reportID = rep.ID

		// Retrieve report as member
		respGet, bodyGet := env.req(t, "GET", "/api/v1/incidents/"+incidentID+"/reports/"+reportID, t1Owner, nil)
		if respGet.StatusCode != http.StatusOK {
			t.Fatalf("expected 200, got %d: %s", respGet.StatusCode, string(bodyGet))
		}
		var getRep store.Report
		_ = json.Unmarshal(bodyGet, &getRep)
		if getRep.ID != reportID || getRep.Title != rep.Title {
			t.Fatalf("report mismatch: %+v", getRep)
		}

		// Non-member rejected with 404
		respOut, _ := env.req(t, "GET", "/api/v1/incidents/"+incidentID+"/reports/"+reportID, t5Outsider, nil)
		if respOut.StatusCode != http.StatusNotFound {
			t.Fatalf("expected 404 for non-member report retrieval, got %d", respOut.StatusCode)
		}
	})

	// 12. Verify audit event generation
	t.Run("12. Verify audit event generation", func(t *testing.T) {
		ctx := context.Background()
		var count int
		err := env.pool.QueryRow(ctx, `
			SELECT count(*) FROM public.audit_events WHERE incident_id = $1
		`, incidentID).Scan(&count)
		if err != nil {
			t.Fatalf("failed to query audit events: %v", err)
		}
		if count < 5 {
			t.Fatalf("expected at least 5 audit events for incident, got %d", count)
		}

		// Verify audit immutability: updates or deletes must fail
		_, err = env.pool.Exec(ctx, `UPDATE public.audit_events SET action = 'tampered' WHERE incident_id = $1`, incidentID)
		if err == nil {
			t.Fatal("expected update on audit_events to fail")
		}
		_, err = env.pool.Exec(ctx, `DELETE FROM public.audit_events WHERE incident_id = $1`, incidentID)
		if err == nil {
			t.Fatal("expected delete on audit_events to fail")
		}
	})

	// 13. Verify transaction isolation across pooled connections
	t.Run("13. Connection pool isolation", func(t *testing.T) {
		txMgr := database.NewTxManager(env.pool)

		// Run in tx as user1
		err := txMgr.WithinTransaction(context.Background(), user1Owner, func(ctx context.Context) error {
			tx, ok := database.TxFromContext(ctx)
			if !ok {
				t.Fatal("missing tx in context")
			}
			var sub string
			var role string
			if err := tx.QueryRow(ctx, "SELECT current_setting('request.jwt.claim.sub', true), current_user").Scan(&sub, &role); err != nil {
				return err
			}
			if sub != user1Owner || role != "authenticated" {
				t.Fatalf("claims not set in tx: sub=%s, role=%s", sub, role)
			}
			return nil
		})
		if err != nil {
			t.Fatalf("user1 tx failed: %v", err)
		}

		// Raw connection from pool outside transaction: must NOT have user1 claims or authenticated role!
		var poolSub string
		var poolRole string
		err = env.pool.QueryRow(context.Background(), "SELECT current_setting('request.jwt.claim.sub', true), current_user").Scan(&poolSub, &poolRole)
		if err != nil {
			t.Fatalf("raw pool query failed: %v", err)
		}
		if poolSub != "" {
			t.Fatalf("leaked claim across pooled connection! got %s", poolSub)
		}
		if poolRole != "postgres" {
			t.Fatalf("leaked role across pooled connection! got %s, want postgres", poolRole)
		}

		// Run in tx as user2
		err = txMgr.WithinTransaction(context.Background(), user2Analyst, func(ctx context.Context) error {
			tx, _ := database.TxFromContext(ctx)
			var sub string
			if err := tx.QueryRow(ctx, "SELECT current_setting('request.jwt.claim.sub', true)").Scan(&sub); err != nil {
				return err
			}
			if sub != user2Analyst {
				t.Fatalf("expected user2 in tx, got %s", sub)
			}
			return nil
		})
		if err != nil {
			t.Fatalf("user2 tx failed: %v", err)
		}
	})

	// 14. Get incident role and add member
	t.Run("14. Get incident role and add member", func(t *testing.T) {
		// Owner gets their own role
		resp, body := env.req(t, "GET", "/api/v1/incidents/"+incidentID+"/role", t1Owner, nil)
		if resp.StatusCode != http.StatusOK {
			t.Fatalf("expected 200 for owner role, got %d: %s", resp.StatusCode, string(body))
		}
		var roleResp map[string]string
		_ = json.Unmarshal(body, &roleResp)
		if roleResp["role"] != "owner" {
			t.Fatalf("expected role owner, got %s", roleResp["role"])
		}

		// Outsider gets 404 or 403
		respOut, _ := env.req(t, "GET", "/api/v1/incidents/"+incidentID+"/role", t5Outsider, nil)
		if respOut.StatusCode != http.StatusNotFound && respOut.StatusCode != http.StatusForbidden {
			t.Fatalf("expected 404 or 403 for outsider role, got %d", respOut.StatusCode)
		}

		// Add user5Outsider as analyst via API
		addBody := map[string]string{
			"user_id": user5Outsider,
			"role":    "analyst",
		}
		respAdd, bodyAdd := env.req(t, "POST", "/api/v1/incidents/"+incidentID+"/members", t1Owner, addBody)
		if respAdd.StatusCode != http.StatusCreated {
			t.Fatalf("expected 201 adding member, got %d: %s", respAdd.StatusCode, string(bodyAdd))
		}

		// Outsider cannot add member
		respAddDenied, _ := env.req(t, "POST", "/api/v1/incidents/"+incidentID+"/members", t5Outsider, addBody)
		if respAddDenied.StatusCode != http.StatusForbidden && respAddDenied.StatusCode != http.StatusNotFound {
			t.Fatalf("expected 403/404 for outsider adding member, got %d", respAddDenied.StatusCode)
		}
	})

	// 15. List audit events
	t.Run("15. List audit events", func(t *testing.T) {
		resp, body := env.req(t, "GET", "/api/v1/incidents/"+incidentID+"/audit", t1Owner, nil)
		if resp.StatusCode != http.StatusOK {
			t.Fatalf("expected 200 listing audit events, got %d: %s", resp.StatusCode, string(body))
		}
		var events []*store.AuditEvent
		if err := json.Unmarshal(body, &events); err != nil {
			t.Fatalf("failed to decode audit events: %v", err)
		}
		if len(events) == 0 {
			t.Fatalf("expected audit events for incident, got 0")
		}
	})

	// 16. Persistence across application process restart
	t.Run("16. Persistence across application process restart", func(t *testing.T) {
		// Close existing HTTP server and pool
		env.apiServer.Close()
		env.pool.Close()

		// Reopen a fresh pool and server pointing to the exact same database
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		newPool, err := pgxpool.New(ctx, env.dbURL)
		if err != nil {
			t.Fatalf("reconnecting to pool failed: %v", err)
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

		// Reassign in env for helper
		env.apiServer = newAPIServer
		env.pool = newPool

		// Verify incident still exists
		resp, body := env.req(t, "GET", "/api/v1/incidents/"+incidentID, t1Owner, nil)
		if resp.StatusCode != http.StatusOK {
			t.Fatalf("expected 200 after restart, got %d: %s", resp.StatusCode, string(body))
		}
		var inc store.Incident
		_ = json.Unmarshal(body, &inc)
		if inc.ID != incidentID {
			t.Fatalf("incident ID mismatch after restart: %s", inc.ID)
		}

		// Verify evidence review state is STILL "accepted"
		respEv, bodyEv := env.req(t, "GET", "/api/v1/incidents/"+incidentID+"/evidence/"+evidenceID, t1Owner, nil)
		if respEv.StatusCode != http.StatusOK {
			t.Fatalf("expected 200 for evidence after restart, got %d", respEv.StatusCode)
		}
		var ev store.Evidence
		_ = json.Unmarshal(bodyEv, &ev)
		if ev.ReviewState != "accepted" {
			t.Fatalf("expected review_state 'accepted' to survive restart, got %s", ev.ReviewState)
		}

		// Verify decision record still exists
		var dec store.Decision
		err = newPool.QueryRow(ctx, `SELECT id, decision, reviewer_id FROM public.decisions WHERE id = $1`, decisionID).Scan(&dec.ID, &dec.Decision, &dec.ReviewerID)
		if err != nil {
			t.Fatalf("failed to query decision after restart: %v", err)
		}
		if dec.Decision != "accept" || dec.ReviewerID != user3Reviewer {
			t.Fatalf("decision mismatch after restart: %+v", dec)
		}
	})
}
