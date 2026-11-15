package database

import (
	"context"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/mahitss/rivet-api/internal/transaction"
)

type Pool struct{ *pgxpool.Pool }

func NewPool(ctx context.Context, url string) (*Pool, error) {
	p, err := pgxpool.New(ctx, url)
	if err != nil {
		return nil, err
	}
	return &Pool{Pool: p}, nil
}

type pgxTx struct{ pgx.Tx }

func (p *Pool) BeginTx(ctx context.Context) (transaction.Tx, error) {
	tx, err := p.Pool.Begin(ctx)
	if err != nil {
		return nil, err
	}
	return &pgxTx{Tx: tx}, nil
}

func (t *pgxTx) SetClaims(ctx context.Context, claims map[string]string) error {
	for k, v := range claims {
		if _, err := t.Exec(ctx, "select set_config($1, $2, true)", "request.jwt.claim."+k, v); err != nil {
			return err
		}
	}
	// also set combined claims
	b := "{"
	first := true
	for k, v := range claims {
		if !first {
			b += ","
		}
		b += `"` + k + `":"` + v + `"`
		first = false
	}
	b += "}"
	_, err := t.Exec(ctx, "select set_config('request.jwt.claims', $1, true)", b)
	return err
}

func (t *pgxTx) SetRole(ctx context.Context, role string) error {
	_, err := t.Exec(ctx, "set local role "+role)
	return err
}

func (t *pgxTx) Commit(ctx context.Context) error   { return t.Tx.Commit(ctx) }
func (t *pgxTx) Rollback(ctx context.Context) error { return t.Tx.Rollback(ctx) }
