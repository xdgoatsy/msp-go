package contract

import (
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"testing"
)

var (
	httpExceptionRE           = regexp.MustCompile(`HTTPException\s*\(`)
	statusCodeNumberRE        = regexp.MustCompile(`(?:status\.HTTP_([0-9]{3})_[A-Z_]+|\b([1-5][0-9]{2})\b)`)
	goDelegatedMethodCallRE   = regexp.MustCompile(`\bh\.([A-Za-z0-9_]+)\(`)
	goFunctionStatusCallRE    = regexp.MustCompile(`\b([A-Za-z_][A-Za-z0-9_]*)\s*\(`)
	goNonMethodHelperPrefixes = []string{"write", "decode", "parse"}
)

func TestGoExplicitErrorStatusesCoverLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	for _, module := range routeModules {
		if module.AIPlaceholder {
			continue
		}
		t.Run(module.Name, func(t *testing.T) {
			expected := extractPythonRouteErrorStatuses(t, filepath.Join(root, module.PythonFile))
			actual := extractGoRouteReachableStatuses(t, filepath.Join(root, module.GoHandlerFile))

			for key, expectedStatuses := range expected {
				actualStatuses, ok := actual[key]
				if !ok {
					t.Fatalf("missing Go error status surface for %s", key)
				}
				missing := missingStatuses(expectedStatuses, actualStatuses)
				if len(missing) > 0 {
					t.Fatalf("missing Go error statuses for %s: %v", key, missing)
				}
			}
		})
	}
}

func extractPythonRouteErrorStatuses(t *testing.T, filename string) map[string]map[int]bool {
	t.Helper()
	source := readFile(t, filename)
	matches := pythonDecoratorRE.FindAllStringSubmatchIndex(source, -1)
	statuses := map[string]map[int]bool{}
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
		key := method + " " + normalizePath(pathMatch[1])
		statuses[key] = pythonHTTPExceptionStatuses(t, source[match[0]:blockEnd])
	}
	return statuses
}

func pythonHTTPExceptionStatuses(t *testing.T, block string) map[int]bool {
	t.Helper()
	statuses := map[int]bool{}
	for _, match := range httpExceptionRE.FindAllStringIndex(block, -1) {
		open := match[1] - 1
		close := matchingParen(block, open)
		if close < 0 {
			t.Fatalf("HTTPException call with unmatched parentheses")
		}
		expression, ok := statusCodeArgument(block[open+1 : close])
		if !ok {
			continue
		}
		for _, code := range extractNumericStatusCodes(t, expression) {
			statuses[code] = true
		}
	}
	return statuses
}

func statusCodeArgument(arguments string) (string, bool) {
	index := strings.Index(arguments, "status_code")
	if index < 0 {
		return "", false
	}
	index += len("status_code")
	for index < len(arguments) && isWhitespace(arguments[index]) {
		index++
	}
	if index >= len(arguments) || arguments[index] != '=' {
		return "", false
	}
	index++
	start := index
	depth := 0
	var quote byte
	escaped := false
	for index < len(arguments) {
		char := arguments[index]
		if quote != 0 {
			if escaped {
				escaped = false
			} else if char == '\\' {
				escaped = true
			} else if char == quote {
				quote = 0
			}
			index++
			continue
		}
		switch char {
		case '\'', '"':
			quote = char
		case '(', '[', '{':
			depth++
		case ')', ']', '}':
			if depth > 0 {
				depth--
			}
		case ',':
			if depth == 0 {
				return arguments[start:index], true
			}
		}
		index++
	}
	return arguments[start:index], true
}

func extractNumericStatusCodes(t *testing.T, expression string) []int {
	t.Helper()
	statuses := []int{}
	for _, match := range statusCodeNumberRE.FindAllStringSubmatch(expression, -1) {
		for _, group := range match[1:] {
			if group == "" {
				continue
			}
			statusCode, err := strconv.Atoi(group)
			if err != nil {
				t.Fatalf("parse status code %q: %v", group, err)
			}
			statuses = append(statuses, statusCode)
		}
	}
	return statuses
}

func extractGoRouteReachableStatuses(t *testing.T, filename string) map[string]map[int]bool {
	t.Helper()
	source := readFile(t, filename)
	statuses := map[string]map[int]bool{}
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
		statuses[routeItem.Method+" "+routeItem.Path] = collectGoReachableStatuses(t, source, handlerName, map[string]bool{})
	}
	return statuses
}

func collectGoReachableStatuses(t *testing.T, source string, functionName string, visited map[string]bool) map[int]bool {
	t.Helper()
	if visited[functionName] {
		return map[int]bool{}
	}
	visited[functionName] = true
	body := goStatusFunctionBody(t, source, functionName)
	statuses := map[int]bool{}
	for _, match := range goHTTPStatusRE.FindAllStringSubmatch(body, -1) {
		if len(match) != 2 {
			continue
		}
		statusCode, ok := goHTTPStatusCodes[match[1]]
		if !ok {
			t.Fatalf("unknown Go HTTP status %s in handler/helper %s", match[1], functionName)
		}
		statuses[statusCode] = true
	}
	for _, match := range goDelegatedMethodCallRE.FindAllStringSubmatch(body, -1) {
		if len(match) == 2 {
			mergeStatuses(statuses, collectGoReachableStatuses(t, source, match[1], visited))
		}
	}
	for _, match := range goFunctionStatusCallRE.FindAllStringSubmatch(body, -1) {
		if len(match) != 2 || !isGoStatusHelper(match[1]) || !goFunctionExists(source, match[1]) {
			continue
		}
		mergeStatuses(statuses, collectGoReachableStatuses(t, source, match[1], visited))
	}
	return statuses
}

func isGoStatusHelper(functionName string) bool {
	for _, prefix := range goNonMethodHelperPrefixes {
		if strings.HasPrefix(functionName, prefix) {
			return true
		}
	}
	return false
}

func goFunctionExists(source string, functionName string) bool {
	return strings.Contains(source, "func "+functionName+"(")
}

func goStatusFunctionBody(t *testing.T, source string, functionName string) string {
	t.Helper()
	if strings.Contains(source, "func (h *Handler) "+functionName+"(") {
		return goHandlerBody(t, source, functionName)
	}
	signature := "func " + functionName + "("
	start := strings.Index(source, signature)
	if start < 0 {
		t.Fatalf("function %s not found", functionName)
	}
	openBrace := strings.Index(source[start:], "{")
	if openBrace < 0 {
		t.Fatalf("function %s has no body", functionName)
	}
	openBrace += start
	closeBrace := matchingBrace(source, openBrace)
	if closeBrace < 0 {
		t.Fatalf("function %s has unmatched body braces", functionName)
	}
	return source[openBrace+1 : closeBrace]
}

func mergeStatuses(left, right map[int]bool) {
	for status := range right {
		left[status] = true
	}
}

func missingStatuses(expected, actual map[int]bool) []int {
	missing := []int{}
	for status := range expected {
		if !actual[status] {
			missing = append(missing, status)
		}
	}
	sort.Ints(missing)
	return missing
}
