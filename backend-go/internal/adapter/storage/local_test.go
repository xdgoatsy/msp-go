package storage

import (
	"context"
	"os"
	"path/filepath"
	"testing"
)

func TestLocalStorageWritesFileAndReturnsUploadsURL(t *testing.T) {
	root := t.TempDir()
	storage := NewLocalStorage(root)

	object, err := storage.UploadData(context.Background(), []byte("data"), "images/file.png", "image/png")
	if err != nil {
		t.Fatalf("UploadData() error = %v", err)
	}
	if object.Key != "images/file.png" || object.URL != "/uploads/images/file.png" || object.Size != 4 || object.ContentType != "image/png" {
		t.Fatalf("object = %#v", object)
	}
	data, err := os.ReadFile(filepath.Join(root, "images", "file.png"))
	if err != nil {
		t.Fatalf("ReadFile() error = %v", err)
	}
	if string(data) != "data" {
		t.Fatalf("file data = %q", data)
	}
}

func TestLocalStorageRejectsPathTraversal(t *testing.T) {
	storage := NewLocalStorage(t.TempDir())
	if _, err := storage.UploadData(context.Background(), []byte("data"), "../outside.txt", "text/plain"); err == nil {
		t.Fatal("UploadData(path traversal) error = nil, want error")
	}
	if _, err := storage.UploadData(context.Background(), []byte("data"), `images\..\outside.txt`, "text/plain"); err == nil {
		t.Fatal("UploadData(backslash traversal) error = nil, want error")
	}
}

func TestCleanObjectKeyNormalizesRedundantSeparators(t *testing.T) {
	key, err := cleanObjectKey("/images//nested/./file.png")
	if err != nil {
		t.Fatalf("cleanObjectKey() error = %v", err)
	}
	if key != "images/nested/file.png" {
		t.Fatalf("key = %q", key)
	}
}
