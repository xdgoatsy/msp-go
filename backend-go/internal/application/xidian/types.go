package xidian

import "time"

// Cookie is a serializable HTTP cookie representation compatible with Python snapshots.
type Cookie map[string]any

// Account is a bound Xidian account.
type Account struct {
	ID                string
	UserID            string
	Username          string
	EncryptedPassword string
	IsPostgraduate    *bool
	Status            string
	SessionCookies    []Cookie
	CookiesUpdatedAt  *time.Time
	LastVerifiedAt    *time.Time
	CreatedAt         time.Time
	UpdatedAt         time.Time
}

// AccountUpsert stores a successful account binding.
type AccountUpsert struct {
	ID                string
	UserID            string
	Username          string
	EncryptedPassword string
	IsPostgraduate    *bool
	SessionCookies    []Cookie
	LastVerifiedAt    time.Time
	Now               time.Time
}

// Snapshot is one cached academic data payload.
type Snapshot struct {
	ID           string
	UserID       string
	DataType     string
	SemesterCode *string
	Payload      map[string]any
	FetchedAt    time.Time
}

// SnapshotInput stores one fetched payload.
type SnapshotInput struct {
	ID           string
	UserID       string
	DataType     string
	SemesterCode *string
	Payload      map[string]any
	FetchedAt    time.Time
}

// Challenge contains public captcha fields plus private login state.
type Challenge struct {
	CaptchaBig   string
	CaptchaPiece string
	PieceY       int
	State        ChallengeState
}

// ChallengeState is the private state needed to complete IDS login.
type ChallengeState struct {
	ServiceURL   string
	HiddenInputs map[string]string
	PasswordSalt string
	Cookies      []Cookie
	CreatedAt    time.Time
	Raw          map[string]any
}

// LoginInput completes one captcha login.
type LoginInput struct {
	Username       string
	Password       string
	SliderPosition float64
}

// LoginResult is returned after a successful portal login.
type LoginResult struct {
	Cookies        []Cookie
	IsPostgraduate *bool
}

// SyncRequest requests one academic data refresh.
type SyncRequest struct {
	DataType       string
	Username       string
	IsPostgraduate *bool
	Cookies        []Cookie
}

// SyncResult contains a fetched payload and refreshed cookies.
type SyncResult struct {
	Payload map[string]any
	Cookies []Cookie
}

// BindingStatus is returned by GET /xidian/binding.
type BindingStatus struct {
	IsBound        bool       `json:"is_bound"`
	Username       *string    `json:"username,omitempty"`
	IsPostgraduate *bool      `json:"is_postgraduate,omitempty"`
	LastVerifiedAt *time.Time `json:"last_verified_at,omitempty"`
	LastSyncAt     *time.Time `json:"last_sync_at,omitempty"`
}

// BindStartResponse is returned by POST /xidian/binding/start.
type BindStartResponse struct {
	ChallengeID  string `json:"challenge_id"`
	CaptchaBig   string `json:"captcha_big"`
	CaptchaPiece string `json:"captcha_piece"`
	PuzzleWidth  int    `json:"puzzle_width"`
	PuzzleHeight int    `json:"puzzle_height"`
	PieceWidth   int    `json:"piece_width"`
	PieceHeight  int    `json:"piece_height"`
	PieceY       int    `json:"piece_y"`
}

// CompleteBindingInput is parsed from POST /xidian/binding/complete.
type CompleteBindingInput struct {
	ChallengeID    string  `json:"challenge_id"`
	SliderPosition float64 `json:"slider_position"`
	Username       *string `json:"username"`
	Password       *string `json:"password"`
}

// BindCompleteResponse is returned after successful binding.
type BindCompleteResponse struct {
	IsBound        bool       `json:"is_bound"`
	Username       string     `json:"username"`
	IsPostgraduate *bool      `json:"is_postgraduate,omitempty"`
	LastVerifiedAt *time.Time `json:"last_verified_at,omitempty"`
}

// SyncResponse is returned by sync endpoints.
type SyncResponse struct {
	Data      map[string]any `json:"data"`
	FetchedAt time.Time      `json:"fetched_at"`
	IsCached  bool           `json:"is_cached"`
}

// SnapshotResponse is returned by cached snapshot endpoint.
type SnapshotResponse struct {
	Data     map[string]any `json:"data"`
	IsCached bool           `json:"is_cached"`
	CachedAt *string        `json:"cached_at"`
}

// UnbindResponse is returned by POST /xidian/binding/unbind.
type UnbindResponse struct {
	Success bool `json:"success"`
}

// ServiceError carries Python-compatible Xidian error details.
type ServiceError struct {
	Code    string
	Message string
	Status  int
	Err     error
}
