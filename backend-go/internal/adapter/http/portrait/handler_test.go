package portraithttp

import (
	"context"
	"encoding/json"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	authapp "mathstudy/backend-go/internal/application/auth"
	portraitapp "mathstudy/backend-go/internal/application/portrait"
	"mathstudy/backend-go/internal/domain/user"
)

func TestGetPortraitRequiresBearerToken(t *testing.T) {
	handler := newTestHandler(t, &fakePortraitService{}, &fakeAuthenticator{})
	mux := http.NewServeMux()
	handler.Register(mux, "/api/v1/portrait")

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodGet, "/api/v1/portrait", nil)
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

func TestGetPortraitReturnsCurrentUsersProfile(t *testing.T) {
	content := "portrait"
	service := &fakePortraitService{
		portrait: portraitapp.PortraitResponse{
			StudentID:       "student-1",
			PortraitContent: &content,
			CorrectRate:     0.75,
			HasContent:      true,
		},
	}
	auth := &fakeAuthenticator{principal: authapp.Principal{UserID: "student-1", Role: user.RoleStudent}}
	handler := newTestHandler(t, service, auth)
	mux := http.NewServeMux()
	handler.Register(mux, "/api/v1/portrait")

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodGet, "/api/v1/portrait", nil)
	request.Header.Set("Authorization", "Bearer token")
	mux.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", recorder.Code, recorder.Body.String())
	}
	if service.lastUserID != "student-1" {
		t.Fatalf("lastUserID = %q", service.lastUserID)
	}
	var body portraitapp.PortraitResponse
	if err := json.Unmarshal(recorder.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}
	if body.StudentID != "student-1" || !body.HasContent || body.CorrectRate != 0.75 {
		t.Fatalf("body = %#v", body)
	}
}

func TestGenerateAndClearPortrait(t *testing.T) {
	service := &fakePortraitService{
		generated: portraitapp.GenerateResponse{
			PortraitContent:     "generated",
			PortraitGeneratedAt: "2026-04-25T11:00:00",
			PortraitVersion:     2,
		},
		clear: portraitapp.ClearResponse{Cleared: true, Message: "画像已清除"},
	}
	auth := &fakeAuthenticator{principal: authapp.Principal{UserID: "student-1", Role: user.RoleStudent}}
	handler := newTestHandler(t, service, auth)
	mux := http.NewServeMux()
	handler.Register(mux, "/api/v1/portrait")

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodPost, "/api/v1/portrait/generate", nil)
	request.Header.Set("Authorization", "Bearer token")
	mux.ServeHTTP(recorder, request)
	if recorder.Code != http.StatusOK {
		t.Fatalf("generate status = %d", recorder.Code)
	}
	var generated portraitapp.GenerateResponse
	if err := json.Unmarshal(recorder.Body.Bytes(), &generated); err != nil {
		t.Fatalf("invalid generate JSON: %v", err)
	}
	if generated.PortraitVersion != 2 || service.lastUserID != "student-1" {
		t.Fatalf("generated = %#v user=%q", generated, service.lastUserID)
	}

	recorder = httptest.NewRecorder()
	request = httptest.NewRequest(http.MethodDelete, "/api/v1/portrait", nil)
	request.Header.Set("Authorization", "Bearer token")
	mux.ServeHTTP(recorder, request)
	if recorder.Code != http.StatusOK {
		t.Fatalf("clear status = %d", recorder.Code)
	}
	var clear portraitapp.ClearResponse
	if err := json.Unmarshal(recorder.Body.Bytes(), &clear); err != nil {
		t.Fatalf("invalid clear JSON: %v", err)
	}
	if !clear.Cleared || clear.Message != "画像已清除" {
		t.Fatalf("clear = %#v", clear)
	}
}

func TestNewHandlerRejectsMissingDependencies(t *testing.T) {
	if _, err := NewHandler(nil, nil, &fakeAuthenticator{}); err == nil {
		t.Fatal("NewHandler(nil service) error = nil, want error")
	}
	if _, err := NewHandler(nil, &fakePortraitService{}, nil); err == nil {
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

type fakePortraitService struct {
	portrait   portraitapp.PortraitResponse
	generated  portraitapp.GenerateResponse
	clear      portraitapp.ClearResponse
	lastUserID string
}

func (s *fakePortraitService) GetPortrait(_ context.Context, userID string) (portraitapp.PortraitResponse, error) {
	s.lastUserID = userID
	return s.portrait, nil
}

func (s *fakePortraitService) GeneratePortrait(_ context.Context, userID string) (portraitapp.GenerateResponse, error) {
	s.lastUserID = userID
	return s.generated, nil
}

func (s *fakePortraitService) ClearPortrait(_ context.Context, userID string) (portraitapp.ClearResponse, error) {
	s.lastUserID = userID
	return s.clear, nil
}
