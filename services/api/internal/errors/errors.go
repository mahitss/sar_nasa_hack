package errors

import "net/http"

type APIError struct {
	Status  int    `json:"-"`
	Code    string `json:"code"`
	Message string `json:"message"`
}

func (e *APIError) Error() string { return e.Message }

func New(status int, code, msg string) *APIError {
	return &APIError{Status: status, Code: code, Message: msg}
}

var (
	ErrUnauthorized = New(http.StatusUnauthorized, "unauthorized", "authentication required")
	ErrForbidden    = New(http.StatusForbidden, "forbidden", "access denied")
	ErrNotFound     = New(http.StatusNotFound, "not_found", "resource not found")
	ErrBadRequest   = New(http.StatusBadRequest, "bad_request", "invalid request")
	ErrConflict     = New(http.StatusConflict, "conflict", "resource conflict")
)
