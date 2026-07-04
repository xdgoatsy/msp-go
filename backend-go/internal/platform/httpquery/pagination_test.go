package httpquery

import (
	"errors"
	"net/url"
	"testing"
)

func TestPagination(t *testing.T) {
	params, err := Pagination(url.Values{}, 20, 100)
	if err != nil {
		t.Fatalf("Pagination(defaults) error = %v", err)
	}
	if params.Page != 1 || params.PageSize != 20 {
		t.Fatalf("Pagination(defaults) = %#v, want page=1 page_size=20", params)
	}

	params, err = Pagination(url.Values{"page": {"2"}, "page_size": {"50"}}, 20, 100)
	if err != nil {
		t.Fatalf("Pagination(values) error = %v", err)
	}
	if params.Page != 2 || params.PageSize != 50 {
		t.Fatalf("Pagination(values) = %#v, want page=2 page_size=50", params)
	}
}

func TestPaginationErrors(t *testing.T) {
	tests := []struct {
		name      string
		query     url.Values
		wantField string
		wantErr   error
	}{
		{
			name:      "invalid page",
			query:     url.Values{"page": {"bad"}},
			wantField: PageField,
			wantErr:   ErrInvalidInt,
		},
		{
			name:      "page out of range",
			query:     url.Values{"page": {"0"}},
			wantField: PageField,
			wantErr:   ErrIntOutOfRange,
		},
		{
			name:      "invalid page size",
			query:     url.Values{"page_size": {"bad"}},
			wantField: PageSizeField,
			wantErr:   ErrInvalidInt,
		},
		{
			name:      "page size out of range",
			query:     url.Values{"page_size": {"101"}},
			wantField: PageSizeField,
			wantErr:   ErrIntOutOfRange,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, err := Pagination(tt.query, 20, 100)
			if !errors.Is(err, tt.wantErr) {
				t.Fatalf("Pagination() error = %v, want %v", err, tt.wantErr)
			}
			var paginationErr PaginationError
			if !errors.As(err, &paginationErr) {
				t.Fatalf("Pagination() error = %T, want PaginationError", err)
			}
			if paginationErr.Field != tt.wantField {
				t.Fatalf("PaginationError.Field = %q, want %q", paginationErr.Field, tt.wantField)
			}
		})
	}
}

func TestPaginationErrorMessage(t *testing.T) {
	tests := []struct {
		name string
		err  error
		want string
	}{
		{
			name: "unknown error",
			err:  errors.New("boom"),
			want: "分页参数无效",
		},
		{
			name: "invalid page",
			err:  PaginationError{Field: PageField, Err: ErrInvalidInt},
			want: "page 必须是整数",
		},
		{
			name: "invalid page size",
			err:  PaginationError{Field: PageSizeField, Err: ErrInvalidInt},
			want: "page_size 必须是整数",
		},
		{
			name: "page out of range",
			err:  PaginationError{Field: PageField, Err: ErrIntOutOfRange},
			want: "page 必须大于等于 1",
		},
		{
			name: "page size out of range",
			err:  PaginationError{Field: PageSizeField, Err: ErrIntOutOfRange},
			want: "page_size 必须在 1 到 50 之间",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := PaginationErrorMessage(tt.err, 50); got != tt.want {
				t.Fatalf("PaginationErrorMessage() = %q, want %q", got, tt.want)
			}
		})
	}
}
