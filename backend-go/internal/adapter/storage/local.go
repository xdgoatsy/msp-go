package storage

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"strings"

	uploadapp "mathstudy/backend-go/internal/application/upload"
)

// LocalStorage persists uploads under the configured uploads directory.
type LocalStorage struct {
	uploadDir string
}

// NewLocalStorage creates a local filesystem upload adapter.
func NewLocalStorage(uploadDir string) *LocalStorage {
	return &LocalStorage{uploadDir: uploadDir}
}

// UploadData writes one object and returns its Python-compatible /uploads URL.
func (s *LocalStorage) UploadData(_ context.Context, data []byte, key string, contentType string) (uploadapp.StoredObject, error) {
	if strings.TrimSpace(s.uploadDir) == "" {
		return uploadapp.StoredObject{}, errors.New("upload directory is empty")
	}
	cleanKey, err := cleanObjectKey(key)
	if err != nil {
		return uploadapp.StoredObject{}, err
	}
	root, err := filepath.Abs(s.uploadDir)
	if err != nil {
		return uploadapp.StoredObject{}, err
	}
	target := filepath.Join(root, filepath.FromSlash(cleanKey))
	if !isSubpath(root, target) {
		return uploadapp.StoredObject{}, errors.New("upload key escapes upload directory")
	}
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		return uploadapp.StoredObject{}, err
	}
	if err := os.WriteFile(target, data, 0o644); err != nil {
		_ = os.Remove(target)
		return uploadapp.StoredObject{}, err
	}
	return uploadapp.StoredObject{
		Key:         cleanKey,
		URL:         "/uploads/" + cleanKey,
		Size:        int64(len(data)),
		ContentType: contentType,
	}, nil
}

func cleanObjectKey(key string) (string, error) {
	key = strings.TrimSpace(strings.ReplaceAll(key, "\\", "/"))
	key = strings.TrimPrefix(key, "/")
	if key == "" {
		return "", errors.New("upload key is empty")
	}
	parts := strings.Split(key, "/")
	cleaned := make([]string, 0, len(parts))
	for _, part := range parts {
		if part == "" || part == "." {
			continue
		}
		if part == ".." {
			return "", errors.New("upload key contains parent directory segment")
		}
		cleaned = append(cleaned, part)
	}
	if len(cleaned) == 0 {
		return "", errors.New("upload key is empty")
	}
	return strings.Join(cleaned, "/"), nil
}

func isSubpath(root string, target string) bool {
	rel, err := filepath.Rel(root, target)
	if err != nil {
		return false
	}
	return rel == "." || (!strings.HasPrefix(rel, ".."+string(filepath.Separator)) && rel != "..")
}
