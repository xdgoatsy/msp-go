package moderation

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"strings"
	"testing"
	"time"

	adminaiconfigapp "mathstudy/backend-go/internal/application/adminaiconfig"
)

func TestNewReviewerValidatesDependencies(t *testing.T) {
	if _, err := NewReviewer(nil); err == nil {
		t.Fatal("NewReviewer(nil) error = nil")
	}
	provider := &fakeRuntimeProvider{}
	if _, err := NewReviewer(provider, doerFunc(nil), doerFunc(nil)); err == nil {
		t.Fatal("NewReviewer(two clients) error = nil")
	}
}

func TestReviewerCallsModerationsEndpointAndParsesScores(t *testing.T) {
	provider := configuredRuntimeProvider()
	var requestURL string
	client := doerFunc(func(req *http.Request) (*http.Response, error) {
		requestURL = req.URL.String()
		if got := req.Header.Get("Authorization"); got != "Bearer api-secret" {
			t.Fatalf("Authorization = %q", got)
		}
		var payload struct {
			Model string `json:"model"`
			Input string `json:"input"`
		}
		if err := json.NewDecoder(req.Body).Decode(&payload); err != nil {
			t.Fatalf("decode request: %v", err)
		}
		if payload.Model != "omni-moderation-latest" || payload.Input != "hello" {
			t.Fatalf("payload = %#v", payload)
		}
		return jsonResponse(http.StatusOK, moderationResponse(safeScores())), nil
	})
	reviewer, err := NewReviewer(provider, client)
	if err != nil {
		t.Fatal(err)
	}

	result, err := reviewer.Review(context.Background(), "  hello  ")
	if err != nil {
		t.Fatalf("Review() error = %v", err)
	}
	if provider.agentType != contentModeratorAgentType || requestURL != "https://api.example.com/v1/moderations" {
		t.Fatalf("agent=%q URL=%q", provider.agentType, requestURL)
	}
	if result.Model != "omni-moderation-latest" || len(result.CategoryScores) != 13 {
		t.Fatalf("result = %#v", result)
	}
}

func TestReviewerRetriesTransientStatusAndRedactsResponseBody(t *testing.T) {
	provider := configuredRuntimeProvider()
	provider.runtime.MaxRetries = 2
	calls := 0
	client := doerFunc(func(*http.Request) (*http.Response, error) {
		calls++
		if calls == 1 {
			return jsonResponse(http.StatusTooManyRequests, `{"error":"upstream-secret"}`), nil
		}
		return jsonResponse(http.StatusOK, moderationResponse(safeScores())), nil
	})
	reviewer, err := NewReviewer(provider, client)
	if err != nil {
		t.Fatal(err)
	}
	reviewer.retryDelay = func(int) time.Duration { return 0 }
	if _, err := reviewer.Review(context.Background(), "hello"); err != nil {
		t.Fatalf("Review() error = %v", err)
	}
	if calls != 2 {
		t.Fatalf("calls = %d, want 2", calls)
	}

	calls = 0
	client = doerFunc(func(*http.Request) (*http.Response, error) {
		calls++
		return jsonResponse(http.StatusBadRequest, `{"error":"api-secret upstream-secret"}`), nil
	})
	reviewer.httpClient = client
	_, err = reviewer.Review(context.Background(), "hello")
	if err == nil {
		t.Fatal("Review(400) error = nil")
	}
	if calls != 1 || strings.Contains(err.Error(), "api-secret") || strings.Contains(err.Error(), "upstream-secret") {
		t.Fatalf("calls=%d error=%q", calls, err)
	}
}

func TestReviewerFailsForMissingConfigAndMalformedResponses(t *testing.T) {
	provider := configuredRuntimeProvider()
	provider.ok = false
	reviewer, err := NewReviewer(provider, doerFunc(func(*http.Request) (*http.Response, error) {
		return nil, errors.New("unexpected call")
	}))
	if err != nil {
		t.Fatal(err)
	}
	if _, err := reviewer.Review(context.Background(), "hello"); err == nil {
		t.Fatal("Review(missing config) error = nil")
	}

	provider.ok = true
	tests := []struct {
		name string
		body string
	}{
		{name: "invalid JSON", body: `{`},
		{name: "empty results", body: `{"results":[]}`},
		{name: "empty scores", body: `{"results":[{"category_scores":{}}]}`},
		{name: "score out of range", body: `{"results":[{"category_scores":{"violence":1.2}}]}`},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			reviewer.httpClient = doerFunc(func(*http.Request) (*http.Response, error) {
				return jsonResponse(http.StatusOK, test.body), nil
			})
			if _, err := reviewer.Review(context.Background(), "hello"); err == nil {
				t.Fatalf("Review(%s) error = nil", test.name)
			}
		})
	}
}

func TestTrimModerationInputBoundsRunesAndKeepsBothEnds(t *testing.T) {
	input := "START" + strings.Repeat("数", maxModerationInputRunes) + "END"
	trimmed := trimModerationInput(input)
	if len([]rune(trimmed)) != maxModerationInputRunes || !strings.HasPrefix(trimmed, "START") || !strings.HasSuffix(trimmed, "END") {
		t.Fatalf("trimmed runes=%d prefix=%t suffix=%t", len([]rune(trimmed)), strings.HasPrefix(trimmed, "START"), strings.HasSuffix(trimmed, "END"))
	}
}

func TestReviewerHelpersValidateRuntimeAndCancellation(t *testing.T) {
	base := configuredRuntimeProvider().runtime
	tests := []struct {
		name   string
		mutate func(*adminaiconfigapp.RuntimeConfig)
	}{
		{name: "base URL", mutate: func(runtime *adminaiconfigapp.RuntimeConfig) { runtime.BaseURL = "http://localhost" }},
		{name: "API key", mutate: func(runtime *adminaiconfigapp.RuntimeConfig) { runtime.APIKey = "" }},
		{name: "model", mutate: func(runtime *adminaiconfigapp.RuntimeConfig) { runtime.Model = "" }},
		{name: "timeout", mutate: func(runtime *adminaiconfigapp.RuntimeConfig) { runtime.Timeout = 0 }},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			runtime := base
			test.mutate(&runtime)
			if _, err := validateRuntimeConfig(runtime); err == nil {
				t.Fatalf("validateRuntimeConfig(%s) error = nil", test.name)
			}
		})
	}
	if got := joinProviderURL("https://api.example.com", "/v1/moderations"); got != "https://api.example.com/v1/moderations" {
		t.Fatalf("joinProviderURL() = %q", got)
	}
	cause := errors.New("network down")
	if !errors.Is(requestError{cause: cause}, cause) {
		t.Fatal("requestError does not unwrap cause")
	}
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if err := waitForRetry(ctx, time.Second); !errors.Is(err, context.Canceled) {
		t.Fatalf("waitForRetry(canceled) error = %v", err)
	}
	if err := waitForRetry(context.Background(), time.Millisecond); err != nil {
		t.Fatalf("waitForRetry(timer) error = %v", err)
	}
}

type fakeRuntimeProvider struct {
	runtime   adminaiconfigapp.RuntimeConfig
	ok        bool
	err       error
	agentType string
}

func (p *fakeRuntimeProvider) RuntimeConfig(_ context.Context, agentType string) (adminaiconfigapp.RuntimeConfig, bool, error) {
	p.agentType = agentType
	return p.runtime, p.ok, p.err
}

func configuredRuntimeProvider() *fakeRuntimeProvider {
	return &fakeRuntimeProvider{
		ok: true,
		runtime: adminaiconfigapp.RuntimeConfig{
			BaseURL:    "https://api.example.com/v1",
			APIKey:     "api-secret",
			Model:      "omni-moderation-latest",
			Timeout:    time.Second,
			MaxRetries: 0,
		},
	}
}

type doerFunc func(*http.Request) (*http.Response, error)

func (f doerFunc) Do(req *http.Request) (*http.Response, error) { return f(req) }

func jsonResponse(status int, body string) *http.Response {
	return &http.Response{
		StatusCode: status,
		Header:     make(http.Header),
		Body:       io.NopCloser(strings.NewReader(body)),
	}
}

func moderationResponse(scores map[string]float64) string {
	raw, _ := json.Marshal(map[string]any{"results": []any{map[string]any{"category_scores": scores}}})
	return string(raw)
}

func safeScores() map[string]float64 {
	return map[string]float64{
		"harassment":             0.01,
		"harassment/threatening": 0.01,
		"hate":                   0.01,
		"hate/threatening":       0.01,
		"illicit":                0.01,
		"illicit/violent":        0.01,
		"self-harm":              0.01,
		"self-harm/intent":       0.01,
		"self-harm/instructions": 0.01,
		"sexual":                 0.01,
		"sexual/minors":          0.01,
		"violence":               0.01,
		"violence/graphic":       0.01,
	}
}
