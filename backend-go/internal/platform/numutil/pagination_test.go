package numutil

import "testing"

func TestTotalPages(t *testing.T) {
	tests := []struct {
		name     string
		total    int
		pageSize int
		want     int
	}{
		{name: "exact page", total: 20, pageSize: 10, want: 2},
		{name: "partial page", total: 21, pageSize: 10, want: 3},
		{name: "zero total", total: 0, pageSize: 10, want: 0},
		{name: "negative total", total: -1, pageSize: 10, want: 0},
		{name: "zero page size", total: 10, pageSize: 0, want: 0},
		{name: "negative page size", total: 10, pageSize: -1, want: 0},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := TotalPages(tt.total, tt.pageSize); got != tt.want {
				t.Fatalf("TotalPages(%d, %d) = %d, want %d", tt.total, tt.pageSize, got, tt.want)
			}
		})
	}
}
