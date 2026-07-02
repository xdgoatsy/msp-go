package teacherhttp

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"

	authapp "mathstudy/backend-go/internal/application/auth"
	teacherapp "mathstudy/backend-go/internal/application/teacher"
	"mathstudy/backend-go/internal/domain/user"
)

func TestTeacherRoutesRequireBearerToken(t *testing.T) {
	handler := newTeacherTestHandler(t, &fakeTeacherService{}, &fakeAuthenticator{})
	mux := http.NewServeMux()
	handler.Register(mux, "/api/v1/teacher")

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodGet, "/api/v1/teacher/dashboard/stats", nil)
	mux.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d", recorder.Code)
	}
	if got := recorder.Header().Get("WWW-Authenticate"); got != "Bearer" {
		t.Fatalf("WWW-Authenticate = %q", got)
	}
	var body map[string]string
	if err := json.Unmarshal(recorder.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}
	if body["detail"] != "未认证，请先登录" || body["code"] != "UNAUTHORIZED" {
		t.Fatalf("body = %#v", body)
	}
}

func TestTeacherRoutesRequireTeacherRole(t *testing.T) {
	auth := &fakeAuthenticator{principal: authapp.Principal{UserID: "student-1", Role: user.RoleStudent}}
	handler := newTeacherTestHandler(t, &fakeTeacherService{}, auth)
	mux := http.NewServeMux()
	handler.Register(mux, "/api/v1/teacher")

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodGet, "/api/v1/teacher/students/stats", nil)
	request.Header.Set("Authorization", "Bearer token")
	mux.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusForbidden {
		t.Fatalf("status = %d", recorder.Code)
	}
}

func TestStudentsListParsesPaginationAndFilters(t *testing.T) {
	service := &fakeTeacherService{studentsListResponse: teacherapp.StudentListResponse{Items: []teacherapp.StudentListItem{{ID: "student-1"}}, Total: 1, Page: 2, PageSize: 10, TotalPages: 1}}
	auth := &fakeAuthenticator{principal: authapp.Principal{UserID: "teacher-1", Role: user.RoleTeacher}}
	handler := newTeacherTestHandler(t, service, auth)
	mux := http.NewServeMux()
	handler.Register(mux, "/api/v1/teacher")

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodGet, "/api/v1/teacher/students?page=2&page_size=10&class_id=class-1&search=zhang", nil)
	request.Header.Set("Authorization", "Bearer token")
	mux.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("status = %d body=%s", recorder.Code, recorder.Body.String())
	}
	if service.lastTeacherID != "teacher-1" || service.lastStudentFilter.Page != 2 || service.lastStudentFilter.PageSize != 10 || service.lastStudentFilter.ClassID != "class-1" || service.lastStudentFilter.Search != "zhang" {
		t.Fatalf("teacher=%q filter=%#v", service.lastTeacherID, service.lastStudentFilter)
	}
}

func TestAnalyticsValidatesTimeRange(t *testing.T) {
	auth := &fakeAuthenticator{principal: authapp.Principal{UserID: "teacher-1", Role: user.RoleTeacher}}
	handler := newTeacherTestHandler(t, &fakeTeacherService{}, auth)
	mux := http.NewServeMux()
	handler.Register(mux, "/api/v1/teacher")

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodGet, "/api/v1/teacher/analytics?time_range=bad", nil)
	request.Header.Set("Authorization", "Bearer token")
	mux.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusUnprocessableEntity {
		t.Fatalf("status = %d body=%s", recorder.Code, recorder.Body.String())
	}
}

func TestTeacherRoutesForwardIDs(t *testing.T) {
	service := &fakeTeacherService{
		classResponse:   teacherapp.ClassAnalyticsResponse{},
		studentResponse: teacherapp.StudentDetailResponse{},
	}
	auth := &fakeAuthenticator{principal: authapp.Principal{UserID: "teacher-1", Role: user.RoleTeacher}}
	handler := newTeacherTestHandler(t, service, auth)
	mux := http.NewServeMux()
	handler.Register(mux, "/api/v1/teacher")

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodGet, "/api/v1/teacher/classes/class-1/analytics", nil)
	request.Header.Set("Authorization", "Bearer token")
	mux.ServeHTTP(recorder, request)
	if recorder.Code != http.StatusOK || service.lastTeacherID != "teacher-1" || service.lastClassID != "class-1" {
		t.Fatalf("class status=%d teacher=%q class=%q", recorder.Code, service.lastTeacherID, service.lastClassID)
	}

	recorder = httptest.NewRecorder()
	request = httptest.NewRequest(http.MethodGet, "/api/v1/teacher/students/student-1/detail", nil)
	request.Header.Set("Authorization", "Bearer token")
	mux.ServeHTTP(recorder, request)
	if recorder.Code != http.StatusOK || service.lastStudentID != "student-1" {
		t.Fatalf("student status=%d student=%q", recorder.Code, service.lastStudentID)
	}
}

func TestStudentDetailMapsMissingStudentAccount(t *testing.T) {
	service := &fakeTeacherService{studentErr: teacherapp.ErrStudentNotFound}
	auth := &fakeAuthenticator{principal: authapp.Principal{UserID: "teacher-1", Role: user.RoleTeacher}}
	handler := newTeacherTestHandler(t, service, auth)
	mux := http.NewServeMux()
	handler.Register(mux, "/api/v1/teacher")

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodGet, "/api/v1/teacher/students/student-1/detail", nil)
	request.Header.Set("Authorization", "Bearer token")
	mux.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusNotFound {
		t.Fatalf("status = %d, body = %s", recorder.Code, recorder.Body.String())
	}
	var body map[string]string
	if err := json.Unmarshal(recorder.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}
	if body["message"] != "学生不存在" {
		t.Fatalf("message = %q", body["message"])
	}
}

func TestInternalErrorsRedactLogs(t *testing.T) {
	credentialErr := errors.New("teacher repo failed Authorization: Bearer teacher-secret token=query-token api_key=plain password=letmein")
	tests := []struct {
		name    string
		path    string
		service fakeTeacherService
	}{
		{
			name:    "dashboard stats",
			path:    "/api/v1/teacher/dashboard/stats",
			service: fakeTeacherService{dashboardErr: credentialErr},
		},
		{
			name:    "students stats",
			path:    "/api/v1/teacher/students/stats",
			service: fakeTeacherService{studentsErr: credentialErr},
		},
		{
			name:    "students list",
			path:    "/api/v1/teacher/students",
			service: fakeTeacherService{studentsErr: credentialErr},
		},
		{
			name:    "analytics",
			path:    "/api/v1/teacher/analytics",
			service: fakeTeacherService{analyticsErr: credentialErr},
		},
		{
			name:    "class analytics",
			path:    "/api/v1/teacher/classes/class-1/analytics",
			service: fakeTeacherService{classErr: credentialErr},
		},
		{
			name:    "student detail",
			path:    "/api/v1/teacher/students/student-1/detail",
			service: fakeTeacherService{studentErr: credentialErr},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var logBuffer bytes.Buffer
			service := tt.service
			handler, err := NewHandler(slog.New(slog.NewTextHandler(&logBuffer, nil)), &service, &fakeAuthenticator{principal: authapp.Principal{UserID: "teacher-1", Role: user.RoleTeacher}})
			if err != nil {
				t.Fatalf("NewHandler() error = %v", err)
			}
			mux := http.NewServeMux()
			handler.Register(mux, "/api/v1/teacher")

			recorder := httptest.NewRecorder()
			request := httptest.NewRequest(http.MethodGet, tt.path, nil)
			request.Header.Set("Authorization", "Bearer token")
			mux.ServeHTTP(recorder, request)

			if recorder.Code != http.StatusInternalServerError {
				t.Fatalf("status = %d, body = %s", recorder.Code, recorder.Body.String())
			}
			if logBuffer.Len() == 0 {
				t.Fatal("expected internal error log")
			}
			assertNoTeacherCredentialLeak(t, recorder.Body.String())
			assertNoTeacherCredentialLeak(t, logBuffer.String())
		})
	}
}

func TestNewHandlerRejectsMissingDependencies(t *testing.T) {
	if _, err := NewHandler(nil, nil, &fakeAuthenticator{}); err == nil {
		t.Fatal("NewHandler(nil service) error = nil, want error")
	}
	if _, err := NewHandler(nil, &fakeTeacherService{}, nil); err == nil {
		t.Fatal("NewHandler(nil auth) error = nil, want error")
	}
}

func newTeacherTestHandler(t *testing.T, service Service, auth Authenticator) *Handler {
	t.Helper()
	handler, err := NewHandler(slog.New(slog.NewTextHandler(os.Stdout, nil)), service, auth)
	if err != nil {
		t.Fatalf("NewHandler() error = %v", err)
	}
	return handler
}

func assertNoTeacherCredentialLeak(t *testing.T, value string) {
	t.Helper()
	for _, leaked := range []string{"teacher-secret", "token=query-token", "api_key=plain", "password=letmein", "Bearer teacher-secret"} {
		if strings.Contains(value, leaked) {
			t.Fatalf("value leaked %q in %q", leaked, value)
		}
	}
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

type fakeTeacherService struct {
	dashboardResponse    teacherapp.DashboardStats
	studentsResponse     teacherapp.StudentsStats
	studentsListResponse teacherapp.StudentListResponse
	analyticsResponse    teacherapp.AnalyticsResponse
	classResponse        teacherapp.ClassAnalyticsResponse
	studentResponse      teacherapp.StudentDetailResponse
	dashboardErr         error
	studentsErr          error
	analyticsErr         error
	classErr             error
	studentErr           error
	lastTeacherID        string
	lastTimeRange        string
	lastClassID          string
	lastStudentID        string
	lastStudentFilter    teacherapp.StudentListFilter
}

func (s *fakeTeacherService) GetDashboardStats(_ context.Context, teacherID string) (teacherapp.DashboardStats, error) {
	s.lastTeacherID = teacherID
	return s.dashboardResponse, s.dashboardErr
}

func (s *fakeTeacherService) GetStudentsStats(_ context.Context, teacherID string) (teacherapp.StudentsStats, error) {
	s.lastTeacherID = teacherID
	return s.studentsResponse, s.studentsErr
}

func (s *fakeTeacherService) ListStudents(_ context.Context, teacherID string, filter teacherapp.StudentListFilter) (teacherapp.StudentListResponse, error) {
	s.lastTeacherID = teacherID
	s.lastStudentFilter = filter
	return s.studentsListResponse, s.studentsErr
}

func (s *fakeTeacherService) GetAnalytics(_ context.Context, teacherID string, timeRange string) (teacherapp.AnalyticsResponse, error) {
	s.lastTeacherID = teacherID
	s.lastTimeRange = timeRange
	return s.analyticsResponse, s.analyticsErr
}

func (s *fakeTeacherService) GetClassAnalytics(_ context.Context, teacherID string, classID string) (teacherapp.ClassAnalyticsResponse, error) {
	s.lastTeacherID = teacherID
	s.lastClassID = classID
	return s.classResponse, s.classErr
}

func (s *fakeTeacherService) GetStudentDetail(_ context.Context, teacherID string, studentID string) (teacherapp.StudentDetailResponse, error) {
	s.lastTeacherID = teacherID
	s.lastStudentID = studentID
	return s.studentResponse, s.studentErr
}
