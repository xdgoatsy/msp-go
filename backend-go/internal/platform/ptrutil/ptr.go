package ptrutil

// Clone returns a pointer to a copy of value, or nil when value is nil.
func Clone[T any](value *T) *T {
	if value == nil {
		return nil
	}
	copied := *value
	return &copied
}
