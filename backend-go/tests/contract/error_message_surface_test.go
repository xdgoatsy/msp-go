package contract

import (
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"testing"
)

var (
	goStringLiteralRE = regexp.MustCompile("`[^`]*`|\"(?:\\\\.|[^\"\\\\])*\"")
)

func TestGoStaticErrorMessagesCoverLegacyPythonBaseline(t *testing.T) {
	root := repoRoot(t)
	for _, module := range routeModules {
		if module.AIPlaceholder {
			continue
		}
		t.Run(module.Name, func(t *testing.T) {
			expected := extractPythonRouteStaticErrorDetails(t, filepath.Join(root, module.PythonFile))
			actual := extractGoRouteReachableMessages(t, filepath.Join(root, module.GoHandlerFile))
			extraMessages := extractGoStringLiteralsFromFiles(t, root, extraGoErrorMessageFiles(module))
			for _, routeMessages := range actual {
				mergeMessages(routeMessages, extraMessages)
			}

			for key, expectedMessages := range expected {
				actualMessages, ok := actual[key]
				if !ok {
					t.Fatalf("missing Go error message surface for %s", key)
				}
				if missing := difference(expectedMessages, actualMessages); len(missing) > 0 {
					t.Fatalf("missing Go static error messages for %s: %v", key, missing)
				}
			}
		})
	}
}

func extraGoErrorMessageFiles(module routeModule) []string {
	switch module.Name {
	case "/auth":
		return []string{"backend-go/internal/application/auth/service.go"}
	case "/admin/users":
		return []string{"backend-go/internal/application/adminuser/service.go"}
	case "/admin/knowledge":
		return []string{"backend-go/internal/application/knowledge/service.go"}
	default:
		return nil
	}
}

func extractPythonRouteStaticErrorDetails(t *testing.T, filename string) map[string]map[string]bool {
	t.Helper()
	source := readFile(t, filename)
	matches := pythonDecoratorRE.FindAllStringSubmatchIndex(source, -1)
	details := map[string]map[string]bool{}
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
		details[key] = pythonHTTPExceptionStaticDetails(t, source[match[0]:blockEnd])
	}
	return details
}

func pythonHTTPExceptionStaticDetails(t *testing.T, block string) map[string]bool {
	t.Helper()
	details := map[string]bool{}
	for _, match := range httpExceptionRE.FindAllStringIndex(block, -1) {
		open := match[1] - 1
		close := matchingParen(block, open)
		if close < 0 {
			t.Fatalf("HTTPException call with unmatched parentheses")
		}
		expression, ok := namedArgumentExpression(block[open+1:close], "detail")
		if !ok {
			continue
		}
		value, ok := pythonStaticStringLiteral(expression)
		if ok {
			details[value] = true
		}
	}
	return details
}

func namedArgumentExpression(arguments string, name string) (string, bool) {
	index := strings.Index(arguments, name)
	if index < 0 {
		return "", false
	}
	index += len(name)
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

func pythonStaticStringLiteral(expression string) (string, bool) {
	expression = strings.TrimSpace(expression)
	if strings.HasPrefix(expression, "f\"") || strings.HasPrefix(expression, "f'") {
		return "", false
	}
	if len(expression) < 2 {
		return "", false
	}
	quote := expression[0]
	if (quote != '"' && quote != '\'') || expression[len(expression)-1] != quote {
		return "", false
	}
	if quote == '\'' {
		expression = `"` + strings.ReplaceAll(expression[1:len(expression)-1], `"`, `\"`) + `"`
	}
	value, err := strconv.Unquote(expression)
	if err != nil {
		return "", false
	}
	return value, true
}

func extractGoRouteReachableMessages(t *testing.T, filename string) map[string]map[string]bool {
	t.Helper()
	source := readFile(t, filename)
	messages := map[string]map[string]bool{}
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
		messages[routeItem.Method+" "+routeItem.Path] = collectGoReachableMessages(t, source, handlerName, map[string]bool{})
	}
	return messages
}

func collectGoReachableMessages(t *testing.T, source string, functionName string, visited map[string]bool) map[string]bool {
	t.Helper()
	if visited[functionName] {
		return map[string]bool{}
	}
	visited[functionName] = true
	body := goStatusFunctionBody(t, source, functionName)
	messages := extractGoStringLiterals(t, body)
	for _, match := range goDelegatedMethodCallRE.FindAllStringSubmatch(body, -1) {
		if len(match) == 2 {
			mergeMessages(messages, collectGoReachableMessages(t, source, match[1], visited))
		}
	}
	for _, match := range goFunctionStatusCallRE.FindAllStringSubmatch(body, -1) {
		if len(match) != 2 || !isGoStatusHelper(match[1]) || !goFunctionExists(source, match[1]) {
			continue
		}
		mergeMessages(messages, collectGoReachableMessages(t, source, match[1], visited))
	}
	return messages
}

func extractGoStringLiterals(t *testing.T, source string) map[string]bool {
	t.Helper()
	values := map[string]bool{}
	for _, literal := range goStringLiteralRE.FindAllString(source, -1) {
		value, err := strconv.Unquote(literal)
		if err != nil {
			t.Fatalf("parse Go string literal %s: %v", literal, err)
		}
		values[value] = true
	}
	return values
}

func extractGoStringLiteralsFromFiles(t *testing.T, root string, filenames []string) map[string]bool {
	t.Helper()
	values := map[string]bool{}
	for _, filename := range filenames {
		mergeMessages(values, extractGoStringLiterals(t, readFile(t, filepath.Join(root, filename))))
	}
	return values
}

func mergeMessages(left, right map[string]bool) {
	for message := range right {
		left[message] = true
	}
}
