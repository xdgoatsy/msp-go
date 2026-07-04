package httpquery

import (
	"errors"
	"testing"
	"time"
)

func TestOptionalTime(t *testing.T) {
	value, err := OptionalTime("", time.RFC3339)
	if err != nil {
		t.Fatalf("OptionalTime(empty) error = %v", err)
	}
	if value != nil {
		t.Fatalf("OptionalTime(empty) = %#v, want nil", value)
	}

	value, err = OptionalTime(" 2026-05-01T12:30:00Z ", time.RFC3339)
	if err != nil {
		t.Fatalf("OptionalTime(RFC3339) error = %v", err)
	}
	if value == nil || value.UTC().Format(time.RFC3339) != "2026-05-01T12:30:00Z" {
		t.Fatalf("OptionalTime(RFC3339) = %#v", value)
	}

	value, err = OptionalTime("2026-05-01", time.RFC3339, "2006-01-02")
	if err != nil {
		t.Fatalf("OptionalTime(date) error = %v", err)
	}
	if value == nil || value.Format("2006-01-02") != "2026-05-01" {
		t.Fatalf("OptionalTime(date) = %#v", value)
	}

	if _, err = OptionalTime("not-a-date", time.RFC3339, "2006-01-02"); !errors.Is(err, ErrInvalidTime) {
		t.Fatalf("OptionalTime(invalid) error = %v, want ErrInvalidTime", err)
	}
}
