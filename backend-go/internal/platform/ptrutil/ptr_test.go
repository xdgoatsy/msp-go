package ptrutil

import "testing"

func TestClone(t *testing.T) {
	source := "value"
	got := Clone(&source)

	if got == nil || *got != "value" {
		t.Fatalf("Clone() = %#v, want pointer to value", got)
	}
	*got = "changed"
	if source != "value" {
		t.Fatalf("Clone() did not copy pointed value")
	}
}

func TestCloneNil(t *testing.T) {
	if got := Clone[string](nil); got != nil {
		t.Fatalf("Clone(nil) = %#v, want nil", got)
	}
}
