package xidian

import (
	"context"
	"errors"
	"testing"
	"time"
)

func TestBindingStatusReturnsUnboundAndBoundState(t *testing.T) {
	repo := &fakeRepo{}
	service := newTestService(repo, &fakePortal{}, &fakeCipher{})

	status, err := service.GetBindingStatus(context.Background(), "user-1")
	if err != nil {
		t.Fatalf("GetBindingStatus(unbound) error = %v", err)
	}
	if status.IsBound {
		t.Fatalf("status = %#v", status)
	}

	isPG := true
	verified := time.Date(2026, 5, 6, 9, 0, 0, 0, time.UTC)
	synced := time.Date(2026, 5, 6, 10, 0, 0, 0, time.UTC)
	repo.account = Account{UserID: "user-1", Username: "student", IsPostgraduate: &isPG, LastVerifiedAt: &verified}
	repo.accountFound = true
	repo.latestSyncAt = &synced
	status, err = service.GetBindingStatus(context.Background(), "user-1")
	if err != nil {
		t.Fatalf("GetBindingStatus(bound) error = %v", err)
	}
	if !status.IsBound || *status.Username != "student" || !*status.IsPostgraduate || !status.LastSyncAt.Equal(synced) {
		t.Fatalf("status = %#v", status)
	}
}

func TestStartAndCompleteBindingStoresAccount(t *testing.T) {
	portal := &fakePortal{
		challenge: Challenge{CaptchaBig: "big", CaptchaPiece: "piece", PieceY: 12, State: ChallengeState{PasswordSalt: "salt"}},
		login:     LoginResult{Cookies: []Cookie{{"name": "sid", "value": "1"}}},
	}
	cipher := &fakeCipher{}
	repo := &fakeRepo{}
	service := newTestService(repo, portal, cipher)
	service.newID = func() string { return "challenge-1" }
	now := time.Date(2026, 5, 6, 10, 0, 0, 0, time.UTC)
	service.now = func() time.Time { return now }

	start, err := service.StartBinding(context.Background())
	if err != nil {
		t.Fatalf("StartBinding() error = %v", err)
	}
	if start.ChallengeID != "challenge-1" || start.PuzzleWidth != 280 || start.PieceY != 12 {
		t.Fatalf("start = %#v", start)
	}
	username := "student"
	password := "password"
	complete, err := service.CompleteBinding(context.Background(), "user-1", CompleteBindingInput{
		ChallengeID:    "challenge-1",
		SliderPosition: 0.5,
		Username:       &username,
		Password:       &password,
	})
	if err != nil {
		t.Fatalf("CompleteBinding() error = %v", err)
	}
	if !complete.IsBound || complete.Username != "student" {
		t.Fatalf("complete = %#v", complete)
	}
	if repo.upsert.Username != "student" || repo.upsert.EncryptedPassword != "enc:password" || len(repo.upsert.SessionCookies) != 1 {
		t.Fatalf("upsert = %#v", repo.upsert)
	}
	if portal.loginInput.Username != "student" || portal.loginInput.Password != "password" || portal.loginInput.SliderPosition != 0.5 {
		t.Fatalf("login input = %#v", portal.loginInput)
	}
}

func TestCompleteBindingReusesStoredPassword(t *testing.T) {
	repo := &fakeRepo{accountFound: true, account: Account{Username: "student", EncryptedPassword: "enc:stored"}}
	portal := &fakePortal{login: LoginResult{}}
	service := newTestService(repo, portal, &fakeCipher{})
	service.newID = func() string { return "challenge-1" }
	_, err := service.StartBinding(context.Background())
	if err != nil {
		t.Fatalf("StartBinding() error = %v", err)
	}
	_, err = service.CompleteBinding(context.Background(), "user-1", CompleteBindingInput{ChallengeID: "challenge-1", SliderPosition: 0.2})
	if err != nil {
		t.Fatalf("CompleteBinding() error = %v", err)
	}
	if portal.loginInput.Username != "student" || portal.loginInput.Password != "stored" {
		t.Fatalf("login input = %#v", portal.loginInput)
	}
}

func TestSyncSavesSnapshotAndCookies(t *testing.T) {
	repo := &fakeRepo{accountFound: true, account: Account{Username: "student", SessionCookies: []Cookie{{"name": "sid", "value": "old"}}}}
	portal := &fakePortal{syncResult: SyncResult{Payload: map[string]any{"semester_code": "2025-2026-2", "scores": []any{}}, Cookies: []Cookie{{"name": "sid", "value": "new"}}}}
	service := newTestService(repo, portal, &fakeCipher{})
	service.newID = func() string { return "snapshot-1" }
	now := time.Date(2026, 5, 6, 10, 0, 0, 0, time.UTC)
	service.now = func() time.Time { return now }

	response, err := service.SyncScores(context.Background(), "user-1")
	if err != nil {
		t.Fatalf("SyncScores() error = %v", err)
	}
	if response.IsCached || !response.FetchedAt.Equal(now) {
		t.Fatalf("response = %#v", response)
	}
	if repo.snapshot.ID != "snapshot-1" || repo.snapshot.DataType != "score" || *repo.snapshot.SemesterCode != "2025-2026-2" {
		t.Fatalf("snapshot = %#v", repo.snapshot)
	}
	if repo.updatedCookies[0]["value"] != "new" {
		t.Fatalf("cookies = %#v", repo.updatedCookies)
	}
}

func TestSyncFallsBackToSnapshot(t *testing.T) {
	fetchedAt := time.Date(2026, 5, 5, 9, 0, 0, 0, time.UTC)
	repo := &fakeRepo{
		accountFound:  true,
		account:       Account{Username: "student"},
		snapshotFound: true,
		snapshotValue: Snapshot{Payload: map[string]any{"scores": []any{"cached"}}, FetchedAt: fetchedAt},
	}
	portal := &fakePortal{syncErr: ServiceError{Code: "CAPTCHA_REQUIRED", Message: "会话已过期，请重新验证", Status: 409}}
	service := newTestService(repo, portal, &fakeCipher{})

	response, err := service.SyncScores(context.Background(), "user-1")
	if err != nil {
		t.Fatalf("SyncScores() error = %v", err)
	}
	if !response.IsCached || response.Data["is_cached"] != true || response.Data["cached_at"] == nil {
		t.Fatalf("response = %#v", response)
	}
}

func TestServiceErrors(t *testing.T) {
	service := newTestService(&fakeRepo{}, &fakePortal{}, &fakeCipher{})
	var serviceErr ServiceError
	if _, err := service.SyncScores(context.Background(), "user-1"); !errors.As(err, &serviceErr) {
		t.Fatalf("SyncScores() error = %v, want ServiceError", err)
	}
	if _, err := service.GetSnapshot(context.Background(), "user-1", "score"); !errors.As(err, &serviceErr) {
		t.Fatalf("GetSnapshot() error = %v, want ServiceError", err)
	}
	if _, err := NewService(nil, &fakePortal{}, &fakeCipher{}, NewMemoryChallengeStore(), Config{ChallengeTTL: time.Minute, CaptchaWidth: 1, CaptchaHeight: 1, PieceWidth: 1, PieceHeight: 1}); err == nil {
		t.Fatal("NewService(nil repo) error = nil, want error")
	}
}

func newTestService(repo Repository, portal PortalClient, cipher Cipher) *Service {
	service, err := NewService(repo, portal, cipher, NewMemoryChallengeStore(), Config{
		ChallengeTTL:            time.Minute,
		SnapshotFallbackEnabled: true,
		CaptchaWidth:            280,
		CaptchaHeight:           155,
		PieceWidth:              44,
		PieceHeight:             155,
	})
	if err != nil {
		panic(err)
	}
	return service
}

type fakeRepo struct {
	account        Account
	accountFound   bool
	upsert         AccountUpsert
	latestSyncAt   *time.Time
	snapshot       SnapshotInput
	snapshotValue  Snapshot
	snapshotFound  bool
	updatedCookies []Cookie
}

func (r *fakeRepo) GetAccount(context.Context, string) (Account, bool, error) {
	return r.account, r.accountFound, nil
}

func (r *fakeRepo) UpsertAccount(_ context.Context, input AccountUpsert) (Account, error) {
	r.upsert = input
	verified := input.LastVerifiedAt
	return Account{Username: input.Username, IsPostgraduate: input.IsPostgraduate, LastVerifiedAt: &verified}, nil
}

func (r *fakeRepo) DeleteAccountAndSnapshots(context.Context, string) error { return nil }

func (r *fakeRepo) LatestSyncAt(context.Context, string) (*time.Time, error) {
	return r.latestSyncAt, nil
}

func (r *fakeRepo) SaveSnapshot(_ context.Context, input SnapshotInput) error {
	r.snapshot = input
	return nil
}

func (r *fakeRepo) LatestSnapshot(context.Context, string, string) (Snapshot, bool, error) {
	return r.snapshotValue, r.snapshotFound, nil
}

func (r *fakeRepo) UpdateCookies(_ context.Context, _ string, cookies []Cookie, _ time.Time) error {
	r.updatedCookies = cookies
	return nil
}

type fakePortal struct {
	challenge  Challenge
	login      LoginResult
	loginInput LoginInput
	syncResult SyncResult
	syncErr    error
}

func (p *fakePortal) StartBinding(context.Context) (Challenge, error) {
	if p.challenge.State.PasswordSalt == "" {
		p.challenge.State.PasswordSalt = "salt"
	}
	return p.challenge, nil
}

func (p *fakePortal) CompleteBinding(_ context.Context, _ ChallengeState, input LoginInput) (LoginResult, error) {
	p.loginInput = input
	return p.login, nil
}

func (p *fakePortal) Sync(context.Context, SyncRequest) (SyncResult, error) {
	if p.syncErr != nil {
		return SyncResult{}, p.syncErr
	}
	return p.syncResult, nil
}

type fakeCipher struct{}

func (c *fakeCipher) Encrypt(value string) (string, error) { return "enc:" + value, nil }

func (c *fakeCipher) Decrypt(value string) (string, error) {
	if len(value) >= 4 && value[:4] == "enc:" {
		return value[4:], nil
	}
	return "", nil
}
