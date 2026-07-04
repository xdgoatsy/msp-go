package maputil

import (
	"reflect"
	"testing"
)

func TestSortedStringKeys(t *testing.T) {
	got := SortedStringKeys(map[string]int{
		"gamma": 3,
		"alpha": 1,
		"beta":  2,
	})
	want := []string{"alpha", "beta", "gamma"}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("SortedStringKeys() = %#v, want %#v", got, want)
	}
}

func TestSortedStringKeysEmpty(t *testing.T) {
	got := SortedStringKeys[int](nil)
	if got == nil {
		t.Fatal("SortedStringKeys(nil) = nil, want empty slice")
	}
	if len(got) != 0 {
		t.Fatalf("SortedStringKeys(nil) len = %d, want 0", len(got))
	}
}
