package httpvalidate

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

type recordedError struct {
	status  int
	code    string
	message string
}

func captureError(slot *recordedError) ErrorWriter {
	return func(w http.ResponseWriter, status int, code, message string) {
		slot.status = status
		slot.code = code
		slot.message = message
		w.WriteHeader(status)
	}
}

func TestRequiredTrimmedString(t *testing.T) {
	tests := []struct {
		name        string
		value       string
		min         int
		max         int
		wantOK      bool
		wantMessage string
	}{
		{name: "valid", value: " ok ", min: 1, max: 2, wantOK: true},
		{name: "empty after trim", value: "  ", min: 1, max: 20, wantMessage: "field 不能为空"},
		{name: "too long after trim", value: "abcd", min: 1, max: 3, wantMessage: "field 长度超出限制"},
		{name: "max zero skips upper bound", value: "abcd", min: 1, max: 0, wantOK: true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var got recordedError
			ok := RequiredTrimmedString(httptest.NewRecorder(), tt.value, tt.min, tt.max, "field", captureError(&got))
			if ok != tt.wantOK {
				t.Fatalf("ok = %v, want %v", ok, tt.wantOK)
			}
			if tt.wantOK {
				if got != (recordedError{}) {
					t.Fatalf("unexpected error: %+v", got)
				}
				return
			}
			assertValidationError(t, got, tt.wantMessage)
		})
	}
}

func TestStringLength(t *testing.T) {
	var got recordedError
	if !StringLength(httptest.NewRecorder(), "abc", 3, "field", captureError(&got)) {
		t.Fatal("expected exact max length to pass")
	}
	if got != (recordedError{}) {
		t.Fatalf("unexpected error: %+v", got)
	}

	if StringLength(httptest.NewRecorder(), "abcd", 3, "field", captureError(&got)) {
		t.Fatal("expected too long value to fail")
	}
	assertValidationError(t, got, "field 长度超出限制")
}

func TestOptionalString(t *testing.T) {
	var got recordedError
	if !OptionalString(httptest.NewRecorder(), nil, 3, "field", captureError(&got)) {
		t.Fatal("expected nil optional string to pass")
	}

	value := "abcd"
	if OptionalString(httptest.NewRecorder(), &value, 3, "field", captureError(&got)) {
		t.Fatal("expected too long optional string to fail")
	}
	assertValidationError(t, got, "field 长度超出限制")
}

func TestOptionalRequiredTrimmedString(t *testing.T) {
	var got recordedError
	if !OptionalRequiredTrimmedString(httptest.NewRecorder(), nil, 1, 3, "field", captureError(&got)) {
		t.Fatal("expected nil optional required string to pass")
	}

	value := " "
	if OptionalRequiredTrimmedString(httptest.NewRecorder(), &value, 1, 3, "field", captureError(&got)) {
		t.Fatal("expected blank present string to fail")
	}
	assertValidationError(t, got, "field 不能为空")
}

func TestRequiredField(t *testing.T) {
	var got recordedError
	value := "present"
	if !RequiredField(httptest.NewRecorder(), &value, "field", captureError(&got)) {
		t.Fatal("expected present field to pass")
	}

	if RequiredField[string](httptest.NewRecorder(), nil, "field", captureError(&got)) {
		t.Fatal("expected nil field to fail")
	}
	assertValidationError(t, got, "field 为必填字段")
}

func TestStringSlice(t *testing.T) {
	tests := []struct {
		name        string
		values      []string
		maxItems    int
		maxBytes    int
		wantOK      bool
		wantMessage string
	}{
		{name: "valid", values: []string{" one ", "two"}, maxItems: 2, maxBytes: 3, wantOK: true},
		{name: "too many items", values: []string{"one", "two"}, maxItems: 1, maxBytes: 3, wantMessage: "items 数量超出限制"},
		{name: "trimmed item too long", values: []string{"long"}, maxItems: 2, maxBytes: 3, wantMessage: "items 单项长度超出限制"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var got recordedError
			ok := StringSlice(httptest.NewRecorder(), tt.values, tt.maxItems, tt.maxBytes, "items", captureError(&got))
			if ok != tt.wantOK {
				t.Fatalf("ok = %v, want %v", ok, tt.wantOK)
			}
			if tt.wantOK {
				return
			}
			assertValidationError(t, got, tt.wantMessage)
		})
	}
}

func TestOptionalStringSlice(t *testing.T) {
	var got recordedError
	if !OptionalStringSlice(httptest.NewRecorder(), nil, 1, 3, "items", captureError(&got)) {
		t.Fatal("expected nil optional slice to pass")
	}

	values := []string{"one", "two"}
	if OptionalStringSlice(httptest.NewRecorder(), &values, 1, 3, "items", captureError(&got)) {
		t.Fatal("expected present invalid slice to fail")
	}
	assertValidationError(t, got, "items 数量超出限制")
}

func assertValidationError(t *testing.T, got recordedError, wantMessage string) {
	t.Helper()
	if got.status != http.StatusUnprocessableEntity {
		t.Fatalf("status = %d, want %d", got.status, http.StatusUnprocessableEntity)
	}
	if got.code != validationErrorCode {
		t.Fatalf("code = %q, want %q", got.code, validationErrorCode)
	}
	if got.message != wantMessage {
		t.Fatalf("message = %q, want %q", got.message, wantMessage)
	}
}
