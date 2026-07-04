package numutil

import "testing"

func TestRoundPlaces(t *testing.T) {
	tests := []struct {
		name   string
		value  float64
		places int
		want   float64
	}{
		{name: "one place rounds up", value: 12.35, places: 1, want: 12.4},
		{name: "two places rounds down", value: 12.344, places: 2, want: 12.34},
		{name: "four places", value: 0.123456, places: 4, want: 0.1235},
		{name: "negative value", value: -1.25, places: 1, want: -1.3},
		{name: "zero places", value: 1.5, places: 0, want: 2},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := RoundPlaces(tt.value, tt.places); got != tt.want {
				t.Fatalf("RoundPlaces(%v, %d) = %v, want %v", tt.value, tt.places, got, tt.want)
			}
		})
	}
}
