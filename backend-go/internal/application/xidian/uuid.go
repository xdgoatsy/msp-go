package xidian

import "mathstudy/backend-go/internal/platform/identifier"

func newUUID() (string, error) {
	return identifier.NewUUID()
}
