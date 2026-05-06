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
	pythonResponseModelRE    = regexp.MustCompile(`\bresponse_model\s*=\s*(?:(?:list|List)\s*\[\s*)?([A-Za-z_][A-Za-z0-9_]*)(?:\s*\])?`)
	pythonTopLevelBoundaryRE = regexp.MustCompile(`(?m)^(class|def|@router|\w+\s*=)`)
	goStructRE               = regexp.MustCompile(`(?m)^type\s+([A-Za-z_][A-Za-z0-9_]*)\s+struct\s*\{`)
	goJSONTagRE              = regexp.MustCompile("`json:\"([^\"]+)\"`")
)

func TestAuthResponseShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonFile := filepath.Join(root, "backend/app/api/v1/auth.py")
	goFile := filepath.Join(root, "backend-go/internal/adapter/http/auth/handler.go")

	assertRouteResponseFieldsMatch(t, pythonFile, pythonFile, goFile, authGoResponseStructs())
}

func TestSessionResponseShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonRouteFile := filepath.Join(root, "backend/app/api/v1/session.py")
	pythonSchemaFile := filepath.Join(root, "backend/app/api/v1/schemas/session.py")
	goFile := filepath.Join(root, "backend-go/internal/application/session/service.go")

	assertRouteResponseFieldsMatch(t, pythonRouteFile, pythonSchemaFile, goFile, sessionGoResponseStructs())
}

func TestExerciseResponseShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonFile := filepath.Join(root, "backend/app/api/v1/exercise.py")
	goFile := filepath.Join(root, "backend-go/internal/application/exercise/service.go")

	assertRouteResponseFieldsMatch(t, pythonFile, pythonFile, goFile, exerciseGoResponseStructs())
}

func TestMistakeResponseShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonFile := filepath.Join(root, "backend/app/api/v1/mistakes.py")
	goFile := filepath.Join(root, "backend-go/internal/application/mistake/service.go")

	assertRouteResponseFieldsMatch(t, pythonFile, pythonFile, goFile, mistakeGoResponseStructs())
}

func TestProgressResponseShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonRouteFile := filepath.Join(root, "backend/app/api/v1/progress.py")
	pythonSchemaFile := filepath.Join(root, "backend/app/api/v1/schemas/progress.py")
	goFile := filepath.Join(root, "backend-go/internal/application/progress/service.go")

	assertRouteResponseFieldsMatch(t, pythonRouteFile, pythonSchemaFile, goFile, progressGoResponseStructs())
}

func TestPortraitResponseShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonRouteFile := filepath.Join(root, "backend/app/api/v1/portrait.py")
	pythonSchemaFile := filepath.Join(root, "backend/app/api/v1/schemas/student_portrait.py")
	goFile := filepath.Join(root, "backend-go/internal/application/portrait/service.go")

	assertRouteResponseFieldsMatch(t, pythonRouteFile, pythonSchemaFile, goFile, portraitGoResponseStructs())
}

func TestResourceResponseShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonRouteFile := filepath.Join(root, "backend/app/api/v1/resources.py")
	pythonSchemaFile := filepath.Join(root, "backend/app/api/v1/schemas/resource.py")
	goFile := filepath.Join(root, "backend-go/internal/application/resource/service.go")

	assertRouteResponseFieldsMatch(t, pythonRouteFile, pythonSchemaFile, goFile, resourceGoResponseStructs())
}

func TestClassResponseShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonRouteFile := filepath.Join(root, "backend/app/api/v1/classes.py")
	pythonSchemaFile := filepath.Join(root, "backend/app/api/v1/schemas/classes.py")
	goFile := filepath.Join(root, "backend-go/internal/application/classroom/service.go")

	assertRouteResponseFieldsMatch(t, pythonRouteFile, pythonSchemaFile, goFile, classGoResponseStructs())
}

func TestTeacherResponseShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonRouteFile := filepath.Join(root, "backend/app/api/v1/teacher_stats.py")
	pythonSchemaFile := filepath.Join(root, "backend/app/api/v1/schemas/teacher_analytics.py")
	goFile := filepath.Join(root, "backend-go/internal/application/teacher/service.go")

	assertRouteResponseFieldsMatch(t, pythonRouteFile, pythonSchemaFile, goFile, teacherGoResponseStructs())
}

func TestQuestionResponseShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonRouteFile := filepath.Join(root, "backend/app/api/v1/questions.py")
	pythonSchemaFile := filepath.Join(root, "backend/app/api/v1/schemas/questions.py")
	goFile := filepath.Join(root, "backend-go/internal/application/question/service.go")

	assertRouteResponseFieldsMatch(t, pythonRouteFile, pythonSchemaFile, goFile, questionGoResponseStructs())
}

func TestAdminKnowledgeResponseShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonRouteFile := filepath.Join(root, "backend/app/api/v1/admin/knowledge.py")
	pythonSchemaFile := filepath.Join(root, "backend/app/api/v1/schemas/knowledge.py")
	goFiles := []string{
		filepath.Join(root, "backend-go/internal/application/knowledge/service.go"),
		filepath.Join(root, "backend-go/internal/adapter/http/knowledge/handler.go"),
	}

	assertRouteResponseFieldsMatchFromSchemasAndGoFiles(t, pythonRouteFile, []string{pythonSchemaFile}, goFiles, adminKnowledgeGoResponseStructs())
}

func TestAdminUserResponseShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonRouteFile := filepath.Join(root, "backend/app/api/v1/admin/users.py")
	pythonSchemaFile := filepath.Join(root, "backend/app/api/v1/schemas/admin_users.py")
	goFile := filepath.Join(root, "backend-go/internal/application/adminuser/service.go")

	assertRouteResponseFieldsMatch(t, pythonRouteFile, pythonSchemaFile, goFile, adminUserGoResponseStructs())
}

func TestAdminSettingsResponseShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonRouteFile := filepath.Join(root, "backend/app/api/v1/admin/settings.py")
	pythonSchemaFiles := []string{
		pythonRouteFile,
		filepath.Join(root, "backend/app/api/v1/schemas/database.py"),
	}
	goFile := filepath.Join(root, "backend-go/internal/application/adminsettings/service.go")

	assertRouteResponseFieldsMatchFromSchemas(t, pythonRouteFile, pythonSchemaFiles, goFile, adminSettingsGoResponseStructs())
}

func TestAdminStatsResponseShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonRouteFile := filepath.Join(root, "backend/app/api/v1/admin/stats.py")
	pythonSchemaFile := filepath.Join(root, "backend/app/api/v1/schemas/admin_stats.py")
	goFile := filepath.Join(root, "backend-go/internal/application/adminstats/service.go")

	assertRouteResponseFieldsMatch(t, pythonRouteFile, pythonSchemaFile, goFile, adminStatsGoResponseStructs())
}

func TestAdminSecurityLogResponseShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonRouteFile := filepath.Join(root, "backend/app/api/v1/admin/security_logs.py")
	pythonSchemaFile := filepath.Join(root, "backend/app/api/v1/schemas/security_log.py")
	goFile := filepath.Join(root, "backend-go/internal/application/securitylog/service.go")

	assertRouteResponseFieldsMatch(t, pythonRouteFile, pythonSchemaFile, goFile, adminSecurityLogGoResponseStructs())
}

func TestAdminInboxResponseShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonRouteFile := filepath.Join(root, "backend/app/api/v1/admin/inbox.py")
	pythonSchemaFile := filepath.Join(root, "backend/app/api/v1/schemas/password_reset.py")
	goFile := filepath.Join(root, "backend-go/internal/application/admininbox/service.go")

	assertRouteResponseFieldsMatch(t, pythonRouteFile, pythonSchemaFile, goFile, adminInboxGoResponseStructs())
}

func TestAdminBKTResponseShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonFile := filepath.Join(root, "backend/app/api/v1/admin/bkt.py")
	goFile := filepath.Join(root, "backend-go/internal/application/bkt/service.go")

	assertRouteResponseFieldsMatch(t, pythonFile, pythonFile, goFile, adminBKTGoResponseStructs())
}

func TestUploadResponseShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonFile := filepath.Join(root, "backend/app/api/v1/upload.py")
	goFile := filepath.Join(root, "backend-go/internal/application/upload/service.go")

	assertRouteResponseFieldsMatch(t, pythonFile, pythonFile, goFile, uploadGoResponseStructs())
}

func TestXidianResponseShapesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	pythonRouteFile := filepath.Join(root, "backend/app/api/v1/xidian.py")
	pythonSchemaFile := filepath.Join(root, "backend/app/api/v1/schemas/xidian.py")
	goFile := filepath.Join(root, "backend-go/internal/application/xidian/types.go")

	assertRouteResponseFieldsMatch(t, pythonRouteFile, pythonSchemaFile, goFile, xidianGoResponseStructs())
}

func assertRouteResponseFieldsMatch(t *testing.T, pythonRouteFile string, pythonSchemaFile string, goFile string, goRouteStructs map[string]string) {
	t.Helper()
	assertRouteResponseFieldsMatchWithIgnored(t, pythonRouteFile, pythonSchemaFile, goFile, goRouteStructs, nil)
}

func assertRouteResponseFieldsMatchFromSchemas(t *testing.T, pythonRouteFile string, pythonSchemaFiles []string, goFile string, goRouteStructs map[string]string) {
	t.Helper()
	assertRouteResponseFieldsMatchFromSchemasAndGoFilesWithIgnored(t, pythonRouteFile, pythonSchemaFiles, []string{goFile}, goRouteStructs, nil)
}

func assertRouteResponseFieldsMatchFromSchemasAndGoFiles(t *testing.T, pythonRouteFile string, pythonSchemaFiles []string, goFiles []string, goRouteStructs map[string]string) {
	t.Helper()
	assertRouteResponseFieldsMatchFromSchemasAndGoFilesWithIgnored(t, pythonRouteFile, pythonSchemaFiles, goFiles, goRouteStructs, nil)
}

func assertRouteResponseFieldsMatchWithIgnored(t *testing.T, pythonRouteFile string, pythonSchemaFile string, goFile string, goRouteStructs map[string]string, ignoredRoutes map[string]string) {
	t.Helper()
	assertRouteResponseFieldsMatchFromSchemasAndGoFilesWithIgnored(t, pythonRouteFile, []string{pythonSchemaFile}, []string{goFile}, goRouteStructs, ignoredRoutes)
}

func assertRouteResponseFieldsMatchFromSchemasAndGoFilesWithIgnored(t *testing.T, pythonRouteFile string, pythonSchemaFiles []string, goFiles []string, goRouteStructs map[string]string, ignoredRoutes map[string]string) {
	t.Helper()
	pythonModels := extractPythonBaseModelFieldsFromFiles(t, pythonSchemaFiles)
	pythonRouteModels := extractPythonRouteResponseModels(t, pythonRouteFile)
	goStructFields := extractGoJSONStructFieldsFromFiles(t, goFiles)

	staleIgnoredRoutes := map[string]bool{}
	for routeKey := range ignoredRoutes {
		if _, ok := pythonRouteModels[routeKey]; !ok {
			staleIgnoredRoutes[routeKey] = true
			continue
		}
		delete(pythonRouteModels, routeKey)
	}
	if len(staleIgnoredRoutes) > 0 {
		t.Fatalf("stale response shape ignored routes: %v", sortedKeys(staleIgnoredRoutes))
	}

	expectedRoutes := map[string]bool{}
	for key := range pythonRouteModels {
		expectedRoutes[key] = true
	}
	actualRoutes := map[string]bool{}
	for key := range goRouteStructs {
		actualRoutes[key] = true
	}
	if missing := difference(expectedRoutes, actualRoutes); len(missing) > 0 {
		t.Fatalf("response shape routes missing Go struct mapping: %v", missing)
	}
	if extra := difference(actualRoutes, expectedRoutes); len(extra) > 0 {
		t.Fatalf("response shape routes without legacy Python response_model: %v", extra)
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

func sessionGoResponseStructs() map[string]string {
	return map[string]string{
		"POST /start":          "CreateSessionResponse",
		"GET /{}/history":      "HistoryResponse",
		"GET /list":            "SessionListResponse",
		"PATCH /{}/mode":       "UpdateModeResponse",
		"DELETE /{}":           "DeleteResponse",
		"POST /batch-delete":   "BatchDeleteResponse",
		"POST /task/{}/cancel": "CancelTaskResponse",
	}
}

func exerciseGoResponseStructs() map[string]string {
	return map[string]string{
		"GET /next":        "ExerciseResponse",
		"POST /submit":     "SubmitResponse",
		"GET /{}":          "ExerciseDetailResponse",
		"GET /{}/solution": "SolutionResponse",
	}
}

func mistakeGoResponseStructs() map[string]string {
	return map[string]string{
		"GET ":             "MistakeListResponse",
		"GET /statistics":  "StatisticsResponse",
		"GET /{}":          "DetailResponse",
		"POST /{}/master":  "MarkAsMasteredResponse",
		"GET /review/next": "ReviewExerciseResponse",
	}
}

func progressGoResponseStructs() map[string]string {
	return map[string]string{
		"GET /class-ranking": "ClassRankingResponse",
	}
}

func portraitGoResponseStructs() map[string]string {
	return map[string]string{
		"GET ":           "PortraitResponse",
		"POST /generate": "GenerateResponse",
		"DELETE ":        "ClearResponse",
	}
}

func resourceGoResponseStructs() map[string]string {
	return map[string]string{
		"GET ":              "ListResponse",
		"GET /stats":        "Stats",
		"GET /favorites":    "ListResponse",
		"GET /{}":           "Resource",
		"POST ":             "Resource",
		"PUT /{}":           "Resource",
		"POST /{}/favorite": "FavoriteToggleResponse",
	}
}

func classGoResponseStructs() map[string]string {
	return map[string]string{
		"POST ":                          "ClassCreateResponse",
		"GET /teacher":                   "ClassListResponse",
		"GET /teacher/{}":                "ClassDetailResponse",
		"DELETE /teacher/{}/students/{}": "ActionResponse",
		"DELETE /teacher/{}":             "ActionResponse",
		"GET /lookup":                    "ClassLookupResponse",
		"POST /join":                     "JoinClassResponse",
		"POST /leave":                    "ActionResponse",
		"GET /me":                        "StudentClassResponse",
	}
}

func teacherGoResponseStructs() map[string]string {
	return map[string]string{
		"GET /analytics":            "AnalyticsResponse",
		"GET /classes/{}/analytics": "ClassAnalyticsResponse",
		"GET /students/{}/detail":   "StudentDetailResponse",
	}
}

func questionGoResponseStructs() map[string]string {
	return map[string]string{
		"POST ":                 "Question",
		"GET /groups":           "GroupsResponse",
		"GET /stats":            "Stats",
		"GET /{}":               "Question",
		"PUT /{}":               "Question",
		"GET ":                  "ListResponse",
		"POST /batch/publish":   "BatchOperationResponse",
		"POST /batch/delete":    "BatchOperationResponse",
		"POST /batch/duplicate": "BatchOperationResponse",
		"POST /ai-parse":        "AIParseResponse",
		"POST /batch/import":    "BatchOperationResponse",
	}
}

func adminKnowledgeGoResponseStructs() map[string]string {
	return map[string]string{
		"GET /stats":           "Stats",
		"GET /chapters":        "chaptersResponse",
		"GET /nodes":           "NodeListResponse",
		"GET /nodes/all":       "SimpleNode",
		"POST /nodes":          "NodeResponse",
		"GET /nodes/{}":        "KnowledgeNode",
		"PUT /nodes/{}":        "NodeResponse",
		"DELETE /nodes/{}":     "DeleteResponse",
		"GET /relations":       "RelationListResponse",
		"POST /relations":      "RelationResponse",
		"PUT /relations/{}":    "RelationResponse",
		"DELETE /relations/{}": "DeleteResponse",
	}
}

func adminUserGoResponseStructs() map[string]string {
	return map[string]string{
		"GET /stats":       "AccountStats",
		"GET ":             "ListResponse",
		"PATCH /{}/status": "UpdateResponse",
		"PUT /{}":          "UpdateResponse",
		"DELETE /{}":       "DeleteResponse",
		"POST ":            "CreateResponse",
		"POST /import":     "ImportResponse",
	}
}

func adminSettingsGoResponseStructs() map[string]string {
	return map[string]string{
		"GET /registration":               "RegistrationSettingsResponse",
		"PUT /registration":               "RegistrationSettingsResponse",
		"GET /general":                    "GeneralSettingsResponse",
		"PUT /general":                    "GeneralSettingsResponse",
		"GET /database/exportable-tables": "ExportableTablesResponse",
		"POST /database/export":           "DataExportResponse",
		"POST /database/import":           "DataImportResponse",
		"GET /database/monitor":           "DatabaseMonitorResponse",
	}
}

func adminStatsGoResponseStructs() map[string]string {
	return map[string]string{
		"GET /overview":          "OverviewStatsResponse",
		"GET /user-growth":       "UserGrowthResponse",
		"GET /recent-activities": "RecentActivitiesResponse",
		"GET /system-status":     "SystemStatusResponse",
	}
}

func adminSecurityLogGoResponseStructs() map[string]string {
	return map[string]string{
		"GET ":          "ListResponse",
		"GET /stats":    "StatsResponse",
		"POST /export":  "ExportResponse",
		"POST /archive": "ArchiveResponse",
	}
}

func adminInboxGoResponseStructs() map[string]string {
	return map[string]string{
		"GET ":            "ListResponse",
		"POST /{}/review": "ReviewResponse",
	}
}

func adminBKTGoResponseStructs() map[string]string {
	return map[string]string{
		"GET /params":           "ListResponse",
		"PUT /params/{}":        "Param",
		"POST /params/reset/{}": "Param",
		"POST /seed":            "SeedResponse",
	}
}

func uploadGoResponseStructs() map[string]string {
	return map[string]string{
		"POST /image":    "Response",
		"POST /resource": "Response",
	}
}

func xidianGoResponseStructs() map[string]string {
	return map[string]string{
		"GET /binding":           "BindingStatus",
		"POST /binding/start":    "BindStartResponse",
		"POST /binding/complete": "BindCompleteResponse",
		"POST /binding/unbind":   "UnbindResponse",
		"POST /sync/classtable":  "SyncResponse",
		"POST /sync/exams":       "SyncResponse",
		"POST /sync/scores":      "SyncResponse",
		"GET /snapshot/{}":       "SnapshotResponse",
	}
}

func extractPythonBaseModelFieldsFromFiles(t *testing.T, filenames []string) map[string]map[string]bool {
	t.Helper()
	models := map[string]map[string]bool{}
	for _, filename := range filenames {
		for modelName, fields := range extractPythonBaseModelFields(t, filename) {
			models[modelName] = fields
		}
	}
	return models
}

func extractGoJSONStructFieldsFromFiles(t *testing.T, filenames []string) map[string]map[string]bool {
	t.Helper()
	structs := map[string]map[string]bool{}
	for _, filename := range filenames {
		for structName, fields := range extractGoJSONStructFields(t, filename) {
			structs[structName] = fields
		}
	}
	return structs
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
