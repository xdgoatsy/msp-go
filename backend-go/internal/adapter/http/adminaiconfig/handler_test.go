package adminaiconfighthttp

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	authapp "mathstudy/backend-go/internal/application/auth"
	"mathstudy/backend-go/internal/domain/user"
)

func TestPlaceholderRequiresAdmin(t *testing.T) {
	handler := newTestHandler(t, &fakeAuthenticator{})
	mux := http.NewServeMux()
	handler.Register(mux, "/api/v1/admin/ai-config")

	request := httptest.NewRequest(http.MethodGet, "/api/v1/admin/ai-config/providers", nil)
	recorder := httptest.NewRecorder()
	mux.ServeHTTP(recorder, request)
	if recorder.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d", recorder.Code)
	}

	handler = newTestHandler(t, &fakeAuthenticator{principal: authapp.Principal{UserID: "teacher-1", Role: user.RoleTeacher}})
	mux = http.NewServeMux()
	handler.Register(mux, "/api/v1/admin/ai-config")
	request = httptest.NewRequest(http.MethodGet, "/api/v1/admin/ai-config/providers", nil)
	request.Header.Set("Authorization", "Bearer token")
	recorder = httptest.NewRecorder()
	mux.ServeHTTP(recorder, request)
	if recorder.Code != http.StatusForbidden {
		t.Fatalf("status = %d", recorder.Code)
	}
}

func TestPlaceholderReturnsExplicitAITODO(t *testing.T) {
	handler := newTestHandler(t, &fakeAuthenticator{principal: authapp.Principal{UserID: "admin-1", Role: user.RoleAdmin}})
	mux := http.NewServeMux()
	handler.Register(mux, "/api/v1/admin/ai-config")

	for _, tc := range []struct {
		name   string
		method string
		path   string
	}{
		{name: "provider list", method: http.MethodGet, path: "/api/v1/admin/ai-config/providers"},
		{name: "provider create", method: http.MethodPost, path: "/api/v1/admin/ai-config/providers"},
		{name: "agent update", method: http.MethodPut, path: "/api/v1/admin/ai-config/agents/tutor"},
		{name: "exact prefix", method: http.MethodGet, path: "/api/v1/admin/ai-config"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			request := httptest.NewRequest(tc.method, tc.path, nil)
			request.Header.Set("Authorization", "Bearer token")
			recorder := httptest.NewRecorder()
			mux.ServeHTTP(recorder, request)
			if recorder.Code != http.StatusNotImplemented {
				t.Fatalf("status=%d body=%s", recorder.Code, recorder.Body.String())
			}
			var response map[string]string
			if err := json.Unmarshal(recorder.Body.Bytes(), &response); err != nil {
				t.Fatalf("invalid JSON: %v", err)
			}
			if response["code"] != "AI_CONFIG_TODO" || response["message"] == "" {
				t.Fatalf("response = %#v", response)
			}
		})
	}
}

func TestNewHandlerRejectsMissingAuth(t *testing.T) {
	if _, err := NewHandler(nil, nil); err == nil {
		t.Fatal("NewHandler(nil auth) error = nil, want error")
	}
}

func newTestHandler(t *testing.T, auth Authenticator) *Handler {
	t.Helper()
	handler, err := NewHandler(slog.New(slog.NewTextHandler(os.Stdout, nil)), auth)
	if err != nil {
		t.Fatalf("NewHandler() error = %v", err)
	}
	return handler
}

type fakeAuthenticator struct {
	principal authapp.Principal
}

func (a *fakeAuthenticator) DecodeAccessToken(string) (authapp.Principal, bool) {
	return a.principal, a.principal.UserID != ""
}
