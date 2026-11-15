package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/mahitss/rivet-api/internal/auth"
	"github.com/mahitss/rivet-api/internal/config"
	"github.com/mahitss/rivet-api/internal/handler"
	"github.com/mahitss/rivet-api/internal/server"
	"github.com/mahitss/rivet-api/internal/store"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		log.Printf("config: %v", err)
		// allow healthz-only mode
		cfg.HTTPAddr = envOr("RIVET_HTTP_ADDR", ":8080")
	}

	st := store.New()
	h := handler.New(st)

	var verifier *auth.Verifier
	if cfg.SupabaseURL != "" {
		verifier = auth.NewVerifier(cfg.JWKSURL, cfg.JWTIssuer, cfg.JWTAudience, cfg.HTTPTimeout, cfg.JWTLeeway)
	} else {
		// development: accept no auth (healthz only meaningful)
		verifier = auth.NewVerifier("", "", "", cfg.HTTPTimeout, cfg.JWTLeeway)
	}

	srv := server.New(cfg, h, verifier)

	go func() {
		log.Printf("listening on %s", cfg.HTTPAddr)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("listen: %v", err)
		}
	}()

	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	<-stop
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	_ = srv.Shutdown(ctx)
}

func envOr(k, d string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return d
}
