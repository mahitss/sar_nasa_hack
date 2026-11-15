package main

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/mahitss/rivet-api/internal/auth"
	"github.com/mahitss/rivet-api/internal/config"
	"github.com/mahitss/rivet-api/internal/database"
	"github.com/mahitss/rivet-api/internal/handler"
	"github.com/mahitss/rivet-api/internal/server"
	"github.com/mahitss/rivet-api/internal/store"
	"github.com/mahitss/rivet-api/internal/transaction"
	"github.com/mahitss/rivet-api/internal/workerauth"
	"github.com/mahitss/rivet-api/internal/workerhandler"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		log.Printf("config: %v", err)
		httpAddr := envOr("RIVET_HTTP_ADDR", "")
		if httpAddr == "" {
			if p := os.Getenv("PORT"); p != "" {
				httpAddr = ":" + p
			} else {
				httpAddr = ":8080"
			}
		}
		cfg.HTTPAddr = httpAddr
	}

	var repo store.Repository
	var txMgr transaction.TxManager

	if cfg.DatabaseURL != "" {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		pool, err := database.NewPool(ctx, cfg.DatabaseURL)
		if err != nil {
			log.Fatalf("database connection failed: %v", err)
		}
		defer pool.Close()
		log.Printf("connected to postgresql successfully")
		repo = database.NewPostgresRepository()
		txMgr = database.NewTxManager(pool.Pool)
	} else {
		if cfg.Env == "production" {
			log.Fatalf("DATABASE_URL is required in production: no in-memory fallback allowed")
		}
		log.Printf("warning: using in-memory store double (non-production test mode)")
		repo = store.New()
		txMgr = transaction.NewMemoryTxManager()
	}

	h := handler.New(repo, txMgr)
	workerH := workerhandler.New(repo, txMgr)

	workerRegistry := workerauth.NewKeyRegistry()
	workerRegistry.RegisterDevKey()
	if workerKeysJSON := os.Getenv("RIVET_WORKER_KEYS"); workerKeysJSON != "" {
		var keys []struct {
			WorkerID  string `json:"worker_id"`
			KeyID     string `json:"key_id"`
			PublicKey string `json:"public_key"`
		}
		if err := json.Unmarshal([]byte(workerKeysJSON), &keys); err == nil {
			for _, k := range keys {
				_ = workerRegistry.RegisterHexKey(k.WorkerID, k.KeyID, k.PublicKey)
			}
		}
	}

	var verifier *auth.Verifier
	if cfg.SupabaseURL != "" {
		verifier = auth.NewVerifier(cfg.JWKSURL, cfg.JWTIssuer, cfg.JWTAudience, cfg.HTTPTimeout, cfg.JWTLeeway)
	} else {
		verifier = auth.NewVerifier("", "", "", cfg.HTTPTimeout, cfg.JWTLeeway)
	}

	srv := server.New(cfg, h, verifier, workerH, workerRegistry)

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
