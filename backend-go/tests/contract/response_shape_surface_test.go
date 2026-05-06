package contract

import (
	"path/filepath"
	"regexp"
	"strings"
	"testing"
)

var (
	pythonBaseModelClassRE   = regexp.MustCompile(`(?m)^class\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(\s*BaseModel\s*\)\s*:`)
	pythonModelFieldRE       = regexp.MustCompile(`(?m)^\s+([A-Za-z_][A-Za-z0-9_]*)\s*:`)
	pythonResponseModelRE    = regexp.MustCompile(`\bresponse_model\s*=\s*([A-Za-z_][A-Za-z0-9_]*)`)
	pythonTopLevelBoundaryRE = regexp.MustCompile(`(?m)^(class|def|@router|\w+\s*=)`)
	goStructRE               = regexp.MustCompile(`(?m)^type\s+([A-Za-z_][A-Za-z0-9_]*)\s+struct\s*\{`)
	goJSONTagRE              = regexp.MustCompile("`json:\"([^\"]+)\"`")
)

func TestAuthResponseShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonFile := filepath.Join(root, "backend/app/api/v1/auth.py")
	goFile := filepath.Join(root, "backend-go/internal/adapter/http/auth/handler.go")

	pythonModels := extractPythonBaseModelFields(t, pythonFile)
	pythonRouteModels := extractPythonRouteResponseModels(t, pythonFile)
	goStructFields := extractGoJSONStructFields(t, goFile)
	goRouteStructs := authGoResponseStructs()

	expectedRoutes := map[string]bool{}
	for key := range pythonRouteModels {
		expectedRoutes[key] = true
	}
	actualRoutes := map[string]bool{}
	for key := range goRouteStructs {
		actualRoutes[key] = true
	}
	if missing := difference(expectedRoutes, actualRoutes); len(missing) > 0 {
		t.Fatalf("auth response shape routes missing Go struct mapping: %v", missing)
	}
	if extra := difference(actualRoutes, expectedRoutes); len(extra) > 0 {
		t.Fatalf("auth response shape routes without legacy Python response_model: %v", extra)
	}

	for routeKey, modelName := range pythonRouteModels {
		structName := goRouteStructs[routeKey]
		expectedFields, ok := pythonModels[modelName]
		if !ok {
			t.Fatalf("Python response model %s for %s was not parsed", modelName, routeKey)
		}
		actualFields, ok := goStructFields[structName]
		if !ok {
			t.Fatalf("Go response struct %s for %s was not parsed", structName, routeKey)
		}
		missing := difference(expectedFields, actualFields)
		extra := difference(actualFields, expectedFields)
		if len(missing) > 0 || len(extra) > 0 {
			t.Fatalf("response field mismatch for %s Python model %s vs Go struct %s\nmissing in Go: %v\nextra in Go: %v", routeKey, modelName, structName, missing, extra)
		}
	}
}

func authGoResponseStructs() map[string]string {
	return map[string]string{
		"POST /login":                 "loginResponse",
		"PUT /change-password":        "messageResponse",
		"POST /register":              "loginResponse",
		"POST /refresh":               "refreshResponse",
		"POST /logout":                "messageResponse",
		"GET /me":                     "userResponse",
		"GET /registration-status":    "registrationStatusResponse",
		"POST /forgot-password":       "forgotPasswordResponse",
		"GET /forgot-password/status": "forgotPasswordStatusResponse",
	}
}

func extractPythonBaseModelFields(t *testing.T, filename string) map[string]map[string]bool {
	t.Helper()
	source := readFile(t, filename)
	models := map[string]map[string]bool{}
	matches := pythonBaseModelClassRE.FindAllStringSubmatchIndex(source, -1)
	for _, match := range matches {
		modelName := source[match[2]:match[3]]
		bodyStart := match[1]
		bodyEnd := len(source)
		if boundary := pythonTopLevelBoundaryRE.FindStringIndex(source[bodyStart:]); boundary != nil {
			bodyEnd = bodyStart + boundary[0]
		}
		fields := map[string]bool{}
		for _, fieldMatch := range pythonModelFieldRE.FindAllStringSubmatch(source[bodyStart:bodyEnd], -1) {
			fields[fieldMatch[1]] = true
		}
		models[modelName] = fields
	}
	return models
}

func extractPythonRouteResponseModels(t *testing.T, filename string) map[string]string {
	t.Helper()
	source := readFile(t, filename)
	matches := pythonDecoratorRE.FindAllStringSubmatchIndex(source, -1)
	models := map[string]string{}
	for _, match := range matches {
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
		modelMatch := pythonResponseModelRE.FindStringSubmatch(decorator)
		if len(modelMatch) != 2 {
			continue
		}
		models[method+" "+normalizePath(pathMatch[1])] = modelMatch[1]
	}
	return models
}

func extractGoJSONStructFields(t *testing.T, filename string) map[string]map[string]bool {
	t.Helper()
	source := readFile(t, filename)
	structs := map[string]map[string]bool{}
	matches := goStructRE.FindAllStringSubmatchIndex(source, -1)
	for _, match := range matches {
		structName := source[match[2]:match[3]]
		openBrace := strings.LastIndex(source[match[0]:match[1]], "{")
		if openBrace < 0 {
			t.Fatalf("Go struct %s has no opening brace", structName)
		}
		openBrace += match[0]
		closeBrace := matchingBrace(source, openBrace)
		if closeBrace < 0 {
			t.Fatalf("Go struct %s has unmatched braces", structName)
		}
		fields := map[string]bool{}
		for _, tagMatch := range goJSONTagRE.FindAllStringSubmatch(source[openBrace+1:closeBrace], -1) {
			tag := strings.Split(tagMatch[1], ",")[0]
			if tag != "" && tag != "-" {
				fields[tag] = true
			}
		}
		structs[structName] = fields
	}
	return structs
}
