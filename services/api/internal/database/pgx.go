package database

import (
	"context"
	"fmt"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/mahitss/rivet-api/internal/transaction"
)

type txContextKey struct{}

func WithTx(ctx context.Context, tx pgx.Tx) context.Context {
	return context.WithValue(ctx, txContextKey{}, tx)
}

func TxFromContext(ctx context.Context) (pgx.Tx, bool) {
	tx, ok := ctx.Value(txContextKey{}).(pgx.Tx)
	return tx, ok
}

type Pool struct {
	*pgxpool.Pool
}

func NewPool(ctx context.Context, url string) (*Pool, error) {
	p, err := pgxpool.New(ctx, url)
	if err != nil {
		return nil, err
	}
	if err := p.Ping(ctx); err != nil {
		p.Close()
		return nil, err
	}
	return &Pool{Pool: p}, nil
}

type PostgresTxManager struct {
	pool *pgxpool.Pool
}

var _ transaction.TxManager = (*PostgresTxManager)(nil)

func NewTxManager(pool *pgxpool.Pool) *PostgresTxManager {
	return &PostgresTxManager{pool: pool}
}

func (m *PostgresTxManager) WithinTransaction(ctx context.Context, subject string, fn func(ctx context.Context) error) error {
	tx, err := m.pool.Begin(ctx)
	if err != nil {
		return err
	}
	defer func() {
		_ = tx.Rollback(ctx)
	}()

	if _, err := tx.Exec(ctx, "select set_config('request.jwt.claim.sub', $1, true)", subject); err != nil {
		return err
	}
	if _, err := tx.Exec(ctx, "select set_config('request.jwt.claim.role', 'authenticated', true)"); err != nil {
		return err
	}
	claimsJSON := fmt.Sprintf(`{"sub":"%s","role":"authenticated"}`, subject)
	if _, err := tx.Exec(ctx, "select set_config('request.jwt.claims', $1, true)", claimsJSON); err != nil {
		return err
	}
	if _, err := tx.Exec(ctx, "set local role authenticated"); err != nil {
		return err
	}

	txCtx := WithTx(ctx, tx)
	if err := fn(txCtx); err != nil {
		return err
	}

	return tx.Commit(ctx)
}

func (m *PostgresTxManager) WithinWorkerTransaction(ctx context.Context, workerID string, fn func(ctx context.Context) error) error {
	tx, err := m.pool.Begin(ctx)
	if err != nil {
		return err
	}
	defer func() {
		_ = tx.Rollback(ctx)
	}()

	if _, err := tx.Exec(ctx, "select set_config('rivet.worker_id', $1, true)", workerID); err != nil {
		return err
	}

	txCtx := WithTx(ctx, tx)
	if err := fn(txCtx); err != nil {
		return err
	}

	return tx.Commit(ctx)
}
