package middleware

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"net/http"

	"github.com/mahitss/rivet-api/internal/auth"
	"github.com/mahitss/rivet-api/internal/errors"
)

type ctxKey string

const identityKey ctxKey = "identity"

func RequestID(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		id := r.Header.Get("X-Request-ID")
		if id == "" {
			b := make([]byte, 8)
			_, _ = rand.Read(b)
			id = hex.EncodeToString(b)
		}
		w.Header().Set("X-Request-ID", id)
		next.ServeHTTP(w, r)
	})
}

func Recover(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if rec := recover(); rec != nil {
				writeErr(w, errors.New(500, "internal_error", "internal server error"))
			}
		}()
		next.ServeHTTP(w, r)
	})
}

func CORS(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Accept, Authorization, Content-Type, X-Request-ID, X-Worker-ID, X-Key-ID, X-Timestamp, X-Nonce, X-Signature")
		w.Header().Set("Access-Control-Expose-Headers", "Link, X-Request-ID")
		w.Header().Set("Access-Control-Max-Age", "300")

		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		next.ServeHTTP(w, r)
	})
}

func Auth(verifier *auth.Verifier) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			h := r.Header.Get("Authorization")
			if len(h) < 8 || h[:7] != "Bearer " {
				writeErr(w, errors.ErrUnauthorized)
				return
			}
			id, err := verifier.Verify(r.Context(), h[7:])
			if err != nil {
				writeErr(w, errors.ErrUnauthorized)
				return
			}
			ctx := context.WithValue(r.Context(), identityKey, id)
			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

func IdentityFromContext(ctx context.Context) (auth.Identity, bool) {
	v, ok := ctx.Value(identityKey).(auth.Identity)
	return v, ok
}

func writeErr(w http.ResponseWriter, e *errors.APIError) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(e.Status)
	_, _ = w.Write([]byte(`{"code":"` + e.Code + `","message":"` + e.Message + `"}`))
}
