package contract

import (
	"path/filepath"
	"regexp"
	"strings"
	"testing"
)

var (
	pythonFunctionParamTypeRE = regexp.MustCompile(`\b[A-Za-z_][A-Za-z0-9_]*\s*:\s*([A-Za-z_][A-Za-z0-9_]*)\b`)
)

func TestAuthRequestShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonFile := filepath.Join(root, "backend/app/api/v1/auth.py")
	goFile := filepath.Join(root, "backend-go/internal/adapter/http/auth/handler.go")

	pythonModels := extractPythonBaseModelFields(t, pythonFile)
	pythonRouteModels := extractPythonRouteBodyModels(t, pythonFile, pythonModels)
	goStructFields := extractGoJSONStructFields(t, goFile)
	goRouteStructs := authGoRequestStructs()

	expectedRoutes := map[string]bool{}
	for key := range pythonRouteModels {
		expectedRoutes[key] = true
	}
	actualRoutes := map[string]bool{}
	for key := range goRouteStructs {
		actualRoutes[key] = true
	}
	if missing := difference(expectedRoutes, actualRoutes); len(missing) > 0 {
		t.Fatalf("auth request shape routes missing Go struct mapping: %v", missing)
	}
	if extra := difference(actualRoutes, expectedRoutes); len(extra) > 0 {
		t.Fatalf("auth request shape routes without legacy Python body model: %v", extra)
	}

	for routeKey, modelName := range pythonRouteModels {
		structName := goRouteStructs[routeKey]
		expectedFields := pythonModels[modelName]
		actualFields, ok := goStructFields[structName]
		if !ok {
			t.Fatalf("Go request struct %s for %s was not parsed", structName, routeKey)
		}
		missing := difference(expectedFields, actualFields)
		extra := difference(actualFields, expectedFields)
		if len(missing) > 0 || len(extra) > 0 {
			t.Fatalf("request field mismatch for %s Python model %s vs Go struct %s\nmissing in Go: %v\nextra in Go: %v", routeKey, modelName, structName, missing, extra)
		}
	}
}

func authGoRequestStructs() map[string]string {
	return map[string]string{
		"POST /login":           "loginRequest",
		"PUT /change-password":  "changePasswordRequest",
		"POST /register":        "registerRequest",
		"POST /forgot-password": "forgotPasswordRequest",
	}
}

func extractPythonRouteBodyModels(t *testing.T, filename string, baseModels map[string]map[string]bool) map[string]string {
	t.Helper()
	source := readFile(t, filename)
	matches := pythonDecoratorRE.FindAllStringSubmatchIndex(source, -1)
	models := map[string]string{}
	for index, match := range matches {
		method := strings.ToUpper(source[match[2]:match[3]])
		openParen := strings.Index(source[match[0]:], "(")
		if openParen < 0 {
			t.Fatalf("route decorator without opening parenthesis in %s", filename)
		}
		start := match[0] + openParen
		end := matchingParen(source, start)
		if end < 0 {
			t.Fatalf("route decorator without matching parenthesis in %s", filename)
		}
		decorator := source[start+1 : end]
		pathMatch := quotedPathRE.FindStringSubmatch(decorator)
		if len(pathMatch) != 2 {
			t.Fatalf("route decorator without path literal in %s: %s", filename, decorator)
		}

		blockEnd := len(source)
		if index+1 < len(matches) {
			blockEnd = matches[index+1][0]
		}
		modelName, ok := routeBodyModel(source[match[1]:blockEnd], baseModels)
		if ok {
			models[method+" "+normalizePath(pathMatch[1])] = modelName
		}
	}
	return models
}

func routeBodyModel(routeBlock string, baseModels map[string]map[string]bool) (string, bool) {
	defIndex := strings.Index(routeBlock, "def ")
	if defIndex < 0 {
		return "", false
	}
	openParen := strings.Index(routeBlock[defIndex:], "(")
	if openParen < 0 {
		return "", false
	}
	openParen += defIndex
	closeParen := matchingParen(routeBlock, openParen)
	if closeParen < 0 {
		return "", false
	}
	signature := routeBlock[openParen+1 : closeParen]
	for _, match := range pythonFunctionParamTypeRE.FindAllStringSubmatch(signature, -1) {
		if _, ok := baseModels[match[1]]; ok {
			return match[1], true
		}
	}
	return "", false
}
