package maputil

import (
	"reflect"
	"testing"
)

func TestSortedFloatKeys(t *testing.T) {
	got := SortedFloatKeys(map[string]float64{
		"gamma": 0.3,
		"alpha": 0.1,
		"beta":  0.2,
	})
	want := []string{"alpha", "beta", "gamma"}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("SortedFloatKeys() = %#v, want %#v", got, want)
	}
}

func TestSortedFloatKeysEmpty(t *testing.T) {
	got := SortedFloatKeys(nil)
	if got == nil {
		t.Fatal("SortedFloatKeys(nil) = nil, want empty slice")
	}
	if len(got) != 0 {
		t.Fatalf("SortedFloatKeys(nil) len = %d, want 0", len(got))
	}
}
