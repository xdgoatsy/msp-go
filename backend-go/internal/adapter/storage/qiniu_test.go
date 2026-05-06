package storage

import (
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"testing"
	"time"
)

func TestQiniuStorageUploadsMultipartData(t *testing.T) {
	var fields url.Values
	var fileData string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if err := r.ParseMultipartForm(1 << 20); err != nil {
			t.Fatalf("ParseMultipartForm() error = %v", err)
		}
		fields = url.Values(r.MultipartForm.Value)
		file, _, err := r.FormFile("file")
		if err != nil {
			t.Fatalf("FormFile() error = %v", err)
		}
		defer file.Close()
		data, _ := io.ReadAll(file)
		fileData = string(data)
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"key":"images/file.png"}`))
	}))
	defer server.Close()

	storage, err := NewQiniuStorage(QiniuConfig{
		AccessKey:  "access",
		SecretKey:  "secret",
		BucketName: "bucket",
		Domain:     "https://cdn.example.com",
		UploadURL:  server.URL,
	}, server.Client())
	if err != nil {
		t.Fatalf("NewQiniuStorage() error = %v", err)
	}
	storage.now = func() time.Time { return time.Date(2026, time.May, 6, 10, 0, 0, 0, time.UTC) }

	object, err := storage.UploadData(context.Background(), []byte("data"), "images/file.png", "image/png")
	if err != nil {
		t.Fatalf("UploadData() error = %v", err)
	}
	if fields.Get("key") != "images/file.png" || fields.Get("token") == "" || fileData != "data" {
		t.Fatalf("fields = %#v fileData = %q", fields, fileData)
	}
	if object.URL != "https://cdn.example.com/images/file.png" || object.Size != 4 {
		t.Fatalf("object = %#v", object)
	}
}

func TestQiniuStorageReturnsPrivateDownloadURL(t *testing.T) {
	storage, err := NewQiniuStorage(QiniuConfig{
		AccessKey:     "access",
		SecretKey:     "secret",
		BucketName:    "bucket",
		Domain:        "https://cdn.example.com",
		PrivateBucket: true,
		URLExpire:     time.Hour,
		UploadURL:     "https://upload.qiniup.com",
	}, http.DefaultClient)
	if err != nil {
		t.Fatalf("NewQiniuStorage() error = %v", err)
	}
	storage.now = func() time.Time { return time.Date(2026, time.May, 6, 10, 0, 0, 0, time.UTC) }

	url := storage.downloadURL("documents/file.pdf")
	if !strings.HasPrefix(url, "https://cdn.example.com/documents/file.pdf?e=") || !strings.Contains(url, "&token=access:") {
		t.Fatalf("url = %q", url)
	}
}

func TestQiniuStorageRejectsMissingConfig(t *testing.T) {
	if _, err := NewQiniuStorage(QiniuConfig{}, http.DefaultClient); err == nil {
		t.Fatal("NewQiniuStorage(empty) error = nil, want error")
	}
}
