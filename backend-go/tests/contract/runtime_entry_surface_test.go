package contract

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

type runtimeEntryExpectation struct {
	File    string
	Require []string
	Forbid  []string
}

func TestDefaultRuntimeEntriesStayOnGoBackend(t *testing.T) {
	root := repoRoot(t)
	expectations := []runtimeEntryExpectation{
		{
			File: "start.bat",
			Require: []string{
				"backend-go",
				"go run ./cmd/api",
			},
			Forbid: []string{
				"uvicorn",
				"alembic",
				"backend/app/main.py",
			},
		},
		{
			File: "docker-compose.yml",
			Require: []string{
				"context: ./backend-go",
				"backend-go",
				"GO_API_PORT=8000",
			},
			Forbid: []string{
				"uvicorn",
				"alembic upgrade",
				"backend/Dockerfile",
			},
		},
		{
			File: "backend-go/Dockerfile",
			Require: []string{
				"msp-api",
				"msp-migrate",
				`CMD ["msp-api"]`,
			},
			Forbid: []string{
				"uvicorn",
				"alembic",
				"python",
			},
		},
		{
			File: "scripts/deploy.sh",
			Require: []string{
				"backend-go:latest",
				"msp-migrate",
				"up -d backend frontend",
			},
			Forbid: []string{
				"uvicorn",
				"alembic upgrade",
				"backend/Dockerfile",
			},
		},
		{
			File: "scripts/update.sh",
			Require: []string{
				"backend-go:${VERSION}",
				"msp-migrate",
				"up -d backend frontend",
			},
			Forbid: []string{
				"uvicorn",
				"alembic upgrade",
				"backend/Dockerfile",
			},
		},
		{
			File: "frontend/nginx.conf",
			Require: []string{
				"proxy_pass http://backend:8000",
			},
			Forbid: []string{
				"uvicorn",
				"backend-python",
			},
		},
		{
			File: "nginx-site.conf",
			Require: []string{
				"proxy_pass http://localhost:8000",
			},
			Forbid: []string{
				"uvicorn",
				"backend-python",
			},
		},
	}

	for _, expectation := range expectations {
		t.Run(expectation.File, func(t *testing.T) {
			source := readFile(t, filepath.Join(root, expectation.File))
			sourceLower := strings.ToLower(source)
			for _, required := range expectation.Require {
				if !strings.Contains(source, required) {
					t.Fatalf("%s must contain %q", expectation.File, required)
				}
			}
			for _, forbidden := range expectation.Forbid {
				if strings.Contains(sourceLower, strings.ToLower(forbidden)) {
					t.Fatalf("%s must not contain default Python backend runtime marker %q", expectation.File, forbidden)
				}
			}
		})
	}
}

func TestLegacyPythonBackendDirectoryIsAbsent(t *testing.T) {
	root := repoRoot(t)
	legacyPath := filepath.Join(root, "backend")
	if _, err := os.Stat(legacyPath); err == nil {
		t.Fatalf("legacy Python backend directory must stay removed: %s", legacyPath)
	} else if !os.IsNotExist(err) {
		t.Fatalf("stat legacy Python backend directory: %v", err)
	}
}
