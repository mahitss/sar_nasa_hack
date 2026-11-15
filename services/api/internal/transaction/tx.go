package transaction

import (
	"context"
	"fmt"
)

type Identity struct {
	Subject string
}

type DB interface {
	BeginTx(ctx context.Context) (Tx, error)
}

type Tx interface {
	SetClaims(ctx context.Context, claims map[string]string) error
	SetRole(ctx context.Context, role string) error
	Commit(ctx context.Context) error
	Rollback(ctx context.Context) error
}

type Manager struct {
	DB DB
}

func (m *Manager) Run(ctx context.Context, ident Identity, fn func(ctx context.Context, tx Tx) error) error {
	tx, err := m.DB.BeginTx(ctx)
	if err != nil {
		return err
	}
	defer func() { _ = tx.Rollback(ctx) }()
	if err := tx.SetClaims(ctx, map[string]string{"sub": ident.Subject}); err != nil {
		return err
	}
	if err := tx.SetRole(ctx, "authenticated"); err != nil {
		return err
	}
	if err := fn(ctx, tx); err != nil {
		return err
	}
	if err := tx.Commit(ctx); err != nil {
		return err
	}
	return nil
}

var _ = fmt.Sprintf
