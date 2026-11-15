package server

import (
	"context"
	"net/http"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"

	"github.com/mahitss/rivet-api/internal/auth"
	"github.com/mahitss/rivet-api/internal/config"
	"github.com/mahitss/rivet-api/internal/handler"
	mwm "github.com/mahitss/rivet-api/internal/middleware"
)

func New(cfg config.Config, h *handler.Handler, verifier *auth.Verifier) *http.Server {
	r := chi.NewRouter()
	r.Use(mwm.Recover)
	r.Use(mwm.RequestID)
	r.Use(middleware.Logger)
	r.Get("/healthz", h.Healthz)
	r.Get("/readyz", h.Readyz)

	r.Route("/api/v1", func(r chi.Router) {
		r.Use(mwm.Auth(verifier))
		r.Get("/whoami", h.Whoami)
		r.Route("/incidents", func(r chi.Router) {
			r.Get("/", h.ListIncidents)
			r.Post("/", h.CreateIncident)
			r.Route("/{incidentID}", func(r chi.Router) {
				r.Get("/", h.GetIncident)
				r.Get("/acquisitions", h.ListAcquisitions)
				r.Post("/acquisitions", h.CreateAcquisition)
				r.Get("/evidence", h.ListEvidence)
				r.Post("/evidence", h.CreateEvidence)
				r.Route("/evidence/{evidenceID}", func(r chi.Router) {
					r.Get("/", h.GetEvidence)
					r.Patch("/", h.PatchEvidence)
					r.Post("/decisions", h.CreateDecision)
				})
				r.Get("/jobs", h.ListJobs)
				r.Post("/jobs", h.CreateJob)
				r.Route("/jobs/{jobID}", func(r chi.Router) {
					r.Get("/", h.GetJob)
				})
				r.Get("/reports", h.ListReports)
				r.Post("/reports", h.CreateReport)
				r.Route("/reports/{reportID}", func(r chi.Router) {
					r.Get("/", h.GetReport)
				})
			})
		})
	})

	return &http.Server{Addr: cfg.HTTPAddr, Handler: r}
}

var _ = context.Background
