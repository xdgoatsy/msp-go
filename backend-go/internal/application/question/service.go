package question

import (
	"context"
	"errors"
	"strings"
	"time"
	"unicode"
)

var (
	// ErrNotFound is returned when a question does not exist or is not accessible.
	ErrNotFound = errors.New("question not found")
	// ErrBadRequest is returned when a request cannot be applied.
	ErrBadRequest = errors.New("question bad request")
	// ErrForbidden is returned when a question exists but is not owned by the current teacher.
	ErrForbidden = errors.New("question forbidden")
)

// Repository is the persistence surface required by teacher question bank use cases.
type Repository interface {
	MatchConceptIDs(context.Context, string) ([]string, error)
	ListQuestions(context.Context, string, ListFilter) ([]Question, int, error)
	GetQuestion(context.Context, string, string) (Question, bool, error)
	CreateQuestion(context.Context, string, QuestionInput, time.Time) (Question, error)
	UpdateQuestion(context.Context, string, string, QuestionUpdate, time.Time) (Question, bool, error)
	DeleteQuestion(context.Context, string, string, time.Time) (bool, error)
	GetGroups(context.Context, string) ([]string, error)
	GetStats(context.Context, string) (Stats, error)
	BatchPublish(context.Context, string, []string, time.Time) (int, error)
	BatchDelete(context.Context, string, []string, time.Time) (int, error)
	BatchDuplicate(context.Context, string, []string, time.Time) (BatchOperationResponse, error)
	BatchImport(context.Context, string, []QuestionInput, time.Time) (BatchOperationResponse, error)
}

// ListFilter stores /questions filters and pagination.
type ListFilter struct {
	Page       int
	PageSize   int
	Search     string
	Difficulty string
	Type       string
	Status     string
	Tags       []string
	Group      string
	SortBy     string
	SortOrder  string
}

// QuestionInput stores fields required to create a question.
type QuestionInput struct {
	Title                string
	Body                 string
	Type                 string
	Difficulty           float64
	ConceptIDs           []string
	Tags                 []string
	Answer               string
	AnswerType           string
	Hints                []string
	SolutionSteps        []string
	Options              *[]string
	EstimatedTimeSeconds int
}

// QuestionUpdate stores optional fields accepted by update question.
type QuestionUpdate struct {
	Title                *string
	Body                 *string
	Type                 *string
	Difficulty           *float64
	ConceptIDs           *[]string
	Tags                 *[]string
	Answer               *string
	AnswerType           *string
	Hints                *[]string
	SolutionSteps        *[]string
	Options              *[]string
	EstimatedTimeSeconds *int
	Status               *string
}

// Question is the Python-compatible question response shape.
type Question struct {
	ID          string         `json:"id"`
	Title       string         `json:"title"`
	Body        string         `json:"body"`
	Type        string         `json:"type"`
	Difficulty  float64        `json:"difficulty"`
	ConceptIDs  []string       `json:"concept_ids"`
	Tags        []string       `json:"tags"`
	Status      string         `json:"status"`
	Meta        map[string]any `json:"meta"`
	CreatedAt   time.Time      `json:"created_at"`
	UpdatedAt   time.Time      `json:"updated_at"`
	UsageCount  int            `json:"usage_count"`
	CorrectRate float64        `json:"correct_rate"`
}

// ListResponse is the Python-compatible question list response.
type ListResponse struct {
	Items    []Question `json:"items"`
	Total    int        `json:"total"`
	Page     int        `json:"page"`
	PageSize int        `json:"page_size"`
}

// Stats stores question counters.
type Stats struct {
	Total        int            `json:"total"`
	ByDifficulty map[string]int `json:"by_difficulty"`
	ByType       map[string]int `json:"by_type"`
	ByStatus     map[string]int `json:"by_status"`
}

// GroupsResponse is returned by /questions/groups.
type GroupsResponse struct {
	Groups []string `json:"groups"`
}

// BatchOperationResponse is shared by batch question endpoints.
type BatchOperationResponse struct {
	Success   int      `json:"success"`
	Failed    int      `json:"failed"`
	FailedIDs []string `json:"failed_ids"`
	Errors    []string `json:"errors"`
}

// AIParseQuestionItem is the shape returned by the AI parse endpoint.
type AIParseQuestionItem struct {
	Title         string   `json:"title"`
	Body          string   `json:"body"`
	Type          string   `json:"type"`
	Difficulty    float64  `json:"difficulty"`
	Answer        string   `json:"answer"`
	AnswerType    string   `json:"answer_type"`
	Options       []string `json:"options,omitempty"`
	Hints         []string `json:"hints"`
	SolutionSteps []string `json:"solution_steps"`
	Tags          []string `json:"tags"`
}

// AIParseResponse wraps parsed question candidates.
type AIParseResponse struct {
	Questions []AIParseQuestionItem `json:"questions"`
}

// Service implements teacher question bank use cases.
type Service struct {
	repo Repository
	now  func() time.Time
}

// NewService creates a question service.
func NewService(repo Repository) (*Service, error) {
	if repo == nil {
		return nil, errors.New("question repository is nil")
	}
	return &Service{repo: repo, now: func() time.Time { return time.Now().UTC() }}, nil
}

// ListQuestions returns a filtered teacher-owned question page.
func (s *Service) ListQuestions(ctx context.Context, ownerID string, filter ListFilter) (ListResponse, error) {
	filter = normalizeListFilter(filter)
	items, total, err := s.repo.ListQuestions(ctx, ownerID, filter)
	if err != nil {
		return ListResponse{}, err
	}
	return ListResponse{Items: items, Total: total, Page: filter.Page, PageSize: filter.PageSize}, nil
}

// GetQuestion returns one teacher-owned problem.
func (s *Service) GetQuestion(ctx context.Context, ownerID string, questionID string) (Question, error) {
	question, ok, err := s.repo.GetQuestion(ctx, ownerID, questionID)
	if err != nil {
		return Question{}, err
	}
	if !ok {
		return Question{}, ErrNotFound
	}
	return question, nil
}

// CreateQuestion creates a teacher-owned draft problem.
func (s *Service) CreateQuestion(ctx context.Context, ownerID string, input QuestionInput) (Question, error) {
	input = normalizeQuestionInput(input)
	if len(input.ConceptIDs) == 0 {
		conceptIDs, err := s.repo.MatchConceptIDs(ctx, input.Title)
		if err != nil {
			return Question{}, err
		}
		input.ConceptIDs = conceptIDs
	}
	return s.repo.CreateQuestion(ctx, ownerID, input, s.now())
}

// UpdateQuestion updates a teacher-owned problem.
func (s *Service) UpdateQuestion(ctx context.Context, ownerID string, questionID string, update QuestionUpdate) (Question, error) {
	update = normalizeQuestionUpdate(update)
	if update.Title != nil && update.ConceptIDs == nil {
		conceptIDs, err := s.repo.MatchConceptIDs(ctx, *update.Title)
		if err != nil {
			return Question{}, err
		}
		if len(conceptIDs) > 0 {
			update.ConceptIDs = &conceptIDs
		}
	}
	question, ok, err := s.repo.UpdateQuestion(ctx, ownerID, questionID, update, s.now())
	if err != nil {
		return Question{}, err
	}
	if !ok {
		return Question{}, ErrNotFound
	}
	return question, nil
}

// DeleteQuestion soft-deletes a teacher-owned problem.
func (s *Service) DeleteQuestion(ctx context.Context, ownerID string, questionID string) error {
	ok, err := s.repo.DeleteQuestion(ctx, ownerID, questionID, s.now())
	if err != nil {
		return err
	}
	if !ok {
		return ErrNotFound
	}
	return nil
}

// GetGroups returns distinct teacher-owned question group names.
func (s *Service) GetGroups(ctx context.Context, ownerID string) (GroupsResponse, error) {
	groups, err := s.repo.GetGroups(ctx, ownerID)
	if err != nil {
		return GroupsResponse{}, err
	}
	return GroupsResponse{Groups: groups}, nil
}

// GetStats returns teacher question counters.
func (s *Service) GetStats(ctx context.Context, ownerID string) (Stats, error) {
	return s.repo.GetStats(ctx, ownerID)
}

// BatchPublish publishes teacher-owned problem content.
func (s *Service) BatchPublish(ctx context.Context, ownerID string, questionIDs []string) (BatchOperationResponse, error) {
	ids := normalizeIDs(questionIDs)
	if len(ids) == 0 {
		return BatchOperationResponse{}, ErrBadRequest
	}
	count, err := s.repo.BatchPublish(ctx, ownerID, ids, s.now())
	if err != nil {
		return BatchOperationResponse{}, err
	}
	return BatchOperationResponse{Success: count, Failed: len(ids) - count, FailedIDs: []string{}, Errors: []string{}}, nil
}

// BatchDelete soft-deletes teacher-owned problem content.
func (s *Service) BatchDelete(ctx context.Context, ownerID string, questionIDs []string) (BatchOperationResponse, error) {
	ids := normalizeIDs(questionIDs)
	if len(ids) == 0 {
		return BatchOperationResponse{}, ErrBadRequest
	}
	count, err := s.repo.BatchDelete(ctx, ownerID, ids, s.now())
	if err != nil {
		return BatchOperationResponse{}, err
	}
	return BatchOperationResponse{Success: count, Failed: len(ids) - count, FailedIDs: []string{}, Errors: []string{}}, nil
}

// BatchDuplicate duplicates teacher-owned problem content.
func (s *Service) BatchDuplicate(ctx context.Context, ownerID string, questionIDs []string) (BatchOperationResponse, error) {
	ids := normalizeIDs(questionIDs)
	if len(ids) == 0 {
		return BatchOperationResponse{}, ErrBadRequest
	}
	return s.repo.BatchDuplicate(ctx, ownerID, ids, s.now())
}

// BatchImport inserts already parsed questions.
func (s *Service) BatchImport(ctx context.Context, ownerID string, questions []QuestionInput) (BatchOperationResponse, error) {
	if len(questions) == 0 || len(questions) > 200 {
		return BatchOperationResponse{}, ErrBadRequest
	}
	normalized := make([]QuestionInput, 0, len(questions))
	for _, input := range questions {
		input = normalizeQuestionInput(input)
		if len(input.ConceptIDs) == 0 {
			conceptIDs, err := s.repo.MatchConceptIDs(ctx, input.Title)
			if err != nil {
				return BatchOperationResponse{}, err
			}
			input.ConceptIDs = conceptIDs
		}
		normalized = append(normalized, input)
	}
	return s.repo.BatchImport(ctx, ownerID, normalized, s.now())
}

// ParseQuestions returns a deterministic shape-compatible parse fallback.
func (s *Service) ParseQuestions(_ context.Context, rawTexts []string) (AIParseResponse, error) {
	if len(rawTexts) == 0 || len(rawTexts) > 10 {
		return AIParseResponse{}, ErrBadRequest
	}
	items := make([]AIParseQuestionItem, 0, len(rawTexts))
	for _, text := range rawTexts {
		if len(text) > 3000 {
			return AIParseResponse{}, ErrBadRequest
		}
		trimmed := strings.TrimSpace(text)
		items = append(items, AIParseQuestionItem{
			Title:         firstNonEmptyLine(trimmed),
			Body:          trimmed,
			Type:          "short_answer",
			Difficulty:    0.5,
			Answer:        "",
			AnswerType:    "expression",
			Hints:         []string{},
			SolutionSteps: []string{},
			Tags:          []string{},
		})
	}
	return AIParseResponse{Questions: items}, nil
}

func normalizeListFilter(filter ListFilter) ListFilter {
	filter.Search = strings.TrimSpace(filter.Search)
	filter.Difficulty = strings.ToLower(strings.TrimSpace(filter.Difficulty))
	filter.Type = strings.ToLower(strings.TrimSpace(filter.Type))
	filter.Status = strings.ToLower(strings.TrimSpace(filter.Status))
	filter.Group = strings.TrimSpace(filter.Group)
	filter.SortBy = strings.ToLower(strings.TrimSpace(filter.SortBy))
	filter.SortOrder = strings.ToLower(strings.TrimSpace(filter.SortOrder))
	filter.Tags = normalizeStringSlice(filter.Tags)
	if filter.Page < 1 {
		filter.Page = 1
	}
	if filter.PageSize < 1 {
		filter.PageSize = 20
	}
	if filter.PageSize > 100 {
		filter.PageSize = 100
	}
	if filter.SortBy == "" {
		filter.SortBy = "created_at"
	}
	if filter.SortOrder != "asc" {
		filter.SortOrder = "desc"
	}
	return filter
}

func normalizeQuestionInput(input QuestionInput) QuestionInput {
	input.Title = strings.TrimSpace(input.Title)
	input.Body = strings.TrimSpace(input.Body)
	input.Type = normalizeQuestionType(input.Type)
	input.AnswerType = normalizeAnswerType(input.AnswerType)
	if input.Difficulty < 0 {
		input.Difficulty = 0
	}
	if input.Difficulty > 1 {
		input.Difficulty = 1
	}
	if input.EstimatedTimeSeconds < 0 {
		input.EstimatedTimeSeconds = 0
	}
	if input.EstimatedTimeSeconds == 0 {
		input.EstimatedTimeSeconds = 300
	}
	input.ConceptIDs = normalizeStringSlice(input.ConceptIDs)
	input.Tags = normalizeStringSlice(input.Tags)
	input.Hints = normalizeStringSlice(input.Hints)
	input.SolutionSteps = normalizeStringSlice(input.SolutionSteps)
	if input.Options != nil {
		options := normalizeStringSlice(*input.Options)
		input.Options = &options
	}
	return input
}

func normalizeQuestionUpdate(update QuestionUpdate) QuestionUpdate {
	if update.Title != nil {
		value := strings.TrimSpace(*update.Title)
		update.Title = &value
	}
	if update.Body != nil {
		value := strings.TrimSpace(*update.Body)
		update.Body = &value
	}
	if update.Type != nil {
		value := normalizeQuestionType(*update.Type)
		update.Type = &value
	}
	if update.AnswerType != nil {
		value := normalizeAnswerType(*update.AnswerType)
		update.AnswerType = &value
	}
	if update.Status != nil {
		value := strings.ToLower(strings.TrimSpace(*update.Status))
		update.Status = &value
	}
	if update.ConceptIDs != nil {
		values := normalizeStringSlice(*update.ConceptIDs)
		update.ConceptIDs = &values
	}
	if update.Tags != nil {
		values := normalizeStringSlice(*update.Tags)
		update.Tags = &values
	}
	if update.Hints != nil {
		values := normalizeStringSlice(*update.Hints)
		update.Hints = &values
	}
	if update.SolutionSteps != nil {
		values := normalizeStringSlice(*update.SolutionSteps)
		update.SolutionSteps = &values
	}
	if update.Options != nil {
		values := normalizeStringSlice(*update.Options)
		update.Options = &values
	}
	return update
}

func normalizeQuestionType(value string) string {
	switch strings.ToLower(strings.TrimSpace(value)) {
	case "multiple_choice", "proof":
		return strings.ToLower(strings.TrimSpace(value))
	default:
		return "short_answer"
	}
}

func normalizeAnswerType(value string) string {
	switch strings.ToLower(strings.TrimSpace(value)) {
	case "numeric", "text":
		return strings.ToLower(strings.TrimSpace(value))
	default:
		return "expression"
	}
}

func normalizeStringSlice(values []string) []string {
	if values == nil {
		return []string{}
	}
	result := make([]string, 0, len(values))
	for _, value := range values {
		trimmed := strings.TrimSpace(value)
		if trimmed != "" {
			result = append(result, trimmed)
		}
	}
	return result
}

func normalizeIDs(values []string) []string {
	result := make([]string, 0, len(values))
	seen := map[string]struct{}{}
	for _, value := range values {
		trimmed := strings.TrimSpace(value)
		if trimmed == "" {
			continue
		}
		if _, ok := seen[trimmed]; ok {
			continue
		}
		seen[trimmed] = struct{}{}
		result = append(result, trimmed)
	}
	return result
}

func firstNonEmptyLine(text string) string {
	for _, line := range strings.Split(text, "\n") {
		line = strings.TrimFunc(line, func(r rune) bool {
			return unicode.IsSpace(r) || r == '#' || r == '-' || r == '*'
		})
		if line != "" {
			if len([]rune(line)) > 500 {
				runes := []rune(line)
				return string(runes[:500])
			}
			return line
		}
	}
	return ""
}
