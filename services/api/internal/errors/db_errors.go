package errors

import (
	"errors"
	"net/http"
	"strings"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
)

var (
	ErrUnprocessableEntity = New(http.StatusUnprocessableEntity, "unprocessable_entity", "validation constraint failure")
	ErrInternalError       = New(http.StatusInternalServerError, "internal_error", "internal server error")
)

// MapDBError converts database/pgx errors into safe APIError types without leaking SQL or internal details.
func MapDBError(err error) *APIError {
	if err == nil {
		return nil
	}

	var apiErr *APIError
	if errors.As(err, &apiErr) {
		return apiErr
	}

	if errors.Is(err, pgx.ErrNoRows) {
		return ErrNotFound
	}

	var pgErr *pgconn.PgError
	if errors.As(err, &pgErr) {
		switch pgErr.Code {
		case "42501": // insufficient_privilege (RLS policy violation or grant denial)
			return ErrForbidden
		case "23505": // unique_violation
			return ErrConflict
		case "23503": // foreign_key_violation
			return New(http.StatusUnprocessableEntity, "foreign_key_violation", "referenced resource does not exist or constraint violated")
		case "23514": // check_violation
			return New(http.StatusUnprocessableEntity, "check_violation", "input violates validation constraints")
		case "P0001": // plpgsql raise_exception
			msg := pgErr.Message
			switch {
			case strings.Contains(msg, "invalid decision value"):
				return New(http.StatusBadRequest, "bad_request", "invalid decision value")
			case strings.Contains(msg, "not authorized to review"):
				return ErrForbidden
			case strings.Contains(msg, "cannot review own evidence"):
				return ErrForbidden
			case strings.Contains(msg, "evidence not in incident"):
				return ErrNotFound
			case strings.Contains(msg, "cannot remove the last owner") || strings.Contains(msg, "cannot demote the last owner"):
				return New(http.StatusUnprocessableEntity, "last_owner_protection", msg)
			case strings.Contains(msg, "illegal processing_job transition"):
				return New(http.StatusConflict, "invalid_state_transition", msg)
			case strings.Contains(msg, "terminal job requires finished_at"):
				return New(http.StatusUnprocessableEntity, "job_validation_error", msg)
			default:
				return New(http.StatusBadRequest, "validation_error", msg)
			}
		}
	}

	return ErrInternalError
}
