package httpauth

import (
	"net/http/httptest"
	"testing"
)

func TestBearerToken(t *testing.T) {
	tests := []struct {
		name   string
		header string
		want   string
		ok     bool
	}{
		{name: "missing"},
		{name: "bearer", header: "Bearer token-1", want: "token-1", ok: true},
		{name: "case insensitive scheme", header: "bearer token-2", want: "token-2", ok: true},
		{name: "extra whitespace", header: "  Bearer   token-3  ", want: "token-3", ok: true},
		{name: "wrong scheme", header: "Basic token-4"},
		{name: "missing token", header: "Bearer"},
		{name: "too many fields", header: "Bearer token-5 extra"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			request := httptest.NewRequest("GET", "/", nil)
			if tt.header != "" {
				request.Header.Set("Authorization", tt.header)
			}
			got, ok := BearerToken(request)
			if ok != tt.ok || got != tt.want {
				t.Fatalf("BearerToken() = %q, %t; want %q, %t", got, ok, tt.want, tt.ok)
			}
		})
	}
}
