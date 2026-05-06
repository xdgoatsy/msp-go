package contract

import (
	"path/filepath"
	"testing"
)

func TestGoErrorBodiesExposeStableCompatibilityFields(t *testing.T) {
	root := repoRoot(t)
	for _, module := range routeModules {
		t.Run(module.Name, func(t *testing.T) {
			goStructFields := extractGoJSONStructFields(t, filepath.Join(root, module.GoHandlerFile))
			actualFields, ok := goStructFields["errorResponse"]
			if !ok {
				t.Fatalf("Go handler %s must define an errorResponse struct", module.GoHandlerFile)
			}
			expectedFields := expectedErrorBodyFields(module)
			if missing := difference(expectedFields, actualFields); len(missing) > 0 {
				t.Fatalf("errorResponse for %s is missing fields: %v", module.Name, missing)
			}
		})
	}
}

func expectedErrorBodyFields(module routeModule) map[string]bool {
	if module.Name == "/xidian" {
		return map[string]bool{
			"code":    true,
			"message": true,
		}
	}
	return map[string]bool{
		"detail":  true,
		"code":    true,
		"message": true,
	}
}
