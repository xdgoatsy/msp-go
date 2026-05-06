package contract

import (
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"testing"
)

type route struct {
	Method string
	Path   string
}

type routeModule struct {
	Name          string
	PythonFile    string
	GoHandlerFile string
	AIPlaceholder bool
}

var routeModules = []routeModule{
	{Name: "/auth", PythonFile: "backend/app/api/v1/auth.py", GoHandlerFile: "backend-go/internal/adapter/http/auth/handler.go"},
	{Name: "/session", PythonFile: "backend/app/api/v1/session.py", GoHandlerFile: "backend-go/internal/adapter/http/session/handler.go"},
	{Name: "/exercise", PythonFile: "backend/app/api/v1/exercise.py", GoHandlerFile: "backend-go/internal/adapter/http/exercise/handler.go"},
	{Name: "/mistakes", PythonFile: "backend/app/api/v1/mistakes.py", GoHandlerFile: "backend-go/internal/adapter/http/mistake/handler.go"},
	{Name: "/questions", PythonFile: "backend/app/api/v1/questions.py", GoHandlerFile: "backend-go/internal/adapter/http/question/handler.go"},
	{Name: "/progress", PythonFile: "backend/app/api/v1/progress.py", GoHandlerFile: "backend-go/internal/adapter/http/progress/handler.go"},
	{Name: "/resources", PythonFile: "backend/app/api/v1/resources.py", GoHandlerFile: "backend-go/internal/adapter/http/resource/handler.go"},
	{Name: "/upload", PythonFile: "backend/app/api/v1/upload.py", GoHandlerFile: "backend-go/internal/adapter/http/upload/handler.go"},
	{Name: "/xidian", PythonFile: "backend/app/api/v1/xidian.py", GoHandlerFile: "backend-go/internal/adapter/http/xidian/handler.go"},
	{Name: "/classes", PythonFile: "backend/app/api/v1/classes.py", GoHandlerFile: "backend-go/internal/adapter/http/classroom/handler.go"},
	{Name: "/teacher", PythonFile: "backend/app/api/v1/teacher_stats.py", GoHandlerFile: "backend-go/internal/adapter/http/teacher/handler.go"},
	{Name: "/portrait", PythonFile: "backend/app/api/v1/portrait.py", GoHandlerFile: "backend-go/internal/adapter/http/portrait/handler.go"},
	{Name: "/admin/users", PythonFile: "backend/app/api/v1/admin/users.py", GoHandlerFile: "backend-go/internal/adapter/http/adminuser/handler.go"},
	{Name: "/admin/stats", PythonFile: "backend/app/api/v1/admin/stats.py", GoHandlerFile: "backend-go/internal/adapter/http/adminstats/handler.go"},
	{Name: "/admin/settings", PythonFile: "backend/app/api/v1/admin/settings.py", GoHandlerFile: "backend-go/internal/adapter/http/adminsettings/handler.go"},
	{Name: "/admin/security-logs", PythonFile: "backend/app/api/v1/admin/security_logs.py", GoHandlerFile: "backend-go/internal/adapter/http/securitylog/handler.go"},
	{Name: "/admin/knowledge", PythonFile: "backend/app/api/v1/admin/knowledge.py", GoHandlerFile: "backend-go/internal/adapter/http/knowledge/handler.go"},
	{Name: "/admin/inbox", PythonFile: "backend/app/api/v1/admin/inbox.py", GoHandlerFile: "backend-go/internal/adapter/http/admininbox/handler.go"},
	{Name: "/admin/bkt", PythonFile: "backend/app/api/v1/admin/bkt.py", GoHandlerFile: "backend-go/internal/adapter/http/bkt/handler.go"},
	{Name: "/admin/ai-config", PythonFile: "backend/app/api/v1/admin/ai_config.py", GoHandlerFile: "backend-go/internal/adapter/http/adminaiconfig/handler.go", AIPlaceholder: true},
}

var (
	pythonDecoratorRE = regexp.MustCompile(`@router\.(get|post|put|patch|delete)\s*\(`)
	quotedPathRE      = regexp.MustCompile(`["']([^"']*)["']`)
	goRouteRE         = regexp.MustCompile(`mux\.HandleFunc\((.*),`)
	goMethodPrefixRE  = regexp.MustCompile(`"([A-Z]+) "\s*\+\s*prefix(?:\s*\+\s*"([^"]*)")?`)
	goPrefixOnlyRE    = regexp.MustCompile(`^prefix(?:\s*\+\s*"([^"]*)")?$`)
	pathParamRE       = regexp.MustCompile(`\{[^}/]+\}`)
)

func TestGoRouteSurfaceMatchesLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	for _, module := range routeModules {
		t.Run(module.Name, func(t *testing.T) {
			pythonRoutes := extractPythonRoutes(t, filepath.Join(root, module.PythonFile))
			goRoutes := extractGoRoutes(t, filepath.Join(root, module.GoHandlerFile))

			if module.AIPlaceholder {
				assertAIPlaceholder(t, goRoutes)
				if len(pythonRoutes) == 0 {
					t.Fatalf("legacy AI route baseline is empty; expected Python route surface for %s", module.Name)
				}
				return
			}

			assertSameRoutes(t, pythonRoutes, goRoutes)
		})
	}
}

func repoRoot(t *testing.T) string {
	t.Helper()
	wd, err := os.Getwd()
	if err != nil {
		t.Fatalf("get working directory: %v", err)
	}
	return filepath.Clean(filepath.Join(wd, "..", "..", ".."))
}

func extractPythonRoutes(t *testing.T, filename string) []route {
	t.Helper()
	source := readFile(t, filename)
	matches := pythonDecoratorRE.FindAllStringSubmatchIndex(source, -1)
	routes := make([]route, 0, len(matches))
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
		routes = append(routes, route{Method: method, Path: normalizePath(pathMatch[1])})
	}
	return routes
}

func extractGoRoutes(t *testing.T, filename string) []route {
	t.Helper()
	source := readFile(t, filename)
	routes := []route{}
	for _, line := range strings.Split(source, "\n") {
		line = strings.TrimSpace(line)
		match := goRouteRE.FindStringSubmatch(line)
		if len(match) != 2 {
			continue
		}
		expr := strings.TrimSpace(match[1])
		if routeMatch := goMethodPrefixRE.FindStringSubmatch(expr); len(routeMatch) == 3 {
			routes = append(routes, route{Method: routeMatch[1], Path: normalizePath(routeMatch[2])})
			continue
		}
		if routeMatch := goPrefixOnlyRE.FindStringSubmatch(expr); len(routeMatch) == 2 {
			routes = append(routes, route{Method: "*", Path: normalizePath(routeMatch[1])})
			continue
		}
		t.Fatalf("unsupported Go route expression in %s: %s", filename, expr)
	}
	return routes
}

func matchingParen(source string, openIndex int) int {
	depth := 0
	var quote rune
	escaped := false
	for index, char := range source[openIndex:] {
		absolute := openIndex + index
		if quote != 0 {
			if escaped {
				escaped = false
				continue
			}
			if char == '\\' {
				escaped = true
				continue
			}
			if char == quote {
				quote = 0
			}
			continue
		}
		switch char {
		case '\'', '"':
			quote = char
		case '(':
			depth++
		case ')':
			depth--
			if depth == 0 {
				return absolute
			}
		}
	}
	return -1
}

func assertAIPlaceholder(t *testing.T, routes []route) {
	t.Helper()
	routeSet := routeKeys(routes)
	if !routeSet["* "] || !routeSet["* /"] {
		t.Fatalf("AI config must preserve exact and subtree TODO placeholders, got %v", sortedKeys(routeSet))
	}
}

func assertSameRoutes(t *testing.T, expected []route, actual []route) {
	t.Helper()
	expectedSet := routeKeys(expected)
	actualSet := routeKeys(actual)
	missing := difference(expectedSet, actualSet)
	extra := difference(actualSet, expectedSet)
	if len(missing) > 0 || len(extra) > 0 {
		t.Fatalf("route mismatch\nmissing in Go: %v\nextra in Go: %v", missing, extra)
	}
}

func routeKeys(routes []route) map[string]bool {
	keys := make(map[string]bool, len(routes))
	for _, item := range routes {
		keys[item.Method+" "+item.Path] = true
	}
	return keys
}

func difference(left, right map[string]bool) []string {
	result := []string{}
	for key := range left {
		if !right[key] {
			result = append(result, key)
		}
	}
	sort.Strings(result)
	return result
}

func sortedKeys(items map[string]bool) []string {
	result := make([]string, 0, len(items))
	for key := range items {
		result = append(result, key)
	}
	sort.Strings(result)
	return result
}

func normalizePath(path string) string {
	path = strings.TrimSpace(path)
	if path == "" {
		return ""
	}
	if !strings.HasPrefix(path, "/") {
		path = "/" + path
	}
	return pathParamRE.ReplaceAllString(path, "{}")
}

func readFile(t *testing.T, filename string) string {
	t.Helper()
	content, err := os.ReadFile(filename)
	if err != nil {
		t.Fatalf("read %s: %v", filename, err)
	}
	return string(content)
}
