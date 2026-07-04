package stringutil

import "testing"

func TestNonBlankOr(t *testing.T) {
	tests := []struct {
		name     string
		value    string
		fallback string
		want     string
	}{
		{name: "empty", value: "", fallback: "fallback", want: "fallback"},
		{name: "whitespace", value: " \t\n", fallback: "fallback", want: "fallback"},
		{name: "preserves non blank value", value: " value ", fallback: "fallback", want: " value "},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := NonBlankOr(tt.value, tt.fallback); got != tt.want {
				t.Fatalf("NonBlankOr() = %q, want %q", got, tt.want)
			}
		})
	}
}
