package adminaiconfighthttp

import (
	"encoding/json"
	"errors"
	"log/slog"
	"net/http"
	"strings"

	authapp "mathstudy/backend-go/internal/application/auth"
)

// Authenticator decodes Go/Python-compatible access tokens.
type Authenticator interface {
	DecodeAccessToken(string) (authapp.Principal, bool)
}

// Handler preserves the /admin/ai-config route surface while P6 AI work is TODO.
type Handler struct {
	auth   Authenticator
	logger *slog.Logger
}

// NewHandler creates an admin AI config placeholder handler.
func NewHandler(logger *slog.Logger, auth Authenticator) (*Handler, error) {
	if auth == nil {
		return nil, errors.New("admin ai config authenticator is nil")
	}
	if logger == nil {
		logger = slog.Default()
	}
	return &Handler{auth: auth, logger: logger}, nil
}

// Register attaches the AI config placeholder under prefix, for example /api/v1/admin/ai-config.
func (h *Handler) Register(mux *http.ServeMux, prefix string) {
	mux.HandleFunc(prefix, h.todo)
	mux.HandleFunc(prefix+"/", h.todo)
}

type errorResponse struct {
	Detail  string `json:"detail"`
	Code    string `json:"code,omitempty"`
	Message string `json:"message,omitempty"`
}

func (h *Handler) todo(w http.ResponseWriter, r *http.Request) {
	if _, ok := h.requireAdmin(w, r); !ok {
		return
	}
	writeJSON(w, http.StatusNotImplemented, errorResponse{
		Detail:  "AI/Agent 配置能力将在 P6 全新架构设计后迁移",
		Code:    "AI_CONFIG_TODO",
		Message: "AI/Agent 配置能力将在 P6 全新架构设计后迁移",
	})
}

func (h *Handler) requireAdmin(w http.ResponseWriter, r *http.Request) (authapp.Principal, bool) {
	authHeader := strings.TrimSpace(r.Header.Get("Authorization"))
	fields := strings.Fields(authHeader)
	if len(fields) != 2 || !strings.EqualFold(fields[0], "Bearer") {
		w.Header().Set("WWW-Authenticate", "Bearer")
		writeJSON(w, http.StatusUnauthorized, errorResponse{
			Detail:  "未认证，请先登录",
			Code:    "UNAUTHORIZED",
			Message: "未认证，请先登录",
		})
		return authapp.Principal{}, false
	}
	principal, ok := h.auth.DecodeAccessToken(fields[1])
	if !ok {
		w.Header().Set("WWW-Authenticate", "Bearer")
		writeJSON(w, http.StatusUnauthorized, errorResponse{
			Detail:  "未认证，请先登录",
			Code:    "UNAUTHORIZED",
			Message: "未认证，请先登录",
		})
		return authapp.Principal{}, false
	}
	if !authapp.IsAdmin(principal) {
		writeJSON(w, http.StatusForbidden, errorResponse{
			Detail:  "权限不足，需要管理员权限",
			Code:    "FORBIDDEN",
			Message: "权限不足，需要管理员权限",
		})
		return authapp.Principal{}, false
	}
	return principal, true
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}
