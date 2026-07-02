package securitylog

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"strings"
	"testing"
	"time"

	"mathstudy/backend-go/internal/platform/redact"
)

func TestNewServiceRejectsNilRepository(t *testing.T) {
	if _, err := NewService(nil, CleanupConfig{}); err == nil {
		t.Fatal("NewService(nil) error = nil, want error")
	}
}

func TestListLogsNormalizesAndGroups(t *testing.T) {
	repo := &fakeRepository{logs: []LogItem{
		{ID: "1", EventType: EventLoginFailed, Severity: SeverityWarning, CreatedAt: time.Date(2026, 5, 3, 10, 0, 0, 0, time.UTC)},
		{ID: "2", EventType: EventServiceError, Severity: SeverityError, CreatedAt: time.Date(2026, 5, 2, 10, 0, 0, 0, time.UTC)},
	}, total: 3}
	service := newTestService(t, repo)

	response, err := service.ListLogs(context.Background(), QueryFilter{Page: 1, PageSize: 2})
	if err != nil {
		t.Fatalf("ListLogs() error = %v", err)
	}
	if response.Total != 3 || !response.HasMore || len(response.Groups) != 2 || response.Groups[0].DateDisplay != "今天" || response.Groups[1].DateDisplay != "昨天" {
		t.Fatalf("response = %#v", response)
	}

	_, err = service.ListLogs(context.Background(), QueryFilter{EventTypes: []EventType{"bad"}})
	if !errors.Is(err, ErrBadRequest) {
		t.Fatalf("ListLogs(invalid) error = %v, want ErrBadRequest", err)
	}
}

func TestExportLogsBuildsJSONAndCSV(t *testing.T) {
	ipAddress := "203.0.113.10"
	repo := &fakeRepository{logs: []LogItem{{
		ID:          "log-1",
		EventType:   EventDailyReport,
		Severity:    SeverityInfo,
		Title:       "=每日安全报告",
		Description: "@正常 Authorization: Bearer secret-token callback=/done?token=abc",
		IPAddress:   &ipAddress,
		Username:    stringPtr("+admin api_key=plain"),
		ExtraData: map[string]any{
			"date":    "2026-05-03",
			"api_key": "secret",
			"nested":  map[string]any{"refresh_token": "rt", "safe": "ok"},
		},
		CreatedAt: time.Date(2026, 5, 3, 12, 0, 0, 0, time.UTC),
	}}}
	service := newTestService(t, repo)

	response, err := service.ExportLogs(context.Background(), ExportRequest{Format: "json"})
	if err != nil {
		t.Fatalf("ExportLogs(json) error = %v", err)
	}
	if response.Filename != "security_logs_20260503_120000.json" || response.RecordCount != 1 || response.ContentType != "application/json" {
		t.Fatalf("response = %#v", response)
	}
	decoded, _ := base64.StdEncoding.DecodeString(response.Content)
	if !strings.Contains(string(decoded), "每日安全报告") {
		t.Fatalf("decoded = %s", decoded)
	}
	for _, leaked := range []string{"secret-token", "token=abc", "plain", "203.0.113.10", "\"rt\""} {
		if strings.Contains(string(decoded), leaked) {
			t.Fatalf("json export leaked %q in %s", leaked, decoded)
		}
	}
	var rows []map[string]any
	if err := json.Unmarshal(decoded, &rows); err != nil {
		t.Fatalf("json export invalid: %v", err)
	}
	if rows[0]["ip_address"] != redact.Marker {
		t.Fatalf("ip_address = %#v, want redacted", rows[0]["ip_address"])
	}
	extra := rows[0]["extra_data"].(map[string]any)
	if extra["date"] != "2026-05-03" || extra["api_key"] != redact.Marker {
		t.Fatalf("extra_data = %#v", extra)
	}
	nested := extra["nested"].(map[string]any)
	if nested["refresh_token"] != redact.Marker || nested["safe"] != "ok" {
		t.Fatalf("nested = %#v", nested)
	}

	response, err = service.ExportLogs(context.Background(), ExportRequest{Format: "csv"})
	if err != nil {
		t.Fatalf("ExportLogs(csv) error = %v", err)
	}
	decoded, _ = base64.StdEncoding.DecodeString(response.Content)
	if response.ContentType != "text/csv" || !strings.Contains(string(decoded), "'=每日安全报告") || !strings.Contains(string(decoded), "'@正常") || !strings.Contains(string(decoded), "'+admin") {
		t.Fatalf("response=%#v decoded=%s", response, decoded)
	}
	for _, leaked := range []string{"secret-token", "token=abc", "api_key=plain", "203.0.113.10"} {
		if strings.Contains(string(decoded), leaked) {
			t.Fatalf("csv export leaked %q in %s", leaked, decoded)
		}
	}
}

func TestGenerateDailyReport(t *testing.T) {
	repo := &fakeRepository{}
	service := newTestService(t, repo)

	response, err := service.GenerateDailyReport(context.Background())
	if err != nil {
		t.Fatalf("GenerateDailyReport() error = %v", err)
	}
	if !response.Generated || response.ReportID == nil || *response.ReportID != "report-1" {
		t.Fatalf("response = %#v", response)
	}
	if repo.created.EventType != EventDailyReport || repo.created.ExtraData["date"] != "2026-05-03" {
		t.Fatalf("created = %#v", repo.created)
	}

	repo.hasDailyReport = true
	response, err = service.GenerateDailyReport(context.Background())
	if err != nil {
		t.Fatalf("GenerateDailyReport(existing) error = %v", err)
	}
	if response.Generated || response.Message == nil {
		t.Fatalf("response = %#v", response)
	}
}

func TestCleanupAndVolume(t *testing.T) {
	repo := &fakeRepository{volume: VolumeResponse{ActiveCount: 80, ArchivedCount: 30}}
	service := newTestService(t, repo)
	service.config = CleanupConfig{ArchiveAfterDays: 30, DeleteAfterDays: 90, BatchSize: 25, MaxLogCount: 100}

	response, err := service.Cleanup(context.Background())
	if err != nil {
		t.Fatalf("Cleanup() error = %v", err)
	}
	if response.ArchivedCount != 2 || response.DeletedCount != 1 || !response.Volume.Exceeded || repo.archiveBatch != 25 || repo.deleteBatch != 25 {
		t.Fatalf("response=%#v repo=%#v", response, repo)
	}
}

func newTestService(t *testing.T, repo *fakeRepository) *Service {
	t.Helper()
	service, err := NewService(repo, CleanupConfig{MaxLogCount: 100})
	if err != nil {
		t.Fatalf("NewService() error = %v", err)
	}
	service.now = func() time.Time { return time.Date(2026, 5, 3, 12, 0, 0, 0, time.UTC) }
	return service
}

func stringPtr(value string) *string {
	return &value
}

type fakeRepository struct {
	logs           []LogItem
	total          int
	stats          StatsResponse
	created        CreateLog
	hasDailyReport bool
	abnormalCount  int
	volume         VolumeResponse
	archiveBatch   int
	deleteBatch    int
}

func (r *fakeRepository) ListLogs(context.Context, QueryFilter) ([]LogItem, int, error) {
	return r.logs, r.total, nil
}

func (r *fakeRepository) Stats(context.Context) (StatsResponse, error) {
	return r.stats, nil
}

func (r *fakeRepository) DeleteLogs(context.Context, DeleteRequest) (int, error) {
	return 3, nil
}

func (r *fakeRepository) ExportLogs(context.Context, ExportRequest) ([]LogItem, error) {
	return r.logs, nil
}

func (r *fakeRepository) ArchiveLogs(context.Context, time.Time) (int, error) {
	return 4, nil
}

func (r *fakeRepository) DailyReportStatus(context.Context, time.Time, time.Time) (bool, int, error) {
	return r.hasDailyReport, r.abnormalCount, nil
}

func (r *fakeRepository) CreateLog(_ context.Context, create CreateLog) (LogItem, error) {
	r.created = create
	return LogItem{ID: "report-1", EventType: create.EventType, Severity: create.Severity, CreatedAt: create.CreatedAt}, nil
}

func (r *fakeRepository) AutoArchive(_ context.Context, _ time.Time, batchSize int) (int, error) {
	r.archiveBatch = batchSize
	return 2, nil
}

func (r *fakeRepository) AutoDelete(_ context.Context, _ time.Time, batchSize int) (int, error) {
	r.deleteBatch = batchSize
	return 1, nil
}

func (r *fakeRepository) Volume(context.Context) (VolumeResponse, error) {
	return r.volume, nil
}
