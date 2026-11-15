package workerauth

import (
	"bytes"
	"context"
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"sync"
	"time"
)

type contextKey string

const (
	WorkerIdentityContextKey contextKey = "worker_identity"

	HeaderWorkerID  = "X-Worker-ID"
	HeaderKeyID     = "X-Key-ID"
	HeaderTimestamp = "X-Timestamp"
	HeaderNonce     = "X-Nonce"
	HeaderSignature = "X-Signature"

	DefaultClockSkew = 5 * time.Minute
	MaxBodySize      = 2 * 1024 * 1024 // 2MB max worker request body

	DefaultDevWorkerID = "worker-local-1"
	DefaultDevKeyID    = "key-local-1"
	DefaultDevPubKey   = "544f8f03edfc09fab6ab5d7b42351a0eef237ebfee26bc8e87d60d8899a45113"
	DefaultDevPrivSeed = "272d500ca44a5cd4ad8fa4a4fa09ce35f1e416733ad6f3beaed708887d46cd2d"
)

type WorkerIdentity struct {
	WorkerID string `json:"worker_id"`
	KeyID    string `json:"key_id"`
}

type KeyRegistry struct {
	mu   sync.RWMutex
	keys map[string]ed25519.PublicKey
}

func NewKeyRegistry() *KeyRegistry {
	return &KeyRegistry{
		keys: make(map[string]ed25519.PublicKey),
	}
}

func (r *KeyRegistry) RegisterKey(workerID, keyID string, pubKey ed25519.PublicKey) {
	r.mu.Lock()
	defer r.mu.Unlock()
	key := fmt.Sprintf("%s:%s", workerID, keyID)
	r.keys[key] = pubKey
}

func (r *KeyRegistry) RegisterHexKey(workerID, keyID, hexKey string) error {
	raw, err := hex.DecodeString(hexKey)
	if err != nil {
		return fmt.Errorf("invalid hex public key: %w", err)
	}
	if len(raw) != ed25519.PublicKeySize {
		return fmt.Errorf("invalid ed25519 public key length %d, expected %d", len(raw), ed25519.PublicKeySize)
	}
	r.RegisterKey(workerID, keyID, ed25519.PublicKey(raw))
	return nil
}

func (r *KeyRegistry) RegisterDevKey() {
	_ = r.RegisterHexKey(DefaultDevWorkerID, DefaultDevKeyID, DefaultDevPubKey)
}

func (r *KeyRegistry) LookupKey(workerID, keyID string) (ed25519.PublicKey, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	key := fmt.Sprintf("%s:%s", workerID, keyID)
	pub, ok := r.keys[key]
	return pub, ok
}

type NonceCache struct {
	mu     sync.Mutex
	nonces map[string]time.Time
}

func NewNonceCache() *NonceCache {
	return &NonceCache{
		nonces: make(map[string]time.Time),
	}
}

// CheckAndRecord returns true if the nonce is new and successfully recorded,
// or false if the nonce was already used (replay attack).
func (c *NonceCache) CheckAndRecord(nonce string, expiresAt time.Time) bool {
	c.mu.Lock()
	defer c.mu.Unlock()

	now := time.Now()
	// Evict expired nonces
	for k, exp := range c.nonces {
		if exp.Before(now) {
			delete(c.nonces, k)
		}
	}

	if _, exists := c.nonces[nonce]; exists {
		return false
	}
	c.nonces[nonce] = expiresAt
	return true
}

func CanonicalString(method, path, workerID, keyID, timestamp, nonce, bodySHA256 string) string {
	return fmt.Sprintf("%s\n%s\n%s\n%s\n%s\n%s\n%s",
		method, path, workerID, keyID, timestamp, nonce, bodySHA256,
	)
}

func Middleware(registry *KeyRegistry, nonceCache *NonceCache, maxClockSkew time.Duration) func(http.Handler) http.Handler {
	if maxClockSkew <= 0 {
		maxClockSkew = DefaultClockSkew
	}

	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			workerID := r.Header.Get(HeaderWorkerID)
			keyID := r.Header.Get(HeaderKeyID)
			timestampStr := r.Header.Get(HeaderTimestamp)
			nonce := r.Header.Get(HeaderNonce)
			sigHex := r.Header.Get(HeaderSignature)

			if workerID == "" || keyID == "" || timestampStr == "" || nonce == "" || sigHex == "" {
				reject(w, http.StatusUnauthorized, "missing required worker auth headers")
				return
			}

			pubKey, ok := registry.LookupKey(workerID, keyID)
			if !ok {
				reject(w, http.StatusUnauthorized, "unrecognized worker or key identifier")
				return
			}

			ts, err := strconv.ParseInt(timestampStr, 10, 64)
			if err != nil {
				reject(w, http.StatusUnauthorized, "invalid timestamp format")
				return
			}

			reqTime := time.Unix(ts, 0)
			now := time.Now()
			diff := now.Sub(reqTime)
			if diff < -maxClockSkew || diff > maxClockSkew {
				reject(w, http.StatusUnauthorized, "request timestamp outside allowed clock skew window")
				return
			}

			// Read body for sha256 calculation
			bodyBytes, err := io.ReadAll(http.MaxBytesReader(w, r.Body, MaxBodySize))
			if err != nil {
				reject(w, http.StatusBadRequest, "request body too large or unreadable")
				return
			}
			r.Body = io.NopCloser(bytes.NewReader(bodyBytes))

			bodyHash := sha256.Sum256(bodyBytes)
			bodySHA256 := hex.EncodeToString(bodyHash[:])

			// Replay prevention via nonce cache
			nonceExpiry := reqTime.Add(maxClockSkew)
			if !nonceCache.CheckAndRecord(nonce, nonceExpiry) {
				reject(w, http.StatusUnauthorized, "replayed request nonce detected")
				return
			}

			// Validate Ed25519 signature
			canonical := CanonicalString(r.Method, r.URL.Path, workerID, keyID, timestampStr, nonce, bodySHA256)
			sigBytes, err := hex.DecodeString(sigHex)
			if err != nil || len(sigBytes) != ed25519.SignatureSize {
				reject(w, http.StatusUnauthorized, "invalid signature format")
				return
			}

			if !ed25519.Verify(pubKey, []byte(canonical), sigBytes) {
				reject(w, http.StatusUnauthorized, "signature verification failed")
				return
			}

			ctx := context.WithValue(r.Context(), WorkerIdentityContextKey, WorkerIdentity{
				WorkerID: workerID,
				KeyID:    keyID,
			})
			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

func IdentityFromContext(ctx context.Context) (WorkerIdentity, bool) {
	v := ctx.Value(WorkerIdentityContextKey)
	if v == nil {
		return WorkerIdentity{}, false
	}
	id, ok := v.(WorkerIdentity)
	return id, ok
}

func reject(w http.ResponseWriter, status int, msg string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]string{"error": msg})
}
