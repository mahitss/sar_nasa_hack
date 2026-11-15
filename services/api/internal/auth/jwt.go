package auth

import (
	"context"
	"crypto/rsa"
	"fmt"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

type Identity struct {
	Subject  string
	Email    string
	Issuer   string
	Audience []string
}

type Verifier struct {
	jwks     *jwksClient
	issuer   string
	audience string
	leeway   time.Duration
}

func NewVerifier(jwksURL, issuer, audience string, timeout, leeway time.Duration) *Verifier {
	return &Verifier{
		jwks:     newJWKSClient(jwksURL, timeout),
		issuer:   issuer,
		audience: audience,
		leeway:   leeway,
	}
}

func (v *Verifier) Verify(ctx context.Context, tokenString string) (Identity, error) {
	parser := jwt.NewParser(
		jwt.WithValidMethods([]string{"RS256"}),
		jwt.WithIssuer(v.issuer),
		jwt.WithAudience(v.audience),
		jwt.WithLeeway(v.leeway),
	)
	token, err := parser.Parse(tokenString, func(t *jwt.Token) (interface{}, error) {
		kid, _ := t.Header["kid"].(string)
		if kid == "" {
			return nil, fmt.Errorf("missing kid")
		}
		key, err := v.jwks.GetKey(ctx, kid)
		if err != nil {
			return nil, err
		}
		return (*rsa.PublicKey)(key), nil
	})
	if err != nil {
		return Identity{}, err
	}
	if !token.Valid {
		return Identity{}, fmt.Errorf("invalid token")
	}
	claims, ok := token.Claims.(jwt.MapClaims)
	if !ok {
		return Identity{}, fmt.Errorf("invalid claims")
	}
	sub, _ := claims["sub"].(string)
	if sub == "" {
		return Identity{}, fmt.Errorf("missing subject")
	}
	email, _ := claims["email"].(string)
	aud := []string{}
	switch a := claims["aud"].(type) {
	case string:
		aud = []string{a}
	case []interface{}:
		for _, x := range a {
			if s, ok := x.(string); ok {
				aud = append(aud, s)
			}
		}
	}
	return Identity{Subject: sub, Email: email, Issuer: v.issuer, Audience: aud}, nil
}
