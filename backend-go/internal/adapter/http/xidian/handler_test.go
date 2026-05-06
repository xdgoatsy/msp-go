package xidianhttp

import (
	"bytes"
	"context"
	"encoding/json"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
	"time"

	authapp "mathstudy/backend-go/internal/application/auth"
	xidianapp "mathstudy/backend-go/internal/application/xidian"
	"mathstudy/backend-go/internal/domain/user"
)

func TestBindingRequiresBearerToken(t *testing.T) {
	handler := newTestHandler(t, &fakeXidianService{}, &fakeAuthenticator{})
	mux := http.NewServeMux()
	handler.Register(mux, "/api/v1/xidian")

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodGet, "/api/v1/xidian/binding", nil)
	mux.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d", recorder.Code)
	}
	if got := recorder.Header().Get("WWW-Authenticate"); got != "Bearer" {
		t.Fatalf("WWW-Authenticate = %q", got)
	}
}

func TestBindingStatusForwardsUserID(t *testing.T) {
	service := &fakeXidianService{status: xidianapp.BindingStatus{IsBound: true}}
	auth := &fakeAuthenticator{principal: authapp.Principal{UserID: "user-1", Role: user.RoleStudent}}
	handler := newTestHandler(t, service, auth)
	mux := http.NewServeMux()
	handler.Register(mux, "/api/v1/xidian")

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodGet, "/api/v1/xidian/binding", nil)
	request.Header.Set("Authorization", "Bearer token")
	mux.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", recorder.Code, recorder.Body.String())
	}
	if service.lastUserID != "user-1" {
		t.Fatalf("userID = %q", service.lastUserID)
	}
}

func TestStartCompleteUnbindAndSyncRoutes(t *testing.T) {
	now := time.Date(2026, 5, 6, 10, 0, 0, 0, time.UTC)
	service := &fakeXidianService{
		start:    xidianapp.BindStartResponse{ChallengeID: "challenge-1"},
		complete: xidianapp.BindCompleteResponse{IsBound: true, Username: "student"},
		sync:     xidianapp.SyncResponse{Data: map[string]any{"scores": []any{}}, FetchedAt: now},
	}
	auth := &fakeAuthenticator{principal: authapp.Principal{UserID: "user-1", Role: user.RoleStudent}}
	handler := newTestHandler(t, service, auth)
	mux := http.NewServeMux()
	handler.Register(mux, "/api/v1/xidian")

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodPost, "/api/v1/xidian/binding/start", nil)
	request.Header.Set("Authorization", "Bearer token")
	mux.ServeHTTP(recorder, request)
	if recorder.Code != http.StatusOK || !service.startCalled {
		t.Fatalf("start status = %d called=%t", recorder.Code, service.startCalled)
	}

	recorder = httptest.NewRecorder()
	request = httptest.NewRequest(http.MethodPost, "/api/v1/xidian/binding/complete", bytes.NewBufferString(`{"challenge_id":"challenge-1","slider_position":0.5,"username":"student","password":"pw"}`))
	request.Header.Set("Authorization", "Bearer token")
	mux.ServeHTTP(recorder, request)
	if recorder.Code != http.StatusOK || service.completeInput.ChallengeID != "challenge-1" || service.completeInput.SliderPosition != 0.5 {
		t.Fatalf("complete status = %d input=%#v body=%s", recorder.Code, service.completeInput, recorder.Body.String())
	}

	recorder = httptest.NewRecorder()
	request = httptest.NewRequest(http.MethodPost, "/api/v1/xidian/sync/scores", nil)
	request.Header.Set("Authorization", "Bearer token")
	mux.ServeHTTP(recorder, request)
	if recorder.Code != http.StatusOK || service.syncType != "score" {
		t.Fatalf("sync status = %d type=%q", recorder.Code, service.syncType)
	}

	recorder = httptest.NewRecorder()
	request = httptest.NewRequest(http.MethodPost, "/api/v1/xidian/binding/unbind", nil)
	request.Header.Set("Authorization", "Bearer token")
	mux.ServeHTTP(recorder, request)
	if recorder.Code != http.StatusOK || !service.unbindCalled {
		t.Fatalf("unbind status = %d called=%t", recorder.Code, service.unbindCalled)
	}
	var body xidianapp.UnbindResponse
	if err := json.Unmarshal(recorder.Body.Bytes(), &body); err != nil || !body.Success {
		t.Fatalf("unbind body = %#v err=%v", body, err)
	}
}

func TestSnapshotAndServiceErrorMapping(t *testing.T) {
	service := &fakeXidianService{
		snapshot: xidianapp.SnapshotResponse{Data: map[string]any{"scores": []any{}}, IsCached: true},
		err:      xidianapp.ServiceError{Code: "NO_SNAPSHOT", Message: "暂无缓存数据", Status: http.StatusNotFound},
	}
	auth := &fakeAuthenticator{principal: authapp.Principal{UserID: "user-1", Role: user.RoleStudent}}
	handler := newTestHandler(t, service, auth)
	mux := http.NewServeMux()
	handler.Register(mux, "/api/v1/xidian")

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodGet, "/api/v1/xidian/snapshot/score", nil)
	request.Header.Set("Authorization", "Bearer token")
	mux.ServeHTTP(recorder, request)
	if recorder.Code != http.StatusNotFound {
		t.Fatalf("status = %d, body = %s", recorder.Code, recorder.Body.String())
	}
	var body map[string]string
	if err := json.Unmarshal(recorder.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}
	if body["code"] != "NO_SNAPSHOT" || body["message"] != "暂无缓存数据" {
		t.Fatalf("body = %#v", body)
	}
}

func TestNewHandlerRejectsMissingDependencies(t *testing.T) {
	if _, err := NewHandler(nil, nil, &fakeAuthenticator{}); err == nil {
		t.Fatal("NewHandler(nil service) error = nil, want error")
	}
	if _, err := NewHandler(nil, &fakeXidianService{}, nil); err == nil {
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

type fakeXidianService struct {
	status        xidianapp.BindingStatus
	start         xidianapp.BindStartResponse
	complete      xidianapp.BindCompleteResponse
	sync          xidianapp.SyncResponse
	snapshot      xidianapp.SnapshotResponse
	err           error
	lastUserID    string
	startCalled   bool
	unbindCalled  bool
	completeInput xidianapp.CompleteBindingInput
	syncType      string
}

func (s *fakeXidianService) GetBindingStatus(_ context.Context, userID string) (xidianapp.BindingStatus, error) {
	s.lastUserID = userID
	return s.status, s.err
}

func (s *fakeXidianService) StartBinding(context.Context) (xidianapp.BindStartResponse, error) {
	s.startCalled = true
	return s.start, s.err
}

func (s *fakeXidianService) CompleteBinding(_ context.Context, userID string, input xidianapp.CompleteBindingInput) (xidianapp.BindCompleteResponse, error) {
	s.lastUserID = userID
	s.completeInput = input
	return s.complete, s.err
}

func (s *fakeXidianService) Unbind(_ context.Context, userID string) error {
	s.lastUserID = userID
	s.unbindCalled = true
	return s.err
}

func (s *fakeXidianService) SyncClasstable(context.Context, string) (xidianapp.SyncResponse, error) {
	s.syncType = "classtable"
	return s.sync, s.err
}

func (s *fakeXidianService) SyncExams(context.Context, string) (xidianapp.SyncResponse, error) {
	s.syncType = "exam"
	return s.sync, s.err
}

func (s *fakeXidianService) SyncScores(context.Context, string) (xidianapp.SyncResponse, error) {
	s.syncType = "score"
	return s.sync, s.err
}

func (s *fakeXidianService) GetSnapshot(context.Context, string, string) (xidianapp.SnapshotResponse, error) {
	return s.snapshot, s.err
}
