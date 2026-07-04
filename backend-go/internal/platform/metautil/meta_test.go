package metautil

import "testing"

func TestLookupString(t *testing.T) {
	tests := []struct {
		name   string
		meta   map[string]any
		want   string
		wantOK bool
	}{
		{name: "nil meta", meta: nil},
		{name: "missing key", meta: map[string]any{}},
		{name: "nil value", meta: map[string]any{"field": nil}},
		{name: "non string", meta: map[string]any{"field": 42}},
		{name: "string", meta: map[string]any{"field": "value"}, want: "value", wantOK: true},
		{name: "empty string is present", meta: map[string]any{"field": ""}, wantOK: true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, ok := LookupString(tt.meta, "field")
			if got != tt.want || ok != tt.wantOK {
				t.Fatalf("LookupString() = %q, %v; want %q, %v", got, ok, tt.want, tt.wantOK)
			}
		})
	}
}

func TestString(t *testing.T) {
	if got := String(map[string]any{"field": "value"}, "field"); got != "value" {
		t.Fatalf("String() = %q, want value", got)
	}
	if got := String(map[string]any{"field": 42}, "field"); got != "" {
		t.Fatalf("String() = %q, want empty", got)
	}
}

func TestStringPointer(t *testing.T) {
	if got := StringPointer(map[string]any{}, "field"); got != nil {
		t.Fatalf("StringPointer() = %v, want nil", got)
	}
	got := StringPointer(map[string]any{"field": "value"}, "field")
	if got == nil || *got != "value" {
		t.Fatalf("StringPointer() = %v, want value", got)
	}
}

func TestLookupStringSlice(t *testing.T) {
	tests := []struct {
		name   string
		meta   map[string]any
		want   []string
		wantOK bool
	}{
		{name: "nil meta", meta: nil},
		{name: "missing key", meta: map[string]any{}},
		{name: "nil value", meta: map[string]any{"items": nil}},
		{name: "non slice", meta: map[string]any{"items": "one"}},
		{name: "string slice", meta: map[string]any{"items": []string{"one", "two"}}, want: []string{"one", "two"}, wantOK: true},
		{name: "any slice filters strings", meta: map[string]any{"items": []any{"one", 2, "two"}}, want: []string{"one", "two"}, wantOK: true},
		{name: "empty any slice is present", meta: map[string]any{"items": []any{}}, want: []string{}, wantOK: true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, ok := LookupStringSlice(tt.meta, "items")
			if ok != tt.wantOK {
				t.Fatalf("ok = %v, want %v", ok, tt.wantOK)
			}
			assertStrings(t, got, tt.want)
			if ok && len(got) > 0 {
				got[0] = "changed"
				again, _ := LookupStringSlice(tt.meta, "items")
				if again[0] == "changed" {
					t.Fatal("LookupStringSlice returned slice sharing backing storage")
				}
			}
		})
	}
}

func TestStringSlice(t *testing.T) {
	got := StringSlice(map[string]any{"items": []any{"one"}}, "items")
	assertStrings(t, got, []string{"one"})

	got = StringSlice(map[string]any{"items": 42}, "items")
	if got == nil || len(got) != 0 {
		t.Fatalf("StringSlice() = %#v, want non-nil empty slice", got)
	}
}

func TestOptionalStringSlice(t *testing.T) {
	if got := OptionalStringSlice(map[string]any{}, "items"); got != nil {
		t.Fatalf("OptionalStringSlice() = %#v, want nil", got)
	}
	got := OptionalStringSlice(map[string]any{"items": []any{}}, "items")
	if got == nil || len(got) != 0 {
		t.Fatalf("OptionalStringSlice() = %#v, want non-nil empty slice for present value", got)
	}
}

func assertStrings(t *testing.T, got []string, want []string) {
	t.Helper()
	if len(got) != len(want) {
		t.Fatalf("len = %d, want %d: %#v", len(got), len(want), got)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("got[%d] = %q, want %q", i, got[i], want[i])
		}
	}
}
