package contract

import (
	"net/http"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"testing"
)

var (
	pythonStatusCodeRE = regexp.MustCompile(`status_code\s*=\s*(?:status\.HTTP_([0-9]{3})_[A-Z_]+|([0-9]{3}))`)
	goRouteHandlerRE   = regexp.MustCompile(`mux\.HandleFunc\((.*),\s*h\.([A-Za-z0-9_]+)\)`)
	goHTTPStatusRE     = regexp.MustCompile(`http\.Status([A-Za-z0-9]+)`)
	goMethodCallRE     = regexp.MustCompile(`\bh\.([A-Za-z0-9_]+)\(`)
)

var goHTTPStatusCodes = map[string]int{
	"OK":                    http.StatusOK,
	"Created":               http.StatusCreated,
	"Accepted":              http.StatusAccepted,
	"NoContent":             http.StatusNoContent,
	"BadRequest":            http.StatusBadRequest,
	"Unauthorized":          http.StatusUnauthorized,
	"Forbidden":             http.StatusForbidden,
	"NotFound":              http.StatusNotFound,
	"Conflict":              http.StatusConflict,
	"RequestEntityTooLarge": http.StatusRequestEntityTooLarge,
	"UnsupportedMediaType":  http.StatusUnsupportedMediaType,
	"UnprocessableEntity":   http.StatusUnprocessableEntity,
	"TooManyRequests":       http.StatusTooManyRequests,
	"InternalServerError":   http.StatusInternalServerError,
	"NotImplemented":        http.StatusNotImplemented,
	"ServiceUnavailable":    http.StatusServiceUnavailable,
}

func TestGoSuccessStatusesMatchLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	for _, module := range routeModules {
		if module.AIPlaceholder {
			continue
		}
		t.Run(module.Name, func(t *testing.T) {
			expected := extractPythonRouteSuccessStatuses(t, filepath.Join(root, module.PythonFile))
			actual := extractGoRouteSuccessStatuses(t, filepath.Join(root, module.GoHandlerFile))

			for key, expectedStatus := range expected {
				actualStatus, ok := actual[key]
				if !ok {
					t.Fatalf("missing Go status for %s", key)
				}
				if actualStatus != expectedStatus {
					t.Fatalf("success status mismatch for %s: Go=%d Python=%d", key, actualStatus, expectedStatus)
				}
			}
		})
	}
}

func extractPythonRouteSuccessStatuses(t *testing.T, filename string) map[string]int {
	t.Helper()
	source := readFile(t, filename)
	matches := pythonDecoratorRE.FindAllStringSubmatchIndex(source, -1)
	statuses := map[string]int{}
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
		statuses[method+" "+normalizePath(pathMatch[1])] = pythonSuccessStatus(t, decorator)
	}
	return statuses
}

func pythonSuccessStatus(t *testing.T, decorator string) int {
	t.Helper()
	match := pythonStatusCodeRE.FindStringSubmatch(decorator)
	if len(match) == 0 {
		return http.StatusOK
	}
	for _, group := range match[1:] {
		if group == "" {
			continue
		}
		statusCode, err := strconv.Atoi(group)
		if err != nil {
			t.Fatalf("parse Python status code %q: %v", group, err)
		}
		return statusCode
	}
	return http.StatusOK
}

func extractGoRouteSuccessStatuses(t *testing.T, filename string) map[string]int {
	t.Helper()
	source := readFile(t, filename)
	statuses := map[string]int{}
	for _, line := range strings.Split(source, "\n") {
		line = strings.TrimSpace(line)
		match := goRouteHandlerRE.FindStringSubmatch(line)
		if len(match) != 3 {
			continue
		}
		expr := strings.TrimSpace(match[1])
		handlerName := match[2]
		var routeItem route
		if routeMatch := goMethodPrefixRE.FindStringSubmatch(expr); len(routeMatch) == 3 {
			routeItem = route{Method: routeMatch[1], Path: normalizePath(routeMatch[2])}
		} else if routeMatch := goPrefixOnlyRE.FindStringSubmatch(expr); len(routeMatch) == 2 {
			routeItem = route{Method: "*", Path: normalizePath(routeMatch[1])}
		} else {
			t.Fatalf("unsupported Go route expression in %s: %s", filename, expr)
		}
		if routeItem.Method == "*" {
			continue
		}
		statuses[routeItem.Method+" "+routeItem.Path] = inferGoHandlerSuccessStatus(t, source, handlerName)
	}
	return statuses
}

func inferGoHandlerSuccessStatus(t *testing.T, source string, handlerName string) int {
	t.Helper()
	return inferGoHandlerSuccessStatusWithVisited(t, source, handlerName, map[string]bool{})
}

func inferGoHandlerSuccessStatusWithVisited(t *testing.T, source string, handlerName string, visited map[string]bool) int {
	t.Helper()
	if visited[handlerName] {
		t.Fatalf("recursive Go handler/helper status inference at %s", handlerName)
	}
	visited[handlerName] = true
	body := goHandlerBody(t, source, handlerName)
	if strings.Contains(body, "writeSSEChatResult(") {
		return http.StatusOK
	}
	statusMatches := goHTTPStatusRE.FindAllStringSubmatch(body, -1)
	if len(statusMatches) == 0 {
		calls := goMethodCallRE.FindAllStringSubmatch(body, -1)
		for index := len(calls) - 1; index >= 0; index-- {
			if len(calls[index]) != 2 {
				continue
			}
			methodName := calls[index][1]
			if methodName == handlerName || strings.HasPrefix(methodName, "require") || strings.HasPrefix(methodName, "write") {
				continue
			}
			return inferGoHandlerSuccessStatusWithVisited(t, source, methodName, visited)
		}
		t.Fatalf("no HTTP status found in Go handler/helper %s", handlerName)
	}
	statusName := statusMatches[len(statusMatches)-1][1]
	statusCode, ok := goHTTPStatusCodes[statusName]
	if !ok {
		t.Fatalf("unknown Go HTTP status %s in handler %s", statusName, handlerName)
	}
	return statusCode
}

func goHandlerBody(t *testing.T, source string, handlerName string) string {
	t.Helper()
	signature := "func (h *Handler) " + handlerName + "("
	start := strings.Index(source, signature)
	if start < 0 {
		t.Fatalf("handler %s not found", handlerName)
	}
	openBrace := strings.Index(source[start:], "{")
	if openBrace < 0 {
		t.Fatalf("handler %s has no body", handlerName)
	}
	openBrace += start
	closeBrace := matchingBrace(source, openBrace)
	if closeBrace < 0 {
		t.Fatalf("handler %s has unmatched body braces", handlerName)
	}
	return source[openBrace+1 : closeBrace]
}

func matchingBrace(source string, openIndex int) int {
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
		case '\'', '"', '`':
			quote = char
		case '{':
			depth++
		case '}':
			depth--
			if depth == 0 {
				return absolute
			}
		}
	}
	return -1
}
