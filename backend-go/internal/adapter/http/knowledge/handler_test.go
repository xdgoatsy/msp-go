package knowledgehttp

import (
	"bytes"
	"context"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	authapp "mathstudy/backend-go/internal/application/auth"
	knowledgeapp "mathstudy/backend-go/internal/application/knowledge"
	"mathstudy/backend-go/internal/domain/user"
)

func TestKnowledgeRoutesRequireAdmin(t *testing.T) {
	handler := newKnowledgeTestHandler(t, &fakeKnowledgeService{}, &fakeAuthenticator{})
	mux := http.NewServeMux()
	handler.Register(mux, "/api/v1/admin/knowledge")

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodGet, "/api/v1/admin/knowledge/stats", nil)
	mux.ServeHTTP(recorder, request)
	if recorder.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d", recorder.Code)
	}
	if got := recorder.Header().Get("WWW-Authenticate"); got != "Bearer" {
		t.Fatalf("WWW-Authenticate = %q", got)
	}

	auth := &fakeAuthenticator{principal: authapp.Principal{UserID: "teacher-1", Role: user.RoleTeacher}}
	handler = newKnowledgeTestHandler(t, &fakeKnowledgeService{}, auth)
	mux = http.NewServeMux()
	handler.Register(mux, "/api/v1/admin/knowledge")
	recorder = httptest.NewRecorder()
	request = httptest.NewRequest(http.MethodGet, "/api/v1/admin/knowledge/stats", nil)
	request.Header.Set("Authorization", "Bearer token")
	mux.ServeHTTP(recorder, request)
	if recorder.Code != http.StatusForbidden {
		t.Fatalf("status = %d", recorder.Code)
	}
}

func TestListNodesParsesFilters(t *testing.T) {
	service := &fakeKnowledgeService{nodeListResponse: knowledgeapp.NodeListResponse{Items: []knowledgeapp.KnowledgeNode{}, Page: 2, PageSize: 50}}
	auth := &fakeAuthenticator{principal: authapp.Principal{UserID: "admin-1", Role: user.RoleAdmin}}
	handler := newKnowledgeTestHandler(t, service, auth)
	mux := http.NewServeMux()
	handler.Register(mux, "/api/v1/admin/knowledge")

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodGet, "/api/v1/admin/knowledge/nodes?page=2&page_size=50&type=concept&chapter=第一章&search=极限", nil)
	request.Header.Set("Authorization", "Bearer token")
	mux.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("status = %d body=%s", recorder.Code, recorder.Body.String())
	}
	if service.lastFilter.Page != 2 || service.lastFilter.PageSize != 50 || service.lastFilter.NodeType != "concept" || service.lastFilter.Chapter != "第一章" {
		t.Fatalf("filter = %#v", service.lastFilter)
	}
}

func TestCreateNodeValidatesAndForwards(t *testing.T) {
	service := &fakeKnowledgeService{
		nodeResponse: knowledgeapp.NodeResponse{Success: true, Message: "创建成功", Node: &knowledgeapp.KnowledgeNode{ID: "node-1"}},
	}
	auth := &fakeAuthenticator{principal: authapp.Principal{UserID: "admin-1", Role: user.RoleAdmin}}
	handler := newKnowledgeTestHandler(t, service, auth)
	mux := http.NewServeMux()
	handler.Register(mux, "/api/v1/admin/knowledge")

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodPost, "/api/v1/admin/knowledge/nodes", bytes.NewBufferString(`{"name":"","node_type":"concept"}`))
	request.Header.Set("Authorization", "Bearer token")
	mux.ServeHTTP(recorder, request)
	if recorder.Code != http.StatusUnprocessableEntity {
		t.Fatalf("status = %d", recorder.Code)
	}

	recorder = httptest.NewRecorder()
	request = httptest.NewRequest(http.MethodPost, "/api/v1/admin/knowledge/nodes", bytes.NewBufferString(`{"name":"极限","node_type":"concept","difficulty":0.4,"tags":["基础"]}`))
	request.Header.Set("Authorization", "Bearer token")
	mux.ServeHTTP(recorder, request)
	if recorder.Code != http.StatusCreated {
		t.Fatalf("status = %d body=%s", recorder.Code, recorder.Body.String())
	}
	if service.lastNodeInput.Name != "极限" || service.lastNodeInput.NodeType != "concept" || len(service.lastNodeInput.Tags) != 1 {
		t.Fatalf("input = %#v", service.lastNodeInput)
	}
}

func TestRelationRoutesForwardIDs(t *testing.T) {
	service := &fakeKnowledgeService{
		relationResponse: knowledgeapp.RelationResponse{Success: true, Message: "更新成功", Relation: &knowledgeapp.KnowledgeRelation{ID: "rel-1"}},
		deleteResponse:   knowledgeapp.DeleteResponse{Success: true, Message: "删除成功"},
	}
	auth := &fakeAuthenticator{principal: authapp.Principal{UserID: "admin-1", Role: user.RoleAdmin}}
	handler := newKnowledgeTestHandler(t, service, auth)
	mux := http.NewServeMux()
	handler.Register(mux, "/api/v1/admin/knowledge")

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodPut, "/api/v1/admin/knowledge/relations/rel-1", bytes.NewBufferString(`{"relation_type":"used_in","weight":0.7}`))
	request.Header.Set("Authorization", "Bearer token")
	mux.ServeHTTP(recorder, request)
	if recorder.Code != http.StatusOK || service.lastRelationID != "rel-1" {
		t.Fatalf("update status=%d relation=%q", recorder.Code, service.lastRelationID)
	}

	recorder = httptest.NewRecorder()
	request = httptest.NewRequest(http.MethodDelete, "/api/v1/admin/knowledge/relations/rel-2", nil)
	request.Header.Set("Authorization", "Bearer token")
	mux.ServeHTTP(recorder, request)
	if recorder.Code != http.StatusOK || service.lastRelationID != "rel-2" {
		t.Fatalf("delete status=%d relation=%q", recorder.Code, service.lastRelationID)
	}
}

func TestNewHandlerRejectsMissingDependencies(t *testing.T) {
	if _, err := NewHandler(nil, nil, &fakeAuthenticator{}); err == nil {
		t.Fatal("NewHandler(nil service) error = nil, want error")
	}
	if _, err := NewHandler(nil, &fakeKnowledgeService{}, nil); err == nil {
		t.Fatal("NewHandler(nil auth) error = nil, want error")
	}
}

func newKnowledgeTestHandler(t *testing.T, service Service, auth Authenticator) *Handler {
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

type fakeKnowledgeService struct {
	statsResponse        knowledgeapp.Stats
	chaptersResponse     []string
	nodeListResponse     knowledgeapp.NodeListResponse
	simpleNodesResponse  []knowledgeapp.SimpleNode
	node                 knowledgeapp.KnowledgeNode
	nodeResponse         knowledgeapp.NodeResponse
	deleteResponse       knowledgeapp.DeleteResponse
	relationListResponse knowledgeapp.RelationListResponse
	relationResponse     knowledgeapp.RelationResponse
	err                  error
	lastFilter           knowledgeapp.NodeFilter
	lastNodeID           string
	lastNodeInput        knowledgeapp.NodeInput
	lastNodeUpdate       knowledgeapp.NodeUpdate
	lastRelationID       string
	lastRelationInput    knowledgeapp.RelationInput
	lastRelationUpdate   knowledgeapp.RelationUpdate
}

func (s *fakeKnowledgeService) GetStats(context.Context) (knowledgeapp.Stats, error) {
	return s.statsResponse, s.err
}

func (s *fakeKnowledgeService) GetChapters(context.Context) ([]string, error) {
	return s.chaptersResponse, s.err
}

func (s *fakeKnowledgeService) ListNodes(_ context.Context, filter knowledgeapp.NodeFilter) (knowledgeapp.NodeListResponse, error) {
	s.lastFilter = filter
	return s.nodeListResponse, s.err
}

func (s *fakeKnowledgeService) GetAllNodesSimple(context.Context) ([]knowledgeapp.SimpleNode, error) {
	return s.simpleNodesResponse, s.err
}

func (s *fakeKnowledgeService) GetNode(_ context.Context, nodeID string) (knowledgeapp.KnowledgeNode, error) {
	s.lastNodeID = nodeID
	return s.node, s.err
}

func (s *fakeKnowledgeService) CreateNode(_ context.Context, input knowledgeapp.NodeInput) (knowledgeapp.NodeResponse, error) {
	s.lastNodeInput = input
	return s.nodeResponse, s.err
}

func (s *fakeKnowledgeService) UpdateNode(_ context.Context, nodeID string, update knowledgeapp.NodeUpdate) (knowledgeapp.NodeResponse, error) {
	s.lastNodeID = nodeID
	s.lastNodeUpdate = update
	return s.nodeResponse, s.err
}

func (s *fakeKnowledgeService) DeleteNode(_ context.Context, nodeID string) (knowledgeapp.DeleteResponse, error) {
	s.lastNodeID = nodeID
	return s.deleteResponse, s.err
}

func (s *fakeKnowledgeService) ListRelations(context.Context, string) (knowledgeapp.RelationListResponse, error) {
	return s.relationListResponse, s.err
}

func (s *fakeKnowledgeService) CreateRelation(_ context.Context, input knowledgeapp.RelationInput) (knowledgeapp.RelationResponse, error) {
	s.lastRelationInput = input
	return s.relationResponse, s.err
}

func (s *fakeKnowledgeService) UpdateRelation(_ context.Context, relationID string, update knowledgeapp.RelationUpdate) (knowledgeapp.RelationResponse, error) {
	s.lastRelationID = relationID
	s.lastRelationUpdate = update
	return s.relationResponse, s.err
}

func (s *fakeKnowledgeService) DeleteRelation(_ context.Context, relationID string) (knowledgeapp.DeleteResponse, error) {
	s.lastRelationID = relationID
	return s.deleteResponse, s.err
}
