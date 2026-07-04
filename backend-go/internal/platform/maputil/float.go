package maputil

import "sort"

// SortedFloatKeys returns the keys of values in ascending lexical order.
func SortedFloatKeys(values map[string]float64) []string {
	keys := make([]string, 0, len(values))
	for key := range values {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}
