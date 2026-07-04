package numutil

import "math"

// RoundPlaces rounds value to the requested number of decimal places.
func RoundPlaces(value float64, places int) float64 {
	scale := math.Pow10(places)
	return math.Round(value*scale) / scale
}
