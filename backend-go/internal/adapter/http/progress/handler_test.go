package progresshttp

import (
	"context"
	"encoding/json"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	authapp "mathstudy/backend-go/internal/application/auth"
	progressapp "mathstudy/backend-go/internal/application/progress"
	"mathstudy/backend-go/internal/domain/user"
)

func TestOverviewRequiresBearerToken(t *testing.T) {
	handler := newTestHandler(t, &fakeProgressService{}, &fakeAuthenticator{})
	mux := http.NewServeMux()
	handler.Register(mux, "/api/v1/progress")

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodGet, "/api/v1/progress/overview", nil)
	mux.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d", recorder.Code)
	}
	var body map[string]string
	if err := json.Unmarshal(recorder.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}
	if body["detail"] != "未认证，请先登录" || body["code"] != "UNAUTHORIZED" {
		t.Fatalf("body = %#v", body)
	}
	if got := recorder.Header().Get("WWW-Authenticate"); got != "Bearer" {
		t.Fatalf("WWW-Authenticate = %q", got)
	}
}

func TestOverviewReturnsProgressForPrincipal(t *testing.T) {
	service := &fakeProgressService{
		overview: progressapp.Overview{
			TotalExercises: 4,
			CorrectCount:   3,
			CorrectRate:    75,
			StudyMinutes:   12,
			TodayStats: progressapp.TodayStats{
				StudyMinutes:       5,
				ExercisesCompleted: 2,
			},
		},
	}
	auth := &fakeAuthenticator{principal: authapp.Principal{UserID: "student-1", Role: user.RoleStudent}}
	handler := newTestHandler(t, service, auth)
	mux := http.NewServeMux()
	handler.Register(mux, "/api/v1/progress")

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodGet, "/api/v1/progress/overview", nil)
	request.Header.Set("Authorization", "Bearer token")
	mux.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", recorder.Code, recorder.Body.String())
	}
	if service.lastUserID != "student-1" {
		t.Fatalf("lastUserID = %q", service.lastUserID)
	}
	var body progressapp.Overview
	if err := json.Unmarshal(recorder.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}
	if body.TotalExercises != 4 || body.TodayStats.ExercisesCompleted != 2 {
		t.Fatalf("body = %#v", body)
	}
}

func TestPathAndGraphForwardQueryParameters(t *testing.T) {
	service := &fakeProgressService{}
	auth := &fakeAuthenticator{principal: authapp.Principal{UserID: "student-1", Role: user.RoleStudent}}
	handler := newTestHandler(t, service, auth)
	mux := http.NewServeMux()
	handler.Register(mux, "/api/v1/progress")

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodGet, "/api/v1/progress/path?target=node-1", nil)
	request.Header.Set("Authorization", "Bearer token")
	mux.ServeHTTP(recorder, request)
	if recorder.Code != http.StatusOK {
		t.Fatalf("path status = %d", recorder.Code)
	}
	if service.lastTarget != "node-1" {
		t.Fatalf("target = %q", service.lastTarget)
	}

	recorder = httptest.NewRecorder()
	request = httptest.NewRequest(http.MethodGet, "/api/v1/progress/knowledge-graph?chapter=第一章&type=concept&search=极限", nil)
	request.Header.Set("Authorization", "Bearer token")
	mux.ServeHTTP(recorder, request)
	if recorder.Code != http.StatusOK {
		t.Fatalf("graph status = %d", recorder.Code)
	}
	if service.lastFilter.Chapter != "第一章" || service.lastFilter.NodeType != "concept" || service.lastFilter.Search != "极限" {
		t.Fatalf("filter = %#v", service.lastFilter)
	}
}

func TestChaptersWrapsListInPythonCompatibleObject(t *testing.T) {
	service := &fakeProgressService{chapters: []string{"第一章", "第二章"}}
	auth := &fakeAuthenticator{principal: authapp.Principal{UserID: "student-1", Role: user.RoleStudent}}
	handler := newTestHandler(t, service, auth)
	mux := http.NewServeMux()
	handler.Register(mux, "/api/v1/progress")

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodGet, "/api/v1/progress/chapters", nil)
	request.Header.Set("Authorization", "Bearer token")
	mux.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("status = %d", recorder.Code)
	}
	var body chaptersResponse
	if err := json.Unmarshal(recorder.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}
	if len(body.Chapters) != 2 || body.Chapters[0] != "第一章" {
		t.Fatalf("body = %#v", body)
	}
}

func TestNewHandlerRejectsMissingDependencies(t *testing.T) {
	if _, err := NewHandler(nil, nil, &fakeAuthenticator{}); err == nil {
		t.Fatal("NewHandler(nil service) error = nil, want error")
	}
	if _, err := NewHandler(nil, &fakeProgressService{}, nil); err == nil {
		t.Fatal("NewHandler(nil auth) error = nil, want error")
	}
}

func newTestHandler(t *testing.T, service Service, auth Authenticator) *Handler {
	t.Helper()
	handler, err := NewHandler(slog.New(slog.NewTextHandler(os.Stdout, nil)), service, auth)
	if err != nil {
		t.Fatalf("NewHandler() error = %v", err)
	}
	return handler
}

type fakeAuthenticator struct {
	principal authapp.Principal
}

func (a *fakeAuthenticator) DecodeAccessToken(string) (authapp.Principal, bool) {
	if a.principal.UserID == "" {
		return authapp.Principal{}, false
	}
	return a.principal, true
}

type fakeProgressService struct {
	overview   progressapp.Overview
	chapters   []string
	lastUserID string
	lastTarget string
	lastFilter progressapp.KnowledgeNodeFilter
	lastRange  string
}

func (s *fakeProgressService) GetOverview(_ context.Context, userID string) (progressapp.Overview, error) {
	s.lastUserID = userID
	return s.overview, nil
}

func (s *fakeProgressService) GetMasteryVector(_ context.Context, userID string) (progressapp.MasteryResponse, error) {
	s.lastUserID = userID
	return progressapp.MasteryResponse{Topics: []progressapp.MasteryTopic{}, Model: "bkt"}, nil
}

func (s *fakeProgressService) GetLearningPath(_ context.Context, userID string, target string) (progressapp.PathResponse, error) {
	s.lastUserID = userID
	s.lastTarget = target
	return progressapp.PathResponse{Path: []progressapp.PathItem{}}, nil
}

func (s *fakeProgressService) GetKnowledgeGraphView(_ context.Context, userID string, filter progressapp.KnowledgeNodeFilter) (progressapp.GraphResponse, error) {
	s.lastUserID = userID
	s.lastFilter = filter
	return progressapp.GraphResponse{Nodes: []progressapp.GraphNode{}, Edges: []progressapp.GraphEdge{}}, nil
}

func (s *fakeProgressService) GetStatistics(_ context.Context, userID string, rangeType string) (progressapp.StatisticsResponse, error) {
	s.lastUserID = userID
	s.lastRange = rangeType
	return progressapp.StatisticsResponse{Daily: []progressapp.DailyStat{}, ErrorTypeDistribution: map[string]progressapp.ErrorTypeDistribution{}}, nil
}

func (s *fakeProgressService) GetClassRanking(_ context.Context, userID string) (progressapp.ClassRankingResponse, error) {
	s.lastUserID = userID
	return progressapp.ClassRankingResponse{InClass: false}, nil
}

func (s *fakeProgressService) GetChapters(context.Context) ([]string, error) {
	return s.chapters, nil
}
