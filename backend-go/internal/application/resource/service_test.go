package resource

import (
	"context"
	"errors"
	"strings"
	"testing"
	"time"
)

func TestGetResourcesNormalizesPaginationAndHasMore(t *testing.T) {
	repo := &fakeResourceRepo{
		resources: []Resource{{ID: "resource-1"}},
		total:     25,
	}
	service := newTestService(repo, time.Date(2026, time.April, 26, 10, 0, 0, 0, time.UTC))

	response, err := service.GetResources(context.Background(), "student-1", ListFilter{Page: -1, PageSize: 500})
	if err != nil {
		t.Fatalf("GetResources() error = %v", err)
	}
	if response.Page != 1 || response.PageSize != 100 || response.HasMore {
		t.Fatalf("response = %#v", response)
	}
	if repo.lastUserID != "student-1" || repo.lastFilter.Page != 1 || repo.lastFilter.PageSize != 100 {
		t.Fatalf("repo call = user %q filter %#v", repo.lastUserID, repo.lastFilter)
	}
}

func TestGetFavoritesForwardsFavoriteOnlyFilter(t *testing.T) {
	repo := &fakeResourceRepo{}
	service := newTestService(repo, time.Now())

	_, err := service.GetFavorites(context.Background(), "user-1", 2, 10)
	if err != nil {
		t.Fatalf("GetFavorites() error = %v", err)
	}
	if !repo.lastFilter.FavoritesOnly || repo.lastFilter.Page != 2 || repo.lastFilter.PageSize != 10 {
		t.Fatalf("filter = %#v", repo.lastFilter)
	}
}

func TestNotFoundErrors(t *testing.T) {
	repo := &fakeResourceRepo{}
	service := newTestService(repo, time.Now())

	if _, err := service.GetResource(context.Background(), "user-1", "missing"); !errors.Is(err, ErrNotFound) {
		t.Fatalf("GetResource() error = %v, want ErrNotFound", err)
	}
	if _, err := service.UpdateResource(context.Background(), "missing", "teacher-1", ResourceUpdate{}); !errors.Is(err, ErrNotFound) {
		t.Fatalf("UpdateResource() error = %v, want ErrNotFound", err)
	}
	if err := service.DeleteResource(context.Background(), "missing", "teacher-1"); !errors.Is(err, ErrNotFound) {
		t.Fatalf("DeleteResource() error = %v, want ErrNotFound", err)
	}
	if _, err := service.ToggleFavorite(context.Background(), "user-1", "missing"); !errors.Is(err, ErrNotFound) {
		t.Fatalf("ToggleFavorite() error = %v, want ErrNotFound", err)
	}
}

func TestCreateResourceNormalizesStorageAndTags(t *testing.T) {
	now := time.Date(2026, time.April, 26, 10, 0, 0, 0, time.UTC)
	repo := &fakeResourceRepo{createResource: Resource{ID: "resource-1"}}
	service := newTestService(repo, now)

	response, err := service.CreateResource(context.Background(), "teacher-1", ResourceInput{Title: "导数", Type: " DOCUMENT "})
	if err != nil {
		t.Fatalf("CreateResource() error = %v", err)
	}
	if response.ID != "resource-1" {
		t.Fatalf("response = %#v", response)
	}
	if repo.lastOwnerID != "teacher-1" || repo.lastInput.Type != "document" || repo.lastInput.StorageType != "external" {
		t.Fatalf("input = %#v owner = %q", repo.lastInput, repo.lastOwnerID)
	}
	if repo.lastInput.Tags == nil || !repo.lastNow.Equal(now) {
		t.Fatalf("tags/now = %#v %v", repo.lastInput.Tags, repo.lastNow)
	}
}

func TestCreateResourceNormalizesExternalURL(t *testing.T) {
	repo := &fakeResourceRepo{createResource: Resource{ID: "resource-1"}}
	service := newTestService(repo, time.Now())

	_, err := service.CreateResource(context.Background(), "teacher-1", ResourceInput{
		Title: "导数",
		Type:  "video",
		URL:   stringPtr(" example.com:8443/watch?v=1 "),
	})
	if err != nil {
		t.Fatalf("CreateResource() error = %v", err)
	}
	if repo.lastInput.URL == nil || *repo.lastInput.URL != "https://example.com:8443/watch?v=1" {
		t.Fatalf("URL = %#v", repo.lastInput.URL)
	}
}

func TestCreateResourceAcceptsLocalUploadedResourcePath(t *testing.T) {
	repo := &fakeResourceRepo{createResource: Resource{ID: "resource-1"}}
	service := newTestService(repo, time.Now())

	_, err := service.CreateResource(context.Background(), "teacher-1", ResourceInput{
		Title:       "讲义",
		Type:        "document",
		StorageType: "local",
		URL:         stringPtr("/uploads/documents/file.pdf"),
	})
	if err != nil {
		t.Fatalf("CreateResource() error = %v", err)
	}
	if repo.lastInput.URL == nil || *repo.lastInput.URL != "/uploads/documents/file.pdf" {
		t.Fatalf("URL = %#v", repo.lastInput.URL)
	}
}

func TestCreateResourceRejectsUnsafeURLs(t *testing.T) {
	cases := []string{
		"javascript:alert(1)",
		"data:text/html,<script>alert(1)</script>",
		"mailto:teacher@example.com",
		"https://user:pass@example.com/resource",
		"http://127.0.0.1:8080/internal",
		"/uploads/documents/../secret.pdf",
		"/uploads/documents/file.pdf?download=1",
		"/uploads/videos/%2e%2e/file.mp4",
		`/uploads/documents\file.pdf`,
		"/uploads/images/file.png",
		"//example.com/resource",
	}
	service := newTestService(&fakeResourceRepo{}, time.Now())

	for _, rawURL := range cases {
		t.Run(rawURL, func(t *testing.T) {
			_, err := service.CreateResource(context.Background(), "teacher-1", ResourceInput{
				Title: "导数",
				Type:  "document",
				URL:   stringPtr(rawURL),
			})
			if !errors.Is(err, ErrBadRequest) {
				t.Fatalf("CreateResource(%q) error = %v, want ErrBadRequest", rawURL, err)
			}
		})
	}
}

func TestUpdateResourceNormalizesURLAndStorageType(t *testing.T) {
	repo := &fakeResourceRepo{updateResource: Resource{ID: "resource-1"}, updateFound: true}
	service := newTestService(repo, time.Now())

	_, err := service.UpdateResource(context.Background(), "resource-1", "teacher-1", ResourceUpdate{
		StorageType: stringPtr(" LOCAL "),
		URL:         stringPtr(" /uploads/videos/file.mp4 "),
	})
	if err != nil {
		t.Fatalf("UpdateResource() error = %v", err)
	}
	if repo.lastUpdate.StorageType == nil || *repo.lastUpdate.StorageType != "local" {
		t.Fatalf("StorageType = %#v", repo.lastUpdate.StorageType)
	}
	if repo.lastUpdate.URL == nil || *repo.lastUpdate.URL != "/uploads/videos/file.mp4" {
		t.Fatalf("URL = %#v", repo.lastUpdate.URL)
	}
}

func TestCreateResourceURLRejectsControlWhitespace(t *testing.T) {
	service := newTestService(&fakeResourceRepo{}, time.Now())

	_, err := service.CreateResource(context.Background(), "teacher-1", ResourceInput{
		Title: "导数",
		Type:  "document",
		URL:   stringPtr("https://example.com/\nnext"),
	})
	if !errors.Is(err, ErrBadRequest) || !strings.Contains(err.Error(), "资源链接格式无效") {
		t.Fatalf("CreateResource() error = %v, want URL format ErrBadRequest", err)
	}
}

func TestToggleFavoriteBuildsMessage(t *testing.T) {
	repo := &fakeResourceRepo{favoriteState: true, favoriteFound: true}
	service := newTestService(repo, time.Now())

	response, err := service.ToggleFavorite(context.Background(), "user-1", "resource-1")
	if err != nil {
		t.Fatalf("ToggleFavorite() error = %v", err)
	}
	if !response.IsFavorite || response.Message != "已收藏" || response.ResourceID != "resource-1" {
		t.Fatalf("response = %#v", response)
	}
}

func TestNewServiceRejectsNilRepository(t *testing.T) {
	if _, err := NewService(nil); err == nil {
		t.Fatal("NewService(nil) error = nil, want error")
	}
}

func newTestService(repo Repository, now time.Time) *Service {
	service, err := NewService(repo)
	if err != nil {
		panic(err)
	}
	service.now = func() time.Time { return now }
	return service
}

type fakeResourceRepo struct {
	resources      []Resource
	total          int
	resource       Resource
	resourceFound  bool
	createResource Resource
	updateResource Resource
	updateFound    bool
	deleteFound    bool
	favoriteState  bool
	favoriteFound  bool
	stats          Stats
	lastUserID     string
	lastOwnerID    string
	lastResourceID string
	lastFilter     ListFilter
	lastInput      ResourceInput
	lastUpdate     ResourceUpdate
	lastNow        time.Time
}

func (r *fakeResourceRepo) ListResources(_ context.Context, userID string, filter ListFilter) ([]Resource, int, error) {
	r.lastUserID = userID
	r.lastFilter = filter
	return r.resources, r.total, nil
}

func (r *fakeResourceRepo) GetResourceByID(_ context.Context, resourceID string, userID string) (Resource, bool, error) {
	r.lastUserID = userID
	r.lastResourceID = resourceID
	return r.resource, r.resourceFound, nil
}

func (r *fakeResourceRepo) CreateResource(_ context.Context, ownerID string, input ResourceInput, now time.Time) (Resource, error) {
	r.lastOwnerID = ownerID
	r.lastInput = input
	r.lastNow = now
	return r.createResource, nil
}

func (r *fakeResourceRepo) UpdateResource(_ context.Context, resourceID string, ownerID string, input ResourceUpdate, now time.Time) (Resource, bool, error) {
	r.lastResourceID = resourceID
	r.lastOwnerID = ownerID
	r.lastUpdate = input
	r.lastNow = now
	return r.updateResource, r.updateFound, nil
}

func (r *fakeResourceRepo) DeleteResource(_ context.Context, resourceID string, ownerID string, now time.Time) (bool, error) {
	r.lastResourceID = resourceID
	r.lastOwnerID = ownerID
	r.lastNow = now
	return r.deleteFound, nil
}

func (r *fakeResourceRepo) ToggleFavorite(_ context.Context, userID string, resourceID string) (bool, bool, error) {
	r.lastUserID = userID
	r.lastResourceID = resourceID
	return r.favoriteState, r.favoriteFound, nil
}

func (r *fakeResourceRepo) GetStats(_ context.Context, userID string) (Stats, error) {
	r.lastUserID = userID
	return r.stats, nil
}

func stringPtr(value string) *string {
	return &value
}
