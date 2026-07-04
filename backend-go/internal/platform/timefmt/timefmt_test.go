package timefmt

import (
	"testing"
	"time"
)

func TestDate(t *testing.T) {
	value := time.Date(2026, 7, 4, 15, 30, 45, 123456789, time.FixedZone("CST", 8*60*60))
	if got := Date(value); got != "2026-07-04" {
		t.Fatalf("Date() = %q, want 2026-07-04", got)
	}
}

func TestStartOfDay(t *testing.T) {
	location := time.FixedZone("CST", 8*60*60)
	value := time.Date(2026, 7, 4, 15, 30, 45, 123456789, location)
	got := StartOfDay(value)
	want := time.Date(2026, 7, 4, 0, 0, 0, 0, location)
	if !got.Equal(want) {
		t.Fatalf("StartOfDay() = %v, want %v", got, want)
	}
	if got.Location() != location {
		t.Fatalf("StartOfDay() location = %v, want original location", got.Location())
	}
}

func TestDateTimeMicros(t *testing.T) {
	value := time.Date(2026, 7, 4, 15, 30, 45, 123456789, time.FixedZone("CST", 8*60*60))
	if got := DateTimeMicros(value); got != "2026-07-04T15:30:45.123456" {
		t.Fatalf("DateTimeMicros() = %q, want 2026-07-04T15:30:45.123456", got)
	}
}

func TestOptionalDateTimeMicros(t *testing.T) {
	if got := OptionalDateTimeMicros(nil); got != nil {
		t.Fatalf("OptionalDateTimeMicros(nil) = %v, want nil", got)
	}

	value := time.Date(2026, 7, 4, 15, 30, 45, 123456789, time.UTC)
	got := OptionalDateTimeMicros(&value)
	if got == nil || *got != "2026-07-04T15:30:45.123456" {
		t.Fatalf("OptionalDateTimeMicros() = %v, want 2026-07-04T15:30:45.123456", got)
	}
}
