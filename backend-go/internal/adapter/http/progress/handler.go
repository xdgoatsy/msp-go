package progresshttp

import (
	"context"
	"encoding/json"
	"errors"
	"log/slog"
	"net/http"
	"strings"

	authapp "mathstudy/backend-go/internal/application/auth"
	progressapp "mathstudy/backend-go/internal/application/progress"
)

// Service is the progress application surface used by HTTP handlers.
type Service interface {
	GetOverview(context.Context, string) (progressapp.Overview, error)
	GetMasteryVector(context.Context, string) (progressapp.MasteryResponse, error)
	GetLearningPath(context.Context, string, string) (progressapp.PathResponse, error)
	GetKnowledgeGraphView(context.Context, string, progressapp.KnowledgeNodeFilter) (progressapp.GraphResponse, error)
	GetStatistics(context.Context, string, string) (progressapp.StatisticsResponse, error)
	GetClassRanking(context.Context, string) (progressapp.ClassRankingResponse, error)
	GetChapters(context.Context) ([]string, error)
}

// Authenticator decodes Go/Python-compatible access tokens.
type Authenticator interface {
	DecodeAccessToken(string) (authapp.Principal, bool)
}

// Handler serves /progress endpoints.
type Handler struct {
	service Service
	auth    Authenticator
	logger  *slog.Logger
}

// NewHandler creates a progress HTTP handler.
func NewHandler(logger *slog.Logger, service Service, auth Authenticator) (*Handler, error) {
	if service == nil {
		return nil, errors.New("progress service is nil")
	}
	if auth == nil {
		return nil, errors.New("progress authenticator is nil")
	}
	if logger == nil {
		logger = slog.Default()
	}
	return &Handler{service: service, auth: auth, logger: logger}, nil
}

// Register attaches progress routes under prefix, for example /api/v1/progress.
func (h *Handler) Register(mux *http.ServeMux, prefix string) {
	mux.HandleFunc("GET "+prefix+"/overview", h.overview)
	mux.HandleFunc("GET "+prefix+"/mastery", h.mastery)
	mux.HandleFunc("GET "+prefix+"/path", h.path)
	mux.HandleFunc("GET "+prefix+"/knowledge-graph", h.knowledgeGraph)
	mux.HandleFunc("GET "+prefix+"/statistics", h.statistics)
	mux.HandleFunc("GET "+prefix+"/class-ranking", h.classRanking)
	mux.HandleFunc("GET "+prefix+"/chapters", h.chapters)
}

type chaptersResponse struct {
	Chapters []string `json:"chapters"`
}

type errorResponse struct {
	Detail  string `json:"detail"`
	Code    string `json:"code,omitempty"`
	Message string `json:"message,omitempty"`
}

func (h *Handler) overview(w http.ResponseWriter, r *http.Request) {
	principal, ok := h.requirePrincipal(w, r)
	if !ok {
		return
	}
	response, err := h.service.GetOverview(r.Context(), principal.UserID)
	if err != nil {
		h.logger.Error("get progress overview failed", "error", err)
		writeProgressError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "获取学习进度失败")
		return
	}
	writeJSON(w, http.StatusOK, response)
}

func (h *Handler) mastery(w http.ResponseWriter, r *http.Request) {
	principal, ok := h.requirePrincipal(w, r)
	if !ok {
		return
	}
	response, err := h.service.GetMasteryVector(r.Context(), principal.UserID)
	if err != nil {
		h.logger.Error("get mastery vector failed", "error", err)
		writeProgressError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "获取知识点掌握度失败")
		return
	}
	writeJSON(w, http.StatusOK, response)
}

func (h *Handler) path(w http.ResponseWriter, r *http.Request) {
	principal, ok := h.requirePrincipal(w, r)
	if !ok {
		return
	}
	response, err := h.service.GetLearningPath(r.Context(), principal.UserID, r.URL.Query().Get("target"))
	if err != nil {
		h.logger.Error("get learning path failed", "error", err)
		writeProgressError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "获取学习路径失败")
		return
	}
	writeJSON(w, http.StatusOK, response)
}

func (h *Handler) knowledgeGraph(w http.ResponseWriter, r *http.Request) {
	principal, ok := h.requirePrincipal(w, r)
	if !ok {
		return
	}
	query := r.URL.Query()
	response, err := h.service.GetKnowledgeGraphView(r.Context(), principal.UserID, progressapp.KnowledgeNodeFilter{
		Chapter:  query.Get("chapter"),
		NodeType: query.Get("type"),
		Search:   query.Get("search"),
	})
	if err != nil {
		h.logger.Error("get knowledge graph failed", "error", err)
		writeProgressError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "获取知识图谱失败")
		return
	}
	writeJSON(w, http.StatusOK, response)
}

func (h *Handler) statistics(w http.ResponseWriter, r *http.Request) {
	principal, ok := h.requirePrincipal(w, r)
	if !ok {
		return
	}
	rangeType := r.URL.Query().Get("range")
	if rangeType == "" {
		rangeType = "week"
	}
	response, err := h.service.GetStatistics(r.Context(), principal.UserID, rangeType)
	if err != nil {
		h.logger.Error("get learning statistics failed", "error", err)
		writeProgressError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "获取学习统计失败")
		return
	}
	writeJSON(w, http.StatusOK, response)
}

func (h *Handler) classRanking(w http.ResponseWriter, r *http.Request) {
	principal, ok := h.requirePrincipal(w, r)
	if !ok {
		return
	}
	response, err := h.service.GetClassRanking(r.Context(), principal.UserID)
	if err != nil {
		h.logger.Error("get class ranking failed", "error", err)
		writeProgressError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "获取班级排名失败")
		return
	}
	writeJSON(w, http.StatusOK, response)
}

func (h *Handler) chapters(w http.ResponseWriter, r *http.Request) {
	if _, ok := h.requirePrincipal(w, r); !ok {
		return
	}
	chapters, err := h.service.GetChapters(r.Context())
	if err != nil {
		h.logger.Error("get chapters failed", "error", err)
		writeProgressError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "获取章节列表失败")
		return
	}
	writeJSON(w, http.StatusOK, chaptersResponse{Chapters: chapters})
}

func (h *Handler) requirePrincipal(w http.ResponseWriter, r *http.Request) (authapp.Principal, bool) {
	authHeader := strings.TrimSpace(r.Header.Get("Authorization"))
	fields := strings.Fields(authHeader)
	if len(fields) != 2 || !strings.EqualFold(fields[0], "Bearer") {
		w.Header().Set("WWW-Authenticate", "Bearer")
		writeProgressError(w, http.StatusUnauthorized, "UNAUTHORIZED", "未认证，请先登录")
		return authapp.Principal{}, false
	}
	principal, ok := h.auth.DecodeAccessToken(fields[1])
	if !ok {
		w.Header().Set("WWW-Authenticate", "Bearer")
		writeProgressError(w, http.StatusUnauthorized, "UNAUTHORIZED", "未认证，请先登录")
		return authapp.Principal{}, false
	}
	return principal, true
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}

func writeProgressError(w http.ResponseWriter, status int, code, message string) {
	writeJSON(w, status, errorResponse{Detail: message, Code: code, Message: message})
}
