package auth

import (
	"context"
	"crypto/ecdsa"
	"crypto/elliptic"
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

func TestVerifyValidES256(t *testing.T) {
	priv, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	kid := "es256-k1"
	x := base64.RawURLEncoding.EncodeToString(priv.PublicKey.X.Bytes())
	y := base64.RawURLEncoding.EncodeToString(priv.PublicKey.Y.Bytes())
	doc := map[string]interface{}{
		"keys": []map[string]string{{
			"kty": "EC", "kid": kid, "use": "sig", "alg": "ES256", "crv": "P-256",
			"x": x, "y": y,
		}},
	}
	b, _ := json.Marshal(doc)
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write(b)
	}))
	defer srv.Close()

	issuer := "https://waueelcdmvthqlaoghkg.supabase.co/auth/v1"
	aud := "authenticated"
	v := NewVerifier(srv.URL, issuer, aud, 5*time.Second, 30*time.Second)

	claims := jwt.MapClaims{
		"sub":   "user-es256-456",
		"iss":   issuer,
		"aud":   aud,
		"exp":   time.Now().Add(time.Hour).Unix(),
		"email": "es256@test.local",
	}
	tok := jwt.NewWithClaims(jwt.SigningMethodES256, claims)
	tok.Header["kid"] = kid
	signed, err := tok.SignedString(priv)
	if err != nil {
		t.Fatal(err)
	}

	id, err := v.Verify(context.Background(), signed)
	if err != nil {
		t.Fatalf("verify ES256 failed: %v", err)
	}
	if id.Subject != "user-es256-456" {
		t.Fatalf("subject mismatch: %s", id.Subject)
	}
	if id.Email != "es256@test.local" {
		t.Fatalf("email mismatch: %s", id.Email)
	}
}

var _ = fmt.Sprintf
