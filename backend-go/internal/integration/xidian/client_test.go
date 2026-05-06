package xidian

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	xidianapp "mathstudy/backend-go/internal/application/xidian"
)

func TestStartBindingParsesLoginPageAndCaptcha(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/authserver/login":
			_, _ = w.Write([]byte(`<form><input type="hidden" name="lt" value="token"><input id="pwdEncryptSalt" value="1234567890abcdef"></form>`))
		case "/authserver/common/openSliderCaptcha.htl":
			_ = json.NewEncoder(w).Encode(map[string]any{"bigImage": "big", "smallImage": "piece", "y": 17})
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()
	client := newTestClient(t, server.URL)

	challenge, err := client.StartBinding(context.Background())
	if err != nil {
		t.Fatalf("StartBinding() error = %v", err)
	}
	if challenge.CaptchaBig != "big" || challenge.CaptchaPiece != "piece" || challenge.PieceY != 17 {
		t.Fatalf("challenge = %#v", challenge)
	}
	if challenge.State.PasswordSalt != "1234567890abcdef" || challenge.State.HiddenInputs["lt"] != "token" {
		t.Fatalf("state = %#v", challenge.State)
	}
}

func TestCompleteBindingSubmitsEncryptedPassword(t *testing.T) {
	var loginBody string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/authserver/common/verifySliderCaptcha.htl":
			_ = json.NewEncoder(w).Encode(map[string]any{"errorCode": 1})
		case "/authserver/login":
			if r.Method != http.MethodPost {
				http.NotFound(w, r)
				return
			}
			_ = r.ParseForm()
			loginBody = r.PostForm.Encode()
			http.Redirect(w, r, "/new/index.html", http.StatusFound)
		case "/new/index.html":
			_, _ = w.Write([]byte("ok"))
		case "/gsapp/sys/yjsemaphome/portal/index.do":
			_, _ = w.Write([]byte("ok"))
		case "/gsapp/sys/yjsemaphome/modules/pubWork/getCanVisitAppList.do":
			_ = json.NewEncoder(w).Encode(map[string]any{"res": []any{"app"}})
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()
	client := newTestClient(t, server.URL)

	result, err := client.CompleteBinding(context.Background(), xidianapp.ChallengeState{
		PasswordSalt: "1234567890abcdef",
		HiddenInputs: map[string]string{"lt": "token", "pwdEncryptSalt": "1234567890abcdef"},
	}, xidianapp.LoginInput{Username: "student", Password: "plain", SliderPosition: 0.5})
	if err != nil {
		t.Fatalf("CompleteBinding() error = %v", err)
	}
	if !strings.Contains(loginBody, "username=student") || strings.Contains(loginBody, "password=plain") || !strings.Contains(loginBody, "lt=token") {
		t.Fatalf("login body = %q", loginBody)
	}
	if result.IsPostgraduate == nil || !*result.IsPostgraduate {
		t.Fatalf("result = %#v", result)
	}
}

func TestNewClientRejectsMissingBaseURLs(t *testing.T) {
	if _, err := NewClient(Config{}); err == nil {
		t.Fatal("NewClient(empty) error = nil, want error")
	}
}

func newTestClient(t *testing.T, baseURL string) *Client {
	t.Helper()
	client, err := NewClient(Config{
		IDsBase:        baseURL,
		EhallBase:      baseURL,
		YjsptBase:      baseURL,
		UserAgent:      "test-agent",
		ConnectTimeout: time.Second,
		ReadTimeout:    time.Second,
		CaptchaWidth:   280,
	})
	if err != nil {
		t.Fatalf("NewClient() error = %v", err)
	}
	return client
}
