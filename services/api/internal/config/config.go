package config

import (
	"errors"
	"fmt"
	"os"
	"time"
)

type Config struct {
	Env         string
	HTTPAddr    string
	LogLevel    string
	SupabaseURL string
	JWKSURL     string
	JWTIssuer   string
	JWTAudience string
	DatabaseURL string
	JWTLeeway   time.Duration
	HTTPTimeout time.Duration
}

func Load() (Config, error) {
	httpAddr := envOr("RIVET_HTTP_ADDR", "")
	if httpAddr == "" {
		if p := os.Getenv("PORT"); p != "" {
			httpAddr = ":" + p
		} else {
			httpAddr = ":8080"
		}
	}
	cfg := Config{
		Env:         envOr("RIVET_ENV", "development"),
		HTTPAddr:    httpAddr,
		LogLevel:    envOr("RIVET_LOG_LEVEL", "info"),
		SupabaseURL: os.Getenv("SUPABASE_URL"),
		JWKSURL:     os.Getenv("SUPABASE_JWKS_URL"),
		JWTIssuer:   os.Getenv("SUPABASE_JWT_ISSUER"),
		JWTAudience: os.Getenv("SUPABASE_JWT_AUD"),
		DatabaseURL: os.Getenv("DATABASE_URL"),
		JWTLeeway:   30 * time.Second,
		HTTPTimeout: 15 * time.Second,
	}
	if cfg.JWKSURL == "" && cfg.SupabaseURL != "" {
		cfg.JWKSURL = cfg.SupabaseURL + "/auth/v1/.well-known/jwks.json"
	}
	if cfg.JWTIssuer == "" && cfg.SupabaseURL != "" {
		cfg.JWTIssuer = cfg.SupabaseURL + "/auth/v1"
	}
	if err := cfg.Validate(); err != nil {
		return Config{}, err
	}
	return cfg, nil
}

func (c Config) Validate() error {
	if c.SupabaseURL == "" {
		return errors.New("SUPABASE_URL is required")
	}
	if c.JWKSURL == "" {
		return errors.New("SUPABASE_JWKS_URL is required")
	}
	if c.JWTIssuer == "" {
		return errors.New("SUPABASE_JWT_ISSUER is required")
	}
	if c.JWTAudience == "" {
		return errors.New("SUPABASE_JWT_AUD is required")
	}
	return nil
}

func envOr(k, d string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return d
}

var _ = fmt.Sprintf
