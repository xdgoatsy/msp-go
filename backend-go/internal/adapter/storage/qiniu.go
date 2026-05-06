package storage

import (
	"bytes"
	"context"
	"crypto/hmac"
	"crypto/sha1"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"mime/multipart"
	"net/http"
	"net/textproto"
	"net/url"
	"path"
	"sort"
	"strconv"
	"strings"
	"time"

	uploadapp "mathstudy/backend-go/internal/application/upload"
)

// QiniuConfig contains Qiniu Kodo object storage settings.
type QiniuConfig struct {
	AccessKey     string
	SecretKey     string
	BucketName    string
	Domain        string
	PrivateBucket bool
	URLExpire     time.Duration
	UploadURL     string
}

// QiniuStorage uploads files to Qiniu Kodo using server-side upload tokens.
type QiniuStorage struct {
	cfg    QiniuConfig
	client *http.Client
	now    func() time.Time
}

// NewQiniuStorage creates a Qiniu upload adapter.
func NewQiniuStorage(cfg QiniuConfig, client *http.Client) (*QiniuStorage, error) {
	if cfg.URLExpire <= 0 {
		cfg.URLExpire = time.Hour
	}
	if strings.TrimSpace(cfg.UploadURL) == "" {
		cfg.UploadURL = "https://upload.qiniup.com"
	}
	missing := make([]string, 0)
	for key, value := range map[string]string{
		"QINIU_ACCESS_KEY":  cfg.AccessKey,
		"QINIU_SECRET_KEY":  cfg.SecretKey,
		"QINIU_BUCKET_NAME": cfg.BucketName,
		"QINIU_DOMAIN":      cfg.Domain,
		"QINIU_UPLOAD_URL":  cfg.UploadURL,
	} {
		if strings.TrimSpace(value) == "" {
			missing = append(missing, key)
		}
	}
	if len(missing) > 0 {
		sort.Strings(missing)
		return nil, fmt.Errorf("Qiniu storage config missing: %s", strings.Join(missing, ", "))
	}
	if _, err := url.ParseRequestURI(cfg.UploadURL); err != nil {
		return nil, err
	}
	return &QiniuStorage{
		cfg:    cfg,
		client: defaultTimeout(client),
		now:    func() time.Time { return time.Now().UTC() },
	}, nil
}

// UploadData uploads a single object and returns its public or private URL.
func (s *QiniuStorage) UploadData(ctx context.Context, data []byte, key string, contentType string) (uploadapp.StoredObject, error) {
	cleanKey, err := cleanObjectKey(key)
	if err != nil {
		return uploadapp.StoredObject{}, err
	}
	var body bytes.Buffer
	writer := multipart.NewWriter(&body)
	if err := writer.WriteField("token", s.uploadToken(cleanKey)); err != nil {
		return uploadapp.StoredObject{}, err
	}
	if err := writer.WriteField("key", cleanKey); err != nil {
		return uploadapp.StoredObject{}, err
	}
	partHeader := textproto.MIMEHeader{}
	partHeader.Set("Content-Disposition", `form-data; name="file"; filename="`+escapeMultipartFilename(path.Base(cleanKey))+`"`)
	partHeader.Set("Content-Type", contentType)
	part, err := writer.CreatePart(partHeader)
	if err != nil {
		return uploadapp.StoredObject{}, err
	}
	if _, err := part.Write(data); err != nil {
		return uploadapp.StoredObject{}, err
	}
	if err := writer.Close(); err != nil {
		return uploadapp.StoredObject{}, err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, s.cfg.UploadURL, &body)
	if err != nil {
		return uploadapp.StoredObject{}, err
	}
	req.Header.Set("Content-Type", writer.FormDataContentType())
	req.ContentLength = int64(body.Len())

	response, err := s.client.Do(req)
	if err != nil {
		return uploadapp.StoredObject{}, err
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK {
		message := readErrorBody(response.Body)
		if message == "" {
			message = response.Status
		}
		return uploadapp.StoredObject{}, fmt.Errorf("Qiniu upload failed: %s", message)
	}
	return uploadapp.StoredObject{
		Key:         cleanKey,
		URL:         s.downloadURL(cleanKey),
		Size:        int64(len(data)),
		ContentType: contentType,
	}, nil
}

func (s *QiniuStorage) uploadToken(key string) string {
	policy := map[string]any{
		"scope":    s.cfg.BucketName + ":" + key,
		"deadline": s.now().Add(time.Hour).Unix(),
	}
	data, _ := json.Marshal(policy)
	encodedPolicy := qiniuBase64(data)
	signature := qiniuHMACSHA1(s.cfg.SecretKey, encodedPolicy)
	return s.cfg.AccessKey + ":" + signature + ":" + encodedPolicy
}

func (s *QiniuStorage) downloadURL(key string) string {
	base := strings.TrimRight(s.cfg.Domain, "/") + "/" + awsEncode(key, false)
	if !s.cfg.PrivateBucket {
		return base
	}
	deadline := strconv.FormatInt(s.now().Add(s.cfg.URLExpire).Unix(), 10)
	separator := "?"
	if strings.Contains(base, "?") {
		separator = "&"
	}
	urlWithDeadline := base + separator + "e=" + deadline
	token := s.cfg.AccessKey + ":" + qiniuHMACSHA1Raw(s.cfg.SecretKey, []byte(urlWithDeadline))
	return urlWithDeadline + "&token=" + token
}

func qiniuHMACSHA1(secret string, encodedPolicy string) string {
	return qiniuHMACSHA1Raw(secret, []byte(encodedPolicy))
}

func qiniuHMACSHA1Raw(secret string, data []byte) string {
	mac := hmac.New(sha1.New, []byte(secret))
	_, _ = mac.Write(data)
	return qiniuBase64(mac.Sum(nil))
}

func qiniuBase64(data []byte) string {
	return base64.URLEncoding.WithPadding(base64.NoPadding).EncodeToString(data)
}

func escapeMultipartFilename(value string) string {
	replacer := strings.NewReplacer("\\", "\\\\", `"`, "\\\"")
	return replacer.Replace(value)
}
