package upload

import (
	"context"
	"crypto/rand"
	"errors"
	"fmt"
	"io"
	"strings"
)

const (
	// MaxImageSize keeps parity with the Python image upload limit.
	MaxImageSize = 10 * 1024 * 1024
	// MaxResourceSize keeps parity with the Python video/document upload limit.
	MaxResourceSize = 500 * 1024 * 1024
)

var (
	// ErrInvalidContentType is returned when a file MIME type is not allowed.
	ErrInvalidContentType = errors.New("invalid content type")
	// ErrFileTooLarge is returned when a file exceeds its endpoint limit.
	ErrFileTooLarge = errors.New("file too large")
)

// Storage persists uploaded bytes and returns an externally usable URL.
type Storage interface {
	UploadStream(context.Context, io.Reader, string, string, int64) (StoredObject, error)
}

// StoredObject stores the result returned by a storage adapter.
type StoredObject struct {
	Key         string
	URL         string
	Size        int64
	ContentType string
}

// FileMeta stores trusted metadata supplied by the HTTP multipart layer.
type FileMeta struct {
	ContentType string
	Size        int64
}

// Response is the Python-compatible upload response.
type Response struct {
	FileID      string `json:"file_id"`
	URL         string `json:"url"`
	Filename    string `json:"filename"`
	ContentType string `json:"content_type"`
	Size        int64  `json:"size"`
}

// Service validates and stores uploaded files.
type Service struct {
	storage Storage
	newID   func() (string, error)
}

// NewService creates an upload service.
func NewService(storage Storage) (*Service, error) {
	if storage == nil {
		return nil, errors.New("upload storage is nil")
	}
	return &Service{storage: storage, newID: newUUID}, nil
}

// SaveImage validates and stores one image file.
func (s *Service) SaveImage(ctx context.Context, reader io.Reader, meta FileMeta) (Response, error) {
	return s.save(ctx, reader, meta, allowedImageTypes(), MaxImageSize, "images")
}

// SaveResourceFile validates and stores one video or document resource.
func (s *Service) SaveResourceFile(ctx context.Context, reader io.Reader, meta FileMeta) (Response, error) {
	prefix := "documents"
	if strings.HasPrefix(strings.ToLower(strings.TrimSpace(meta.ContentType)), "video/") {
		prefix = "videos"
	}
	return s.save(ctx, reader, meta, allowedResourceTypes(), MaxResourceSize, prefix)
}

func (s *Service) save(ctx context.Context, reader io.Reader, meta FileMeta, allowed map[string]string, maxSize int64, prefix string) (Response, error) {
	contentType := strings.ToLower(strings.TrimSpace(meta.ContentType))
	extension, ok := allowed[contentType]
	if !ok {
		return Response{}, ErrInvalidContentType
	}
	if meta.Size > maxSize {
		return Response{}, ErrFileTooLarge
	}
	if reader == nil {
		return Response{}, errors.New("upload reader is nil")
	}
	fileID, err := s.newID()
	if err != nil {
		return Response{}, err
	}
	filename := fileID + extension
	key := prefix + "/" + filename
	limited := &maxBytesReader{reader: reader, remaining: maxSize}
	counted := &countingReader{reader: limited}
	stored, err := s.storage.UploadStream(ctx, counted, key, contentType, meta.Size)
	if err != nil {
		return Response{}, err
	}
	size := stored.Size
	if size == 0 && counted.n > 0 {
		size = counted.n
	}
	return Response{
		FileID:      fileID,
		URL:         stored.URL,
		Filename:    filename,
		ContentType: contentType,
		Size:        size,
	}, nil
}

type maxBytesReader struct {
	reader    io.Reader
	remaining int64
}

func (r *maxBytesReader) Read(p []byte) (int, error) {
	if r.remaining <= 0 {
		var probe [1]byte
		n, err := r.reader.Read(probe[:])
		if n > 0 {
			return 0, ErrFileTooLarge
		}
		return 0, err
	}
	if int64(len(p)) > r.remaining {
		p = p[:r.remaining]
	}
	n, err := r.reader.Read(p)
	r.remaining -= int64(n)
	return n, err
}

type countingReader struct {
	reader io.Reader
	n      int64
}

func (r *countingReader) Read(p []byte) (int, error) {
	n, err := r.reader.Read(p)
	r.n += int64(n)
	return n, err
}

func allowedImageTypes() map[string]string {
	return map[string]string{
		"image/jpeg": ".jpg",
		"image/png":  ".png",
		"image/gif":  ".gif",
		"image/webp": ".webp",
	}
}

func allowedResourceTypes() map[string]string {
	return map[string]string{
		"video/mp4":          ".mp4",
		"video/avi":          ".avi",
		"video/quicktime":    ".mov",
		"video/x-matroska":   ".mkv",
		"video/webm":         ".webm",
		"application/pdf":    ".pdf",
		"application/msword": ".doc",
		"application/vnd.openxmlformats-officedocument.wordprocessingml.document":   ".docx",
		"application/vnd.ms-powerpoint":                                             ".ppt",
		"application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
		"text/plain":    ".txt",
		"text/markdown": ".md",
	}
}

func newUUID() (string, error) {
	var data [16]byte
	if _, err := rand.Read(data[:]); err != nil {
		return "", err
	}
	data[6] = (data[6] & 0x0f) | 0x40
	data[8] = (data[8] & 0x3f) | 0x80
	return fmt.Sprintf("%08x-%04x-%04x-%04x-%012x",
		data[0:4],
		data[4:6],
		data[6:8],
		data[8:10],
		data[10:16],
	), nil
}
