package auth

import (
	"context"
	"crypto/rsa"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"math/big"
	"net/http"
	"sync"
	"time"
)

type jwk struct {
	Kty string `json:"kty"`
	Kid string `json:"kid"`
	Use string `json:"use"`
	Alg string `json:"alg"`
	N   string `json:"n"`
	E   string `json:"e"`
}

type jwksDoc struct {
	Keys []jwk `json:"keys"`
}

type jwksClient struct {
	url     string
	client  *http.Client
	mu      sync.RWMutex
	keys    map[string]*rsaPublicKey
	fetched time.Time
	ttl     time.Duration
}

type rsaPublicKey = rsa.PublicKey

func newJWKSClient(url string, timeout time.Duration) *jwksClient {
	return &jwksClient{url: url, client: &http.Client{Timeout: timeout}, keys: map[string]*rsaPublicKey{}, ttl: 5 * time.Minute}
}

func (c *jwksClient) GetKey(ctx context.Context, kid string) (*rsaPublicKey, error) {
	c.mu.RLock()
	if k, ok := c.keys[kid]; ok && time.Since(c.fetched) < c.ttl {
		c.mu.RUnlock()
		return k, nil
	}
	c.mu.RUnlock()
	if err := c.refresh(ctx); err != nil {
		return nil, err
	}
	c.mu.RLock()
	defer c.mu.RUnlock()
	if k, ok := c.keys[kid]; ok {
		return k, nil
	}
	return nil, fmt.Errorf("unknown key id %s", kid)
}

func (c *jwksClient) refresh(ctx context.Context) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.url, nil)
	if err != nil {
		return err
	}
	resp, err := c.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("jwks status %d", resp.StatusCode)
	}
	var doc jwksDoc
	if err := json.NewDecoder(resp.Body).Decode(&doc); err != nil {
		return err
	}
	keys := map[string]*rsaPublicKey{}
	for _, k := range doc.Keys {
		if k.Kty != "RSA" {
			continue
		}
		nBytes, err := base64.RawURLEncoding.DecodeString(k.N)
		if err != nil {
			continue
		}
		eBytes, err := base64.RawURLEncoding.DecodeString(k.E)
		if err != nil {
			continue
		}
		n := new(big.Int).SetBytes(nBytes)
		e := 0
		for _, b := range eBytes {
			e = e*256 + int(b)
		}
		keys[k.Kid] = &rsa.PublicKey{N: n, E: e}
	}
	c.mu.Lock()
	defer c.mu.Unlock()
	c.keys = keys
	c.fetched = time.Now()
	return nil
}
