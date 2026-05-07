package auth

import (
	"context"
	"testing"
	"time"
)

func TestRefreshSessionStoreLocalFallbackConsumesOnce(t *testing.T) {
	now := time.Date(2026, 5, 7, 12, 0, 0, 0, time.UTC)
	store := NewRefreshSessionStore(nil, nil)
	store.now = func() time.Time { return now }

	if err := store.Remember(context.Background(), "user-1", "jti-1", now.Add(time.Hour)); err != nil {
		t.Fatalf("Remember() error = %v", err)
	}
	active, err := store.Consume(context.Background(), "user-1", "jti-1")
	if err != nil {
		t.Fatalf("Consume() error = %v", err)
	}
	if !active {
		t.Fatal("Consume() active = false, want true")
	}
	active, err = store.Consume(context.Background(), "user-1", "jti-1")
	if err != nil {
		t.Fatalf("Consume(reuse) error = %v", err)
	}
	if active {
		t.Fatal("Consume(reuse) active = true, want false")
	}
}

func TestRefreshSessionStoreStrictRequiresRedis(t *testing.T) {
	now := time.Date(2026, 5, 7, 12, 0, 0, 0, time.UTC)
	store := NewRefreshSessionStore(nil, nil, WithStrictRefreshSessions(true))
	store.now = func() time.Time { return now }

	if err := store.Remember(context.Background(), "user-1", "jti-1", now.Add(time.Hour)); err == nil {
		t.Fatal("Remember(strict without redis) error = nil, want error")
	}
	if _, err := store.Consume(context.Background(), "user-1", "jti-1"); err == nil {
		t.Fatal("Consume(strict without redis) error = nil, want error")
	}
	if err := store.Revoke(context.Background(), "jti-1"); err == nil {
		t.Fatal("Revoke(strict without redis) error = nil, want error")
	}
}
