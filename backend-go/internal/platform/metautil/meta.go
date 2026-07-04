package metautil

import "mathstudy/backend-go/internal/platform/sliceutil"

// LookupString returns a string metadata value and whether it was present as a string.
func LookupString(meta map[string]any, key string) (string, bool) {
	if meta == nil {
		return "", false
	}
	value, ok := meta[key]
	if !ok || value == nil {
		return "", false
	}
	text, ok := value.(string)
	if !ok {
		return "", false
	}
	return text, true
}

// String returns a string metadata value, or an empty string when missing or not a string.
func String(meta map[string]any, key string) string {
	value, ok := LookupString(meta, key)
	if !ok {
		return ""
	}
	return value
}

// StringPointer returns a pointer to a string metadata value when present.
func StringPointer(meta map[string]any, key string) *string {
	value, ok := LookupString(meta, key)
	if !ok {
		return nil
	}
	return &value
}

// LookupStringSlice returns a string slice metadata value and whether a slice was present.
func LookupStringSlice(meta map[string]any, key string) ([]string, bool) {
	if meta == nil {
		return nil, false
	}
	value, exists := meta[key]
	if !exists || value == nil {
		return nil, false
	}
	switch typed := value.(type) {
	case []string:
		return sliceutil.CloneStrings(typed), true
	case []any:
		result := make([]string, 0, len(typed))
		for _, item := range typed {
			if text, ok := item.(string); ok {
				result = append(result, text)
			}
		}
		return result, true
	default:
		return nil, false
	}
}

// StringSlice returns a string slice metadata value, or an empty slice when missing or not a slice.
func StringSlice(meta map[string]any, key string) []string {
	values, ok := LookupStringSlice(meta, key)
	if !ok {
		return []string{}
	}
	return values
}

// OptionalStringSlice returns nil when the metadata key is absent or not a slice.
func OptionalStringSlice(meta map[string]any, key string) []string {
	values, ok := LookupStringSlice(meta, key)
	if !ok {
		return nil
	}
	return values
}
