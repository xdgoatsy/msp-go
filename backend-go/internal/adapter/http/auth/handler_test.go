package authhttp

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
	"mathstudy/backend-go/internal/domain/user"
	"mathstudy/backend-go/internal/platform/config"
)

func TestLoginSetsRefreshCookieAndReturnsAccessToken(t *testing.T) {
	service := &fakeAuthService{
		loginResult: authapp.AuthResult{
			Success:      true,
			AccessToken:  "access-token",
			RefreshToken: "refresh-token",
			User: user.User{
				ID:       "user-1",
				Username: "alice",
				Email:    "alice@example.com",
				Role:     user.RoleStudent,
			},
		},
	}
	handler := newTestHandler(t, service)
	mux := http.NewServeMux()
	handler.Register(mux, "/api/v1/auth")

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodPost, "/api/v1/auth/login", bytes.NewBufferString(`{"username":"alice","password":"Strong1!"}`))
	mux.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", recorder.Code, recorder.Body.String())
	}
	var body loginResponse
	if err := json.Unmarshal(recorder.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}
	if body.AccessToken != "access-token" || body.TokenType != "bearer" || body.User.Role != "student" {
		t.Fatalf("body = %#v", body)
	}
	refreshCookie := cookieByName(t, recorder.Result().Cookies(), refreshCookieName)
	if refreshCookie.Value != "refresh-token" {
		t.Fatalf("cookie = %#v", refreshCookie)
	}
	if refreshCookie.Path != "/api/v1/auth" || !refreshCookie.HttpOnly || refreshCookie.Secure {
		t.Fatalf("cookie flags = %#v", refreshCookie)
	}
	csrfCookie := cookieByName(t, recorder.Result().Cookies(), csrfCookieName)
	if csrfCookie.Value == "" || csrfCookie.Path != "/" || csrfCookie.HttpOnly || csrfCookie.Secure {
		t.Fatalf("csrf cookie = %#v", csrfCookie)
	}
}

func TestLoginFailureUsesFastAPICompatibleDetail(t *testing.T) {
	service := &fakeAuthService{
		loginResult: authapp.AuthResult{Success: false, Error: "用户名或密码错误"},
	}
	handler := newTestHandler(t, service)
	mux := http.NewServeMux()
	handler.Register(mux, "/api/v1/auth")

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodPost, "/api/v1/auth/login", bytes.NewBufferString(`{"username":"alice","password":"bad"}`))
	mux.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d", recorder.Code)
	}
	var body map[string]string
	if err := json.Unmarshal(recorder.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}
	if body["detail"] != "用户名或密码错误" || body["code"] != "UNAUTHORIZED" {
		t.Fatalf("body = %#v", body)
	}
	if got := recorder.Header().Get("WWW-Authenticate"); got != "Bearer" {
		t.Fatalf("WWW-Authenticate = %q", got)
	}
}

func TestRefreshClearsInvalidCookie(t *testing.T) {
	handler := newTestHandler(t, &fakeAuthService{})
	mux := http.NewServeMux()
	handler.Register(mux, "/api/v1/auth")

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodPost, "/api/v1/auth/refresh", nil)
	addCSRFCookies(request, "csrf-token")
	request.AddCookie(&http.Cookie{Name: refreshCookieName, Value: "bad"})
	mux.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d", recorder.Code)
	}
	cookies := recorder.Result().Cookies()
	if cookieByName(t, cookies, refreshCookieName).MaxAge != -1 || cookieByName(t, cookies, csrfCookieName).MaxAge != -1 {
		t.Fatalf("cookies = %#v", cookies)
	}
}

func TestRefreshRequiresCSRFToken(t *testing.T) {
	handler := newTestHandler(t, &fakeAuthService{
		refreshPrincipal: authapp.RefreshPrincipal{UserID: "user-1", JTI: "jti"},
	})
	mux := http.NewServeMux()
	handler.Register(mux, "/api/v1/auth")

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodPost, "/api/v1/auth/refresh", nil)
	request.AddCookie(&http.Cookie{Name: refreshCookieName, Value: "refresh-token"})
	mux.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusForbidden {
		t.Fatalf("status = %d, body = %s", recorder.Code, recorder.Body.String())
	}
	var body map[string]string
	if err := json.Unmarshal(recorder.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}
	if body["code"] != "CSRF_TOKEN_MISSING" {
		t.Fatalf("body = %#v", body)
	}
}

func TestRefreshRotatesRefreshAndCSRFCookies(t *testing.T) {
	handler := newTestHandler(t, &fakeAuthService{
		refreshPrincipal:    authapp.RefreshPrincipal{UserID: "user-1", JTI: "jti"},
		refreshAccessToken:  "new-access-token",
		refreshRefreshToken: "new-refresh-token",
	})
	mux := http.NewServeMux()
	handler.Register(mux, "/api/v1/auth")

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodPost, "/api/v1/auth/refresh", nil)
	request.AddCookie(&http.Cookie{Name: refreshCookieName, Value: "old-refresh-token"})
	addCSRFCookies(request, "csrf-token")
	mux.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", recorder.Code, recorder.Body.String())
	}
	var body refreshResponse
	if err := json.Unmarshal(recorder.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}
	if body.AccessToken != "new-access-token" || body.TokenType != "bearer" {
		t.Fatalf("body = %#v", body)
	}
	cookies := recorder.Result().Cookies()
	if cookieByName(t, cookies, refreshCookieName).Value != "new-refresh-token" {
		t.Fatalf("cookies = %#v", cookies)
	}
	if csrfCookie := cookieByName(t, cookies, csrfCookieName); csrfCookie.Value == "" || csrfCookie.Value == "csrf-token" {
		t.Fatalf("csrf cookie was not rotated: %#v", csrfCookie)
	}
}

func TestLogoutRequiresCSRFAndClearsCookies(t *testing.T) {
	service := &fakeAuthService{}
	handler := newTestHandler(t, service)
	mux := http.NewServeMux()
	handler.Register(mux, "/api/v1/auth")

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodPost, "/api/v1/auth/logout", nil)
	request.AddCookie(&http.Cookie{Name: refreshCookieName, Value: "refresh-token"})
	mux.ServeHTTP(recorder, request)
	if recorder.Code != http.StatusForbidden {
		t.Fatalf("missing csrf status = %d", recorder.Code)
	}
	if service.revokedToken != "" {
		t.Fatalf("revoked token without csrf = %q", service.revokedToken)
	}

	recorder = httptest.NewRecorder()
	request = httptest.NewRequest(http.MethodPost, "/api/v1/auth/logout", nil)
	request.AddCookie(&http.Cookie{Name: refreshCookieName, Value: "refresh-token"})
	addCSRFCookies(request, "csrf-token")
	mux.ServeHTTP(recorder, request)
	if recorder.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", recorder.Code, recorder.Body.String())
	}
	if service.revokedToken != "refresh-token" {
		t.Fatalf("revoked token = %q", service.revokedToken)
	}
	cookies := recorder.Result().Cookies()
	if cookieByName(t, cookies, refreshCookieName).MaxAge != -1 || cookieByName(t, cookies, csrfCookieName).MaxAge != -1 {
		t.Fatalf("cookies = %#v", cookies)
	}
}

func TestMeRequiresBearerToken(t *testing.T) {
	handler := newTestHandler(t, &fakeAuthService{})
	mux := http.NewServeMux()
	handler.Register(mux, "/api/v1/auth")

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodGet, "/api/v1/auth/me", nil)
	mux.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d", recorder.Code)
	}
	var body map[string]string
	if err := json.Unmarshal(recorder.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}
	if body["detail"] != "未认证，请先登录" {
		t.Fatalf("body = %#v", body)
	}
}

func TestNewHandlerRejectsNilService(t *testing.T) {
	if _, err := NewHandler(config.Config{}, nil, nil); err == nil {
		t.Fatal("NewHandler(nil service) error = nil, want error")
	}
}

func newTestHandler(t *testing.T, service Service) *Handler {
	t.Helper()
	handler, err := NewHandler(config.Config{
		Environment:           "development",
		APIV1Prefix:           "/api/v1",
		JWTRefreshTokenExpire: 7 * 24 * time.Hour,
	}, slog.New(slog.NewTextHandler(os.Stdout, nil)), service)
	if err != nil {
		t.Fatalf("NewHandler() error = %v", err)
	}
	return handler
}

type fakeAuthService struct {
	loginResult          authapp.AuthResult
	registerResult       authapp.AuthResult
	principal            authapp.Principal
	refreshPrincipal     authapp.RefreshPrincipal
	refreshAccessToken   string
	refreshRefreshToken  string
	registrationSettings authapp.RegistrationSettings
	revokedToken         string
}

func (s *fakeAuthService) Authenticate(context.Context, string, string) (authapp.AuthResult, error) {
	return s.loginResult, nil
}

func (s *fakeAuthService) Register(context.Context, string, string, string, string) (authapp.AuthResult, error) {
	return s.registerResult, nil
}

func (s *fakeAuthService) ChangePassword(context.Context, string, string, string) (bool, string, error) {
	return true, "密码修改成功", nil
}

func (s *fakeAuthService) GetUserByID(context.Context, string) (user.User, bool, error) {
	return user.User{ID: "user-1", Username: "alice", Email: "alice@example.com", Role: user.RoleStudent}, true, nil
}

func (s *fakeAuthService) RefreshTokens(context.Context, authapp.RefreshPrincipal) (string, string, bool, error) {
	if s.refreshAccessToken == "" {
		return "", "", false, nil
	}
	return s.refreshAccessToken, s.refreshRefreshToken, true, nil
}

func (s *fakeAuthService) DecodeAccessToken(string) (authapp.Principal, bool) {
	if s.principal.UserID == "" {
		return authapp.Principal{}, false
	}
	return s.principal, true
}

func (s *fakeAuthService) DecodeRefreshToken(string) (authapp.RefreshPrincipal, string, bool) {
	if s.refreshPrincipal.UserID == "" {
		return authapp.RefreshPrincipal{}, "Refresh token 无效或已过期", false
	}
	return s.refreshPrincipal, "", true
}

func (s *fakeAuthService) RevokeRefreshToken(_ context.Context, token string) error {
	s.revokedToken = token
	return nil
}

func (s *fakeAuthService) RegistrationSettings(context.Context) (authapp.RegistrationSettings, error) {
	if !s.registrationSettings.AllowStudent && !s.registrationSettings.AllowTeacher {
		return authapp.RegistrationSettings{AllowStudent: true, AllowTeacher: true}, nil
	}
	return s.registrationSettings, nil
}

func (s *fakeAuthService) SubmitPasswordReset(context.Context, string, string, string) (authapp.PasswordResetResult, error) {
	return authapp.PasswordResetResult{Success: true, Message: "申请已提交，请等待管理员审批"}, nil
}

func (s *fakeAuthService) PasswordResetStatus(context.Context, string, string) (authapp.PasswordResetStatus, error) {
	return authapp.PasswordResetStatus{HasPending: false}, nil
}

func addCSRFCookies(request *http.Request, token string) {
	request.AddCookie(&http.Cookie{Name: csrfCookieName, Value: token})
	request.Header.Set(csrfHeaderName, token)
}

func cookieByName(t *testing.T, cookies []*http.Cookie, name string) *http.Cookie {
	t.Helper()
	for _, cookie := range cookies {
		if cookie.Name == name {
			return cookie
		}
	}
	t.Fatalf("cookie %q not found in %#v", name, cookies)
	return nil
}
