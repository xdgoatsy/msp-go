package portraithttp

import (
	"context"
	"encoding/json"
	"errors"
	"log/slog"
	"net/http"
	"strings"

	authapp "mathstudy/backend-go/internal/application/auth"
	portraitapp "mathstudy/backend-go/internal/application/portrait"
)

// Service is the portrait application surface used by HTTP handlers.
type Service interface {
	GetPortrait(context.Context, string) (portraitapp.PortraitResponse, error)
	GeneratePortrait(context.Context, string) (portraitapp.GenerateResponse, error)
	ClearPortrait(context.Context, string) (portraitapp.ClearResponse, error)
}

// Authenticator decodes Go/Python-compatible access tokens.
type Authenticator interface {
	DecodeAccessToken(string) (authapp.Principal, bool)
}

// Handler serves /portrait endpoints.
type Handler struct {
	service Service
	auth    Authenticator
	logger  *slog.Logger
}

// NewHandler creates a portrait HTTP handler.
func NewHandler(logger *slog.Logger, service Service, auth Authenticator) (*Handler, error) {
	if service == nil {
		return nil, errors.New("portrait service is nil")
	}
	if auth == nil {
		return nil, errors.New("portrait authenticator is nil")
	}
	if logger == nil {
		logger = slog.Default()
	}
	return &Handler{service: service, auth: auth, logger: logger}, nil
}

// Register attaches portrait routes under prefix, for example /api/v1/portrait.
func (h *Handler) Register(mux *http.ServeMux, prefix string) {
	mux.HandleFunc("GET "+prefix, h.get)
	mux.HandleFunc("POST "+prefix+"/generate", h.generate)
	mux.HandleFunc("DELETE "+prefix, h.clear)
}

type errorResponse struct {
	Detail  string `json:"detail"`
	Code    string `json:"code,omitempty"`
	Message string `json:"message,omitempty"`
}

func (h *Handler) get(w http.ResponseWriter, r *http.Request) {
	principal, ok := h.requirePrincipal(w, r)
	if !ok {
		return
	}
	response, err := h.service.GetPortrait(r.Context(), principal.UserID)
	if err != nil {
		h.logger.Error("get portrait failed", "error", err)
		writePortraitError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "获取学生画像失败")
		return
	}
	writeJSON(w, http.StatusOK, response)
}

func (h *Handler) generate(w http.ResponseWriter, r *http.Request) {
	principal, ok := h.requirePrincipal(w, r)
	if !ok {
		return
	}
	response, err := h.service.GeneratePortrait(r.Context(), principal.UserID)
	if err != nil {
		h.logger.Error("generate portrait failed", "error", err)
		writePortraitError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "画像生成失败，请稍后重试")
		return
	}
	writeJSON(w, http.StatusOK, response)
}

func (h *Handler) clear(w http.ResponseWriter, r *http.Request) {
	principal, ok := h.requirePrincipal(w, r)
	if !ok {
		return
	}
	response, err := h.service.ClearPortrait(r.Context(), principal.UserID)
	if err != nil {
		h.logger.Error("clear portrait failed", "error", err)
		writePortraitError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "清除学生画像失败")
		return
	}
	writeJSON(w, http.StatusOK, response)
}

func (h *Handler) requirePrincipal(w http.ResponseWriter, r *http.Request) (authapp.Principal, bool) {
	authHeader := strings.TrimSpace(r.Header.Get("Authorization"))
	fields := strings.Fields(authHeader)
	if len(fields) != 2 || !strings.EqualFold(fields[0], "Bearer") {
		w.Header().Set("WWW-Authenticate", "Bearer")
		writePortraitError(w, http.StatusUnauthorized, "UNAUTHORIZED", "未认证，请先登录")
		return authapp.Principal{}, false
	}
	principal, ok := h.auth.DecodeAccessToken(fields[1])
	if !ok {
		w.Header().Set("WWW-Authenticate", "Bearer")
		writePortraitError(w, http.StatusUnauthorized, "UNAUTHORIZED", "未认证，请先登录")
		return authapp.Principal{}, false
	}
	return principal, true
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}

func writePortraitError(w http.ResponseWriter, status int, code, message string) {
	writeJSON(w, status, errorResponse{Detail: message, Code: code, Message: message})
}
