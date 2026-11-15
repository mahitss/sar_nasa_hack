package auth

import (
	"context"
	"crypto/rand"
	"crypto/rsa"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

func makeJWKS(t *testing.T, priv *rsa.PrivateKey, kid string) *httptest.Server {
	pub := &priv.PublicKey
	n := base64.RawURLEncoding.EncodeToString(pub.N.Bytes())
	eBytes := []byte{byte(pub.E >> 16), byte(pub.E >> 8), byte(pub.E)}
	// trim leading zeros
	for len(eBytes) > 1 && eBytes[0] == 0 {
		eBytes = eBytes[1:]
	}
	e := base64.RawURLEncoding.EncodeToString(eBytes)
	doc := map[string]interface{}{
		"keys": []map[string]string{{
			"kty": "RSA", "kid": kid, "use": "sig", "alg": "RS256",
			"n": n, "e": e,
		}},
	}
	b, _ := json.Marshal(doc)
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write(b)
	}))
}

func signToken(priv *rsa.PrivateKey, kid, issuer, aud, sub string, exp time.Time) string {
	claims := jwt.MapClaims{
		"sub":   sub,
		"iss":   issuer,
		"aud":   aud,
		"exp":   exp.Unix(),
		"email": "u@test.local",
	}
	tok := jwt.NewWithClaims(jwt.SigningMethodRS256, claims)
	tok.Header["kid"] = kid
	s, _ := tok.SignedString(priv)
	return s
}

func TestVerifyValid(t *testing.T) {
	priv, _ := rsa.GenerateKey(rand.Reader, 2048)
	issuer := "https://example.supabase.co/auth/v1"
	aud := "authenticated"
	kid := "k1"
	srv := makeJWKS(t, priv, kid)
	defer srv.Close()
	v := NewVerifier(srv.URL, issuer, aud, 5*time.Second, 30*time.Second)
	tok := signToken(priv, kid, issuer, aud, "user-123", time.Now().Add(time.Hour))
	id, err := v.Verify(context.Background(), tok)
	if err != nil {
		t.Fatal(err)
	}
	if id.Subject != "user-123" {
		t.Fatalf("subject mismatch: %s", id.Subject)
	}
}

func TestVerifyExpired(t *testing.T) {
	priv, _ := rsa.GenerateKey(rand.Reader, 2048)
	issuer := "https://example.supabase.co/auth/v1"
	aud := "authenticated"
	kid := "k1"
	srv := makeJWKS(t, priv, kid)
	defer srv.Close()
	v := NewVerifier(srv.URL, issuer, aud, 5*time.Second, 30*time.Second)
	tok := signToken(priv, kid, issuer, aud, "user-123", time.Now().Add(-time.Hour))
	if _, err := v.Verify(context.Background(), tok); err == nil {
		t.Fatal("expected error for expired token")
	}
}

func TestVerifyBadAudience(t *testing.T) {
	priv, _ := rsa.GenerateKey(rand.Reader, 2048)
	issuer := "https://example.supabase.co/auth/v1"
	kid := "k1"
	srv := makeJWKS(t, priv, kid)
	defer srv.Close()
	v := NewVerifier(srv.URL, issuer, "authenticated", 5*time.Second, 30*time.Second)
	tok := signToken(priv, kid, issuer, "wrong-aud", "user-123", time.Now().Add(time.Hour))
	if _, err := v.Verify(context.Background(), tok); err == nil {
		t.Fatal("expected error for bad audience")
	}
}

var _ = fmt.Sprintf
