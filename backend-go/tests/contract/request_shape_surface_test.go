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

	assertRouteRequestFieldsMatch(t, pythonFile, pythonFile, goFile, authGoRequestStructs())
}

func TestSessionRequestShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonRouteFile := filepath.Join(root, "backend/app/api/v1/session.py")
	pythonSchemaFile := filepath.Join(root, "backend/app/api/v1/schemas/session.py")
	goFile := filepath.Join(root, "backend-go/internal/adapter/http/session/handler.go")

	assertRouteRequestFieldsMatch(t, pythonRouteFile, pythonSchemaFile, goFile, sessionGoRequestStructs())
}

func TestExerciseRequestShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonFile := filepath.Join(root, "backend/app/api/v1/exercise.py")
	goFile := filepath.Join(root, "backend-go/internal/adapter/http/exercise/handler.go")

	assertRouteRequestFieldsMatch(t, pythonFile, pythonFile, goFile, exerciseGoRequestStructs())
}

func TestResourceRequestShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonRouteFile := filepath.Join(root, "backend/app/api/v1/resources.py")
	pythonSchemaFile := filepath.Join(root, "backend/app/api/v1/schemas/resource.py")
	goFile := filepath.Join(root, "backend-go/internal/adapter/http/resource/handler.go")

	assertRouteRequestFieldsMatch(t, pythonRouteFile, pythonSchemaFile, goFile, resourceGoRequestStructs())
}

func TestClassRequestShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonRouteFile := filepath.Join(root, "backend/app/api/v1/classes.py")
	pythonSchemaFile := filepath.Join(root, "backend/app/api/v1/schemas/classes.py")
	goFile := filepath.Join(root, "backend-go/internal/adapter/http/classroom/handler.go")

	assertRouteRequestFieldsMatch(t, pythonRouteFile, pythonSchemaFile, goFile, classGoRequestStructs())
}

func TestQuestionRequestShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonRouteFile := filepath.Join(root, "backend/app/api/v1/questions.py")
	pythonSchemaFile := filepath.Join(root, "backend/app/api/v1/schemas/questions.py")
	goFile := filepath.Join(root, "backend-go/internal/adapter/http/question/handler.go")

	assertRouteRequestFieldsMatch(t, pythonRouteFile, pythonSchemaFile, goFile, questionGoRequestStructs())
}

func TestAdminKnowledgeRequestShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonRouteFile := filepath.Join(root, "backend/app/api/v1/admin/knowledge.py")
	pythonSchemaFile := filepath.Join(root, "backend/app/api/v1/schemas/knowledge.py")
	goFile := filepath.Join(root, "backend-go/internal/adapter/http/knowledge/handler.go")

	assertRouteRequestFieldsMatch(t, pythonRouteFile, pythonSchemaFile, goFile, adminKnowledgeGoRequestStructs())
}

func TestAdminUserRequestShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonRouteFile := filepath.Join(root, "backend/app/api/v1/admin/users.py")
	pythonSchemaFile := filepath.Join(root, "backend/app/api/v1/schemas/admin_users.py")
	goFile := filepath.Join(root, "backend-go/internal/adapter/http/adminuser/handler.go")

	assertRouteRequestFieldsMatch(t, pythonRouteFile, pythonSchemaFile, goFile, adminUserGoRequestStructs())
}

func TestAdminSettingsRequestShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonRouteFile := filepath.Join(root, "backend/app/api/v1/admin/settings.py")
	pythonSchemaFiles := []string{
		pythonRouteFile,
		filepath.Join(root, "backend/app/api/v1/schemas/database.py"),
	}
	goFile := filepath.Join(root, "backend-go/internal/adapter/http/adminsettings/handler.go")

	assertRouteRequestFieldsMatchFromSchemas(t, pythonRouteFile, pythonSchemaFiles, goFile, adminSettingsGoRequestStructs())
}

func TestAdminSecurityLogRequestShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonRouteFile := filepath.Join(root, "backend/app/api/v1/admin/security_logs.py")
	pythonSchemaFile := filepath.Join(root, "backend/app/api/v1/schemas/security_log.py")
	goFiles := []string{
		filepath.Join(root, "backend-go/internal/adapter/http/securitylog/handler.go"),
		filepath.Join(root, "backend-go/internal/application/securitylog/service.go"),
	}

	assertRouteRequestFieldsMatchFromSchemasAndGoFiles(t, pythonRouteFile, []string{pythonSchemaFile}, goFiles, adminSecurityLogGoRequestStructs())
}

func TestAdminInboxRequestShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonRouteFile := filepath.Join(root, "backend/app/api/v1/admin/inbox.py")
	pythonSchemaFile := filepath.Join(root, "backend/app/api/v1/schemas/password_reset.py")
	goFile := filepath.Join(root, "backend-go/internal/adapter/http/admininbox/handler.go")

	assertRouteRequestFieldsMatch(t, pythonRouteFile, pythonSchemaFile, goFile, adminInboxGoRequestStructs())
}

func TestAdminBKTRequestShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonFile := filepath.Join(root, "backend/app/api/v1/admin/bkt.py")
	goFile := filepath.Join(root, "backend-go/internal/adapter/http/bkt/handler.go")

	assertRouteRequestFieldsMatch(t, pythonFile, pythonFile, goFile, adminBKTGoRequestStructs())
}

func TestXidianRequestShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonRouteFile := filepath.Join(root, "backend/app/api/v1/xidian.py")
	pythonSchemaFile := filepath.Join(root, "backend/app/api/v1/schemas/xidian.py")
	goFile := filepath.Join(root, "backend-go/internal/application/xidian/types.go")

	assertRouteRequestFieldsMatch(t, pythonRouteFile, pythonSchemaFile, goFile, xidianGoRequestStructs())
}

func assertRouteRequestFieldsMatch(t *testing.T, pythonRouteFile string, pythonSchemaFile string, goFile string, goRouteStructs map[string]string) {
	t.Helper()
	assertRouteRequestFieldsMatchFromSchemas(t, pythonRouteFile, []string{pythonSchemaFile}, goFile, goRouteStructs)
}

func assertRouteRequestFieldsMatchFromSchemas(t *testing.T, pythonRouteFile string, pythonSchemaFiles []string, goFile string, goRouteStructs map[string]string) {
	t.Helper()
	assertRouteRequestFieldsMatchFromSchemasAndGoFiles(t, pythonRouteFile, pythonSchemaFiles, []string{goFile}, goRouteStructs)
}

func assertRouteRequestFieldsMatchFromSchemasAndGoFiles(t *testing.T, pythonRouteFile string, pythonSchemaFiles []string, goFiles []string, goRouteStructs map[string]string) {
	t.Helper()
	pythonModels := extractPythonBaseModelFieldsFromFiles(t, pythonSchemaFiles)
	pythonRouteModels := extractPythonRouteBodyModels(t, pythonRouteFile, pythonModels)
	goStructFields := extractGoJSONStructFieldsFromFiles(t, goFiles)
	expectedRoutes := map[string]bool{}
	for key := range pythonRouteModels {
		expectedRoutes[key] = true
	}
	actualRoutes := map[string]bool{}
	for key := range goRouteStructs {
		actualRoutes[key] = true
	}
	if missing := difference(expectedRoutes, actualRoutes); len(missing) > 0 {
		t.Fatalf("request shape routes missing Go struct mapping: %v", missing)
	}
	if extra := difference(actualRoutes, expectedRoutes); len(extra) > 0 {
		t.Fatalf("request shape routes without legacy Python body model: %v", extra)
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

func sessionGoRequestStructs() map[string]string {
	return map[string]string{
		"POST /start":        "startRequest",
		"POST /{}/chat":      "chatRequest",
		"PATCH /{}/mode":     "updateModeRequest",
		"POST /batch-delete": "batchDeleteRequest",
	}
}

func exerciseGoRequestStructs() map[string]string {
	return map[string]string{
		"POST /submit": "submitRequest",
	}
}

func resourceGoRequestStructs() map[string]string {
	return map[string]string{
		"POST ":   "createRequest",
		"PUT /{}": "updateRequest",
	}
}

func classGoRequestStructs() map[string]string {
	return map[string]string{
		"POST ":      "createRequest",
		"POST /join": "joinRequest",
	}
}

func questionGoRequestStructs() map[string]string {
	return map[string]string{
		"POST ":                 "createRequest",
		"PUT /{}":               "updateRequest",
		"POST /batch/publish":   "batchRequest",
		"POST /batch/delete":    "batchRequest",
		"POST /batch/duplicate": "batchRequest",
		"POST /ai-parse":        "aiParseRequest",
		"POST /batch/import":    "batchImportRequest",
	}
}

func adminKnowledgeGoRequestStructs() map[string]string {
	return map[string]string{
		"POST /nodes":       "nodeCreateRequest",
		"PUT /nodes/{}":     "nodeUpdateRequest",
		"POST /relations":   "relationCreateRequest",
		"PUT /relations/{}": "relationUpdateRequest",
	}
}

func adminUserGoRequestStructs() map[string]string {
	return map[string]string{
		"PATCH /{}/status": "statusUpdateRequest",
		"PUT /{}":          "updateRequest",
		"POST ":            "createRequest",
	}
}

func adminSettingsGoRequestStructs() map[string]string {
	return map[string]string{
		"PUT /registration":     "registrationRequest",
		"PUT /general":          "generalRequest",
		"POST /database/export": "exportRequest",
	}
}

func adminSecurityLogGoRequestStructs() map[string]string {
	return map[string]string{
		"DELETE ":       "DeleteRequest",
		"POST /export":  "ExportRequest",
		"POST /archive": "archiveRequest",
	}
}

func adminInboxGoRequestStructs() map[string]string {
	return map[string]string{
		"POST /{}/review": "reviewRequestBody",
	}
}

func adminBKTGoRequestStructs() map[string]string {
	return map[string]string{
		"PUT /params/{}": "updateRequest",
	}
}

func xidianGoRequestStructs() map[string]string {
	return map[string]string{
		"POST /binding/complete": "CompleteBindingInput",
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
