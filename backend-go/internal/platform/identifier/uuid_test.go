package identifier

import (
	"bytes"
	"errors"
	"io"
	"regexp"
	"testing"
)

func TestNewUUIDReturnsRFC4122Version4Value(t *testing.T) {
	restore := replaceUUIDRandomReader(bytes.NewReader([]byte{
		0x00, 0x01, 0x02, 0x03,
		0x04, 0x05,
		0x06, 0x07,
		0x08, 0x09,
		0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f,
	}))
	defer restore()

	got, err := NewUUID()
	if err != nil {
		t.Fatalf("NewUUID() error = %v", err)
	}
	if got != "00010203-0405-4607-8809-0a0b0c0d0e0f" {
		t.Fatalf("NewUUID() = %q", got)
	}
	if !regexp.MustCompile(`^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`).MatchString(got) {
		t.Fatalf("NewUUID() is not an RFC 4122 v4 UUID: %q", got)
	}
}

func TestNewUUIDReturnsRandomReaderError(t *testing.T) {
	want := errors.New("entropy unavailable")
	restore := replaceUUIDRandomReader(errReader{err: want})
	defer restore()

	got, err := NewUUID()
	if !errors.Is(err, want) {
		t.Fatalf("NewUUID() error = %v, want %v", err, want)
	}
	if got != "" {
		t.Fatalf("NewUUID() = %q, want empty value", got)
	}
}

func TestNewUUIDReturnsShortReaderError(t *testing.T) {
	restore := replaceUUIDRandomReader(bytes.NewReader([]byte{0x01, 0x02}))
	defer restore()

	got, err := NewUUID()
	if !errors.Is(err, io.ErrUnexpectedEOF) {
		t.Fatalf("NewUUID() error = %v, want %v", err, io.ErrUnexpectedEOF)
	}
	if got != "" {
		t.Fatalf("NewUUID() = %q, want empty value", got)
	}
}

func replaceUUIDRandomReader(reader io.Reader) func() {
	previous := uuidRandomReader
	uuidRandomReader = reader
	return func() {
		uuidRandomReader = previous
	}
}

type errReader struct {
	err error
}

func (r errReader) Read([]byte) (int, error) {
	return 0, r.err
}
