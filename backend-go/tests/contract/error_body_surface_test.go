package contract

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestGoErrorBodiesExposeStableCompatibilityFields(t *testing.T) {
	root := repoRoot(t)
	for _, module := range routeModules {
		t.Run(module.Name, func(t *testing.T) {
			goStructFields := extractGoJSONStructFields(t, filepath.Join(root, module.GoHandlerFile))
			actualFields, ok := goStructFields["errorResponse"]
			if !ok {
				actualFields, ok = sharedDetailErrorFields(t, root, module)
			}
			if !ok {
				t.Fatalf("Go handler %s must define an errorResponse struct or use httpjson.WriteDetailError", module.GoHandlerFile)
			}
			expectedFields := expectedErrorBodyFields(module)
			if missing := difference(expectedFields, actualFields); len(missing) > 0 {
				t.Fatalf("errorResponse for %s is missing fields: %v", module.Name, missing)
			}
		})
	}
}

func sharedDetailErrorFields(t *testing.T, root string, module routeModule) (map[string]bool, bool) {
	if module.Name == "/xidian" {
		return nil, false
	}
	handlerPath := filepath.Join(root, module.GoHandlerFile)
	raw, err := os.ReadFile(handlerPath)
	if err != nil {
		t.Fatalf("read Go handler %s: %v", handlerPath, err)
	}
	if !strings.Contains(string(raw), "httpjson.WriteDetailError") {
		return nil, false
	}
	sharedFields := extractGoJSONStructFields(t, filepath.Join(root, "backend-go/internal/platform/httpjson/decode.go"))
	fields, ok := sharedFields["DetailError"]
	return fields, ok
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
