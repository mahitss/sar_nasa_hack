package transaction

import (
	"context"
)

type Identity struct {
	Subject string
}

type TxManager interface {
	WithinTransaction(ctx context.Context, subject string, fn func(ctx context.Context) error) error
	WithinWorkerTransaction(ctx context.Context, workerID string, fn func(ctx context.Context) error) error
}

type MemoryTxManager struct{}

func NewMemoryTxManager() *MemoryTxManager {
	return &MemoryTxManager{}
}

func (m *MemoryTxManager) WithinTransaction(ctx context.Context, subject string, fn func(ctx context.Context) error) error {
	return fn(ctx)
}

func (m *MemoryTxManager) WithinWorkerTransaction(ctx context.Context, workerID string, fn func(ctx context.Context) error) error {
	return fn(ctx)
}
