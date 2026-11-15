package workerauth_test

import (
	"bytes"
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/mahitss/rivet-api/internal/workerauth"
)

func generateKeyPair(t *testing.T) (ed25519.PublicKey, ed25519.PrivateKey) {
	pub, priv, err := ed25519.GenerateKey(nil)
	if err != nil {
		t.Fatalf("failed to generate ed25519 key: %v", err)
	}
	return pub, priv
}

func signRequest(method, path, workerID, keyID string, ts int64, nonce string, body []byte, priv ed25519.PrivateKey) string {
	h := sha256.Sum256(body)
	bodySHA := hex.EncodeToString(h[:])
	canonical := workerauth.CanonicalString(method, path, workerID, keyID, fmt.Sprintf("%d", ts), nonce, bodySHA)
	sig := ed25519.Sign(priv, []byte(canonical))
	return hex.EncodeToString(sig)
}

func TestWorkerAuth_Scenarios(t *testing.T) {
	pub, priv := generateKeyPair(t)
	workerID := "worker-alpha"
	keyID := "key-2026"

	registry := workerauth.NewKeyRegistry()
	registry.RegisterKey(workerID, keyID, pub)
	nonces := workerauth.NewNonceCache()
	skew := 2 * time.Minute

	handler := workerauth.Middleware(registry, nonces, skew)(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		id, ok := workerauth.IdentityFromContext(r.Context())
		if !ok || id.WorkerID != workerID {
			http.Error(w, "missing or bad identity", http.StatusInternalServerError)
			return
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("ok"))
	}))

	t.Run("1. Valid worker signature passes", func(t *testing.T) {
		body := []byte(`{"task":"inspect"}`)
		ts := time.Now().Unix()
		nonce := "nonce-valid-1"
		sig := signRequest("POST", "/test", workerID, keyID, ts, nonce, body, priv)

		req := httptest.NewRequest("POST", "/test", bytes.NewReader(body))
		req.Header.Set(workerauth.HeaderWorkerID, workerID)
		req.Header.Set(workerauth.HeaderKeyID, keyID)
		req.Header.Set(workerauth.HeaderTimestamp, fmt.Sprintf("%d", ts))
		req.Header.Set(workerauth.HeaderNonce, nonce)
		req.Header.Set(workerauth.HeaderSignature, sig)

		rec := httptest.NewRecorder()
		handler.ServeHTTP(rec, req)

		if rec.Code != http.StatusOK {
			t.Fatalf("expected 200, got %d: %s", rec.Code, rec.Body.String())
		}
	})

	t.Run("2. Missing headers rejected", func(t *testing.T) {
		req := httptest.NewRequest("POST", "/test", bytes.NewReader([]byte("{}")))
		rec := httptest.NewRecorder()
		handler.ServeHTTP(rec, req)

		if rec.Code != http.StatusUnauthorized {
			t.Fatalf("expected 401, got %d", rec.Code)
		}
	})

	t.Run("3. Unknown worker rejected", func(t *testing.T) {
		body := []byte("{}")
		ts := time.Now().Unix()
		nonce := "nonce-unknown-worker"
		sig := signRequest("POST", "/test", "unknown-worker", keyID, ts, nonce, body, priv)

		req := httptest.NewRequest("POST", "/test", bytes.NewReader(body))
		req.Header.Set(workerauth.HeaderWorkerID, "unknown-worker")
		req.Header.Set(workerauth.HeaderKeyID, keyID)
		req.Header.Set(workerauth.HeaderTimestamp, fmt.Sprintf("%d", ts))
		req.Header.Set(workerauth.HeaderNonce, nonce)
		req.Header.Set(workerauth.HeaderSignature, sig)

		rec := httptest.NewRecorder()
		handler.ServeHTTP(rec, req)

		if rec.Code != http.StatusUnauthorized {
			t.Fatalf("expected 401, got %d", rec.Code)
		}
	})

	t.Run("4. Unknown key ID rejected", func(t *testing.T) {
		body := []byte("{}")
		ts := time.Now().Unix()
		nonce := "nonce-unknown-key"
		sig := signRequest("POST", "/test", workerID, "key-bad", ts, nonce, body, priv)

		req := httptest.NewRequest("POST", "/test", bytes.NewReader(body))
		req.Header.Set(workerauth.HeaderWorkerID, workerID)
		req.Header.Set(workerauth.HeaderKeyID, "key-bad")
		req.Header.Set(workerauth.HeaderTimestamp, fmt.Sprintf("%d", ts))
		req.Header.Set(workerauth.HeaderNonce, nonce)
		req.Header.Set(workerauth.HeaderSignature, sig)

		rec := httptest.NewRecorder()
		handler.ServeHTTP(rec, req)

		if rec.Code != http.StatusUnauthorized {
			t.Fatalf("expected 401, got %d", rec.Code)
		}
	})

	t.Run("5. Expired timestamp rejected", func(t *testing.T) {
		body := []byte("{}")
		ts := time.Now().Add(-10 * time.Minute).Unix()
		nonce := "nonce-expired"
		sig := signRequest("POST", "/test", workerID, keyID, ts, nonce, body, priv)

		req := httptest.NewRequest("POST", "/test", bytes.NewReader(body))
		req.Header.Set(workerauth.HeaderWorkerID, workerID)
		req.Header.Set(workerauth.HeaderKeyID, keyID)
		req.Header.Set(workerauth.HeaderTimestamp, fmt.Sprintf("%d", ts))
		req.Header.Set(workerauth.HeaderNonce, nonce)
		req.Header.Set(workerauth.HeaderSignature, sig)

		rec := httptest.NewRecorder()
		handler.ServeHTTP(rec, req)

		if rec.Code != http.StatusUnauthorized {
			t.Fatalf("expected 401, got %d", rec.Code)
		}
	})

	t.Run("6. Future timestamp outside window rejected", func(t *testing.T) {
		body := []byte("{}")
		ts := time.Now().Add(10 * time.Minute).Unix()
		nonce := "nonce-future"
		sig := signRequest("POST", "/test", workerID, keyID, ts, nonce, body, priv)

		req := httptest.NewRequest("POST", "/test", bytes.NewReader(body))
		req.Header.Set(workerauth.HeaderWorkerID, workerID)
		req.Header.Set(workerauth.HeaderKeyID, keyID)
		req.Header.Set(workerauth.HeaderTimestamp, fmt.Sprintf("%d", ts))
		req.Header.Set(workerauth.HeaderNonce, nonce)
		req.Header.Set(workerauth.HeaderSignature, sig)

		rec := httptest.NewRecorder()
		handler.ServeHTTP(rec, req)

		if rec.Code != http.StatusUnauthorized {
			t.Fatalf("expected 401, got %d", rec.Code)
		}
	})

	t.Run("7. Replayed nonce rejected", func(t *testing.T) {
		body := []byte("{}")
		ts := time.Now().Unix()
		nonce := "nonce-replay-target"
		sig := signRequest("POST", "/test", workerID, keyID, ts, nonce, body, priv)

		buildReq := func() *http.Request {
			r := httptest.NewRequest("POST", "/test", bytes.NewReader(body))
			r.Header.Set(workerauth.HeaderWorkerID, workerID)
			r.Header.Set(workerauth.HeaderKeyID, keyID)
			r.Header.Set(workerauth.HeaderTimestamp, fmt.Sprintf("%d", ts))
			r.Header.Set(workerauth.HeaderNonce, nonce)
			r.Header.Set(workerauth.HeaderSignature, sig)
			return r
		}

		rec1 := httptest.NewRecorder()
		handler.ServeHTTP(rec1, buildReq())
		if rec1.Code != http.StatusOK {
			t.Fatalf("expected first request 200, got %d", rec1.Code)
		}

		rec2 := httptest.NewRecorder()
		handler.ServeHTTP(rec2, buildReq())
		if rec2.Code != http.StatusUnauthorized {
			t.Fatalf("expected replay rejection 401, got %d", rec2.Code)
		}
	})

	t.Run("8. Tampered body / invalid hash rejected", func(t *testing.T) {
		origBody := []byte(`{"param":1}`)
		tamperedBody := []byte(`{"param":2}`)
		ts := time.Now().Unix()
		nonce := "nonce-tamper"
		// Sign origBody but send tamperedBody
		sig := signRequest("POST", "/test", workerID, keyID, ts, nonce, origBody, priv)

		req := httptest.NewRequest("POST", "/test", bytes.NewReader(tamperedBody))
		req.Header.Set(workerauth.HeaderWorkerID, workerID)
		req.Header.Set(workerauth.HeaderKeyID, keyID)
		req.Header.Set(workerauth.HeaderTimestamp, fmt.Sprintf("%d", ts))
		req.Header.Set(workerauth.HeaderNonce, nonce)
		req.Header.Set(workerauth.HeaderSignature, sig)

		rec := httptest.NewRecorder()
		handler.ServeHTTP(rec, req)

		if rec.Code != http.StatusUnauthorized {
			t.Fatalf("expected 401 on tampered body, got %d", rec.Code)
		}
	})

	t.Run("9. Key rotation works", func(t *testing.T) {
		pub2, priv2 := generateKeyPair(t)
		keyID2 := "key-2027"
		registry.RegisterKey(workerID, keyID2, pub2)

		body := []byte(`{"action":"rotated"}`)
		ts := time.Now().Unix()
		nonce := "nonce-rotation"
		sig := signRequest("POST", "/test", workerID, keyID2, ts, nonce, body, priv2)

		req := httptest.NewRequest("POST", "/test", bytes.NewReader(body))
		req.Header.Set(workerauth.HeaderWorkerID, workerID)
		req.Header.Set(workerauth.HeaderKeyID, keyID2)
		req.Header.Set(workerauth.HeaderTimestamp, fmt.Sprintf("%d", ts))
		req.Header.Set(workerauth.HeaderNonce, nonce)
		req.Header.Set(workerauth.HeaderSignature, sig)

		rec := httptest.NewRecorder()
		handler.ServeHTTP(rec, req)

		if rec.Code != http.StatusOK {
			t.Fatalf("expected 200 with rotated key, got %d", rec.Code)
		}
	})
}
