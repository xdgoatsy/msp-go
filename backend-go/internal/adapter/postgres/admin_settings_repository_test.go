package postgres

import (
	"context"
	"strings"
	"testing"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"

	"mathstudy/backend-go/internal/platform/redact"
)

func TestFilterImportRowRemovesSensitiveAndUnsafeColumns(t *testing.T) {
	filtered := filterImportRow("system_settings", map[string]any{
		"key":             "system_name",
		"value":           "App",
		"hashed_password": "secret",
		"bad-column":      "ignored",
	})

	if filtered["key"] != "system_name" || filtered["value"] != "App" {
		t.Fatalf("filterImportRow() = %#v", filtered)
	}
	if _, ok := filtered["hashed_password"]; ok {
		t.Fatalf("filterImportRow kept hashed_password: %#v", filtered)
	}
	if _, ok := filtered["bad-column"]; ok {
		t.Fatalf("filterImportRow kept unsafe column: %#v", filtered)
	}
}

func TestFilterImportRowNormalizesNonAdminUsers(t *testing.T) {
	filtered := filterImportRow("users", map[string]any{
		"id":        "user-1",
		"username":  "teacher",
		"role":      "teacher",
		"status":    "suspended",
		"is_active": true,
	})

	if filtered["role"] != "TEACHER" {
		t.Fatalf("role = %#v, want TEACHER", filtered["role"])
	}
	if filtered["status"] != "SUSPENDED" {
		t.Fatalf("status = %#v, want SUSPENDED", filtered["status"])
	}
	if filtered["is_active"] != false {
		t.Fatalf("is_active = %#v, want false for suspended status", filtered["is_active"])
	}
}

func TestFilterImportRowSkipsAdminAndInvalidUsers(t *testing.T) {
	tests := map[string]map[string]any{
		"admin api role": {"id": "admin-1", "role": "admin", "status": "active"},
		"admin db role":  {"id": "admin-1", "role": "ADMIN", "status": "ACTIVE"},
		"invalid role":   {"id": "user-1", "role": "owner", "status": "active"},
		"invalid status": {"id": "user-1", "role": "student", "status": "locked"},
		"missing role":   {"id": "user-1", "status": "active"},
		"missing status": {"id": "user-1", "role": "student"},
	}

	for name, row := range tests {
		t.Run(name, func(t *testing.T) {
			filtered := filterImportRow("users", row)
			if len(filtered) != 0 {
				t.Fatalf("filterImportRow(%s) = %#v, want skipped row", name, filtered)
			}
		})
	}
}

func TestNormalizeExportValueRedactsSensitiveNestedData(t *testing.T) {
	value := normalizeExportValue("metadata", []byte(`{
		"request_id":"req-1",
		"authorization":"Bearer token",
		"nested":{"api_key":"secret","safe":"ok"},
		"items":[{"refresh_token":"rt","count":1}]
	}`))

	metadata, ok := value.(map[string]any)
	if !ok {
		t.Fatalf("normalizeExportValue() = %#v", value)
	}
	if metadata["request_id"] != "req-1" {
		t.Fatalf("request_id = %#v", metadata["request_id"])
	}
	if metadata["authorization"] != redact.Marker {
		t.Fatalf("authorization = %#v, want redacted", metadata["authorization"])
	}
	nested := metadata["nested"].(map[string]any)
	if nested["api_key"] != redact.Marker || nested["safe"] != "ok" {
		t.Fatalf("nested = %#v", nested)
	}
	items := metadata["items"].([]any)
	first := items[0].(map[string]any)
	if first["refresh_token"] != redact.Marker || first["count"] != float64(1) {
		t.Fatalf("items = %#v", items)
	}
}

func TestNormalizeExportValueRedactsSensitiveStrings(t *testing.T) {
	value := normalizeExportValue("description", "Authorization: Bearer secret-token url=/callback?token=abc api_key=plain eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.signature")
	text, ok := value.(string)
	if !ok {
		t.Fatalf("normalizeExportValue() = %#v", value)
	}
	for _, leaked := range []string{"secret-token", "token=abc", "api_key=plain", "eyJhbGci"} {
		if strings.Contains(text, leaked) {
			t.Fatalf("sanitized string leaked %q in %q", leaked, text)
		}
	}
	if !strings.Contains(text, redact.Marker) {
		t.Fatalf("sanitized string = %q, want redaction marker", text)
	}
}

func TestShouldOmitExportFieldDropsSecurityLogIP(t *testing.T) {
	if !shouldOmitExportField("security_logs", "ip_address") {
		t.Fatal("security_logs.ip_address should be omitted from database backups")
	}
	if shouldOmitExportField("users", "email") {
		t.Fatal("users.email should remain exportable")
	}
}

func TestExportTableExcludesAdminUsers(t *testing.T) {
	querier := &capturingQuerier{rows: emptyRows{}}
	repo, err := NewAdminSettingsRepository(querier)
	if err != nil {
		t.Fatalf("NewAdminSettingsRepository() error = %v", err)
	}

	if _, err := repo.ExportTable(context.Background(), "users"); err != nil {
		t.Fatalf("ExportTable(users) error = %v", err)
	}
	if !strings.Contains(querier.query, "role <> 'ADMIN'::public.userrole") {
		t.Fatalf("query = %q, want admin exclusion", querier.query)
	}
}

type capturingQuerier struct {
	query string
	rows  pgx.Rows
}

func (q *capturingQuerier) Exec(context.Context, string, ...any) (pgconn.CommandTag, error) {
	return pgconn.CommandTag{}, nil
}

func (q *capturingQuerier) Query(_ context.Context, query string, _ ...any) (pgx.Rows, error) {
	q.query = query
	return q.rows, nil
}

func (q *capturingQuerier) QueryRow(context.Context, string, ...any) pgx.Row {
	return nil
}

type emptyRows struct{}

func (emptyRows) Close() {}

func (emptyRows) Err() error {
	return nil
}

func (emptyRows) CommandTag() pgconn.CommandTag {
	return pgconn.CommandTag{}
}

func (emptyRows) FieldDescriptions() []pgconn.FieldDescription {
	return nil
}

func (emptyRows) Next() bool {
	return false
}

func (emptyRows) Scan(...any) error {
	return nil
}

func (emptyRows) Values() ([]any, error) {
	return nil, nil
}

func (emptyRows) RawValues() [][]byte {
	return nil
}

func (emptyRows) Conn() *pgx.Conn {
	return nil
}
