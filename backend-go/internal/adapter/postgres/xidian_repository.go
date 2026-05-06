package postgres

import (
	"context"
	"encoding/json"
	"time"

	"github.com/jackc/pgx/v5"

	xidianapp "mathstudy/backend-go/internal/application/xidian"
)

// XidianRepository persists Xidian account bindings and snapshots.
type XidianRepository struct {
	Repository
}

// NewXidianRepository creates a PostgreSQL-backed Xidian repository.
func NewXidianRepository(db Querier) (XidianRepository, error) {
	base, err := NewRepository(db)
	if err != nil {
		return XidianRepository{}, err
	}
	return XidianRepository{Repository: base}, nil
}

// GetAccount loads the Xidian account bound to userID.
func (r XidianRepository) GetAccount(ctx context.Context, userID string) (xidianapp.Account, bool, error) {
	row := r.DB().QueryRow(ctx, `
		SELECT id, user_id, username, encrypted_password, is_postgraduate, status,
			session_cookies, cookies_updated_at, last_verified_at, created_at, updated_at
		FROM public.xidian_accounts
		WHERE user_id = $1`,
		userID,
	)
	account, err := scanXidianAccount(row)
	if err != nil {
		if err == pgx.ErrNoRows {
			return xidianapp.Account{}, false, nil
		}
		return xidianapp.Account{}, false, err
	}
	return account, true, nil
}

// UpsertAccount inserts or updates one Xidian account binding.
func (r XidianRepository) UpsertAccount(ctx context.Context, input xidianapp.AccountUpsert) (xidianapp.Account, error) {
	cookiesJSON, err := json.Marshal(input.SessionCookies)
	if err != nil {
		return xidianapp.Account{}, err
	}
	row := r.DB().QueryRow(ctx, `
		INSERT INTO public.xidian_accounts (
			id, user_id, username, encrypted_password, is_postgraduate, status,
			session_cookies, cookies_updated_at, last_verified_at, created_at, updated_at
		)
		VALUES ($1, $2, $3, $4, $5, 'active', $6, $7, $8, $9, $9)
		ON CONFLICT (user_id) DO UPDATE
		SET username = EXCLUDED.username,
			encrypted_password = EXCLUDED.encrypted_password,
			is_postgraduate = EXCLUDED.is_postgraduate,
			status = 'active',
			session_cookies = EXCLUDED.session_cookies,
			cookies_updated_at = EXCLUDED.cookies_updated_at,
			last_verified_at = EXCLUDED.last_verified_at,
			updated_at = EXCLUDED.updated_at
		RETURNING id, user_id, username, encrypted_password, is_postgraduate, status,
			session_cookies, cookies_updated_at, last_verified_at, created_at, updated_at`,
		input.ID,
		input.UserID,
		input.Username,
		input.EncryptedPassword,
		input.IsPostgraduate,
		cookiesJSON,
		input.Now,
		input.LastVerifiedAt,
		input.Now,
	)
	return scanXidianAccount(row)
}

// DeleteAccountAndSnapshots removes the binding and cached snapshots for a user.
func (r XidianRepository) DeleteAccountAndSnapshots(ctx context.Context, userID string) error {
	if _, err := r.DB().Exec(ctx, `DELETE FROM public.xidian_snapshots WHERE user_id = $1`, userID); err != nil {
		return err
	}
	_, err := r.DB().Exec(ctx, `DELETE FROM public.xidian_accounts WHERE user_id = $1`, userID)
	return err
}

// LatestSyncAt returns the latest snapshot time for a user.
func (r XidianRepository) LatestSyncAt(ctx context.Context, userID string) (*time.Time, error) {
	var value *time.Time
	if err := r.DB().QueryRow(ctx, `SELECT max(fetched_at) FROM public.xidian_snapshots WHERE user_id = $1`, userID).Scan(&value); err != nil {
		return nil, err
	}
	return value, nil
}

// SaveSnapshot stores one fetched payload.
func (r XidianRepository) SaveSnapshot(ctx context.Context, input xidianapp.SnapshotInput) error {
	payload, err := json.Marshal(input.Payload)
	if err != nil {
		return err
	}
	_, err = r.DB().Exec(ctx, `
		INSERT INTO public.xidian_snapshots (id, user_id, data_type, semester_code, payload, fetched_at)
		VALUES ($1, $2, $3, $4, $5, $6)`,
		input.ID,
		input.UserID,
		input.DataType,
		input.SemesterCode,
		payload,
		input.FetchedAt,
	)
	return err
}

// LatestSnapshot returns the latest cached payload for userID and dataType.
func (r XidianRepository) LatestSnapshot(ctx context.Context, userID string, dataType string) (xidianapp.Snapshot, bool, error) {
	row := r.DB().QueryRow(ctx, `
		SELECT id, user_id, data_type, semester_code, payload, fetched_at
		FROM public.xidian_snapshots
		WHERE user_id = $1 AND data_type = $2
		ORDER BY fetched_at DESC
		LIMIT 1`,
		userID,
		dataType,
	)
	snapshot, err := scanXidianSnapshot(row)
	if err != nil {
		if err == pgx.ErrNoRows {
			return xidianapp.Snapshot{}, false, nil
		}
		return xidianapp.Snapshot{}, false, err
	}
	return snapshot, true, nil
}

// UpdateCookies refreshes persisted portal cookies.
func (r XidianRepository) UpdateCookies(ctx context.Context, userID string, cookies []xidianapp.Cookie, now time.Time) error {
	cookiesJSON, err := json.Marshal(cookies)
	if err != nil {
		return err
	}
	_, err = r.DB().Exec(ctx, `
		UPDATE public.xidian_accounts
		SET session_cookies = $2, cookies_updated_at = $3, updated_at = $3
		WHERE user_id = $1`,
		userID,
		cookiesJSON,
		now,
	)
	return err
}

func scanXidianAccount(row pgx.Row) (xidianapp.Account, error) {
	var account xidianapp.Account
	var cookiesData []byte
	if err := row.Scan(
		&account.ID,
		&account.UserID,
		&account.Username,
		&account.EncryptedPassword,
		&account.IsPostgraduate,
		&account.Status,
		&cookiesData,
		&account.CookiesUpdatedAt,
		&account.LastVerifiedAt,
		&account.CreatedAt,
		&account.UpdatedAt,
	); err != nil {
		return xidianapp.Account{}, err
	}
	if len(cookiesData) > 0 {
		if err := json.Unmarshal(cookiesData, &account.SessionCookies); err != nil {
			return xidianapp.Account{}, err
		}
	}
	return account, nil
}

func scanXidianSnapshot(row pgx.Row) (xidianapp.Snapshot, error) {
	var snapshot xidianapp.Snapshot
	var payloadData []byte
	if err := row.Scan(
		&snapshot.ID,
		&snapshot.UserID,
		&snapshot.DataType,
		&snapshot.SemesterCode,
		&payloadData,
		&snapshot.FetchedAt,
	); err != nil {
		return xidianapp.Snapshot{}, err
	}
	if len(payloadData) > 0 {
		if err := json.Unmarshal(payloadData, &snapshot.Payload); err != nil {
			return xidianapp.Snapshot{}, err
		}
	}
	if snapshot.Payload == nil {
		snapshot.Payload = map[string]any{}
	}
	return snapshot, nil
}
