package postgres

import (
	"strings"
	"testing"

	questionapp "mathstudy/backend-go/internal/application/question"
)

func TestNewQuestionRepositoryRejectsNilQuerier(t *testing.T) {
	if _, err := NewQuestionRepository(nil); err == nil {
		t.Fatal("NewQuestionRepository(nil) error = nil, want error")
	}
}

func TestQuestionWhereClauseIncludesProblemScopeAndFilters(t *testing.T) {
	where, args := questionWhereClause("teacher-1", questionapp.ListFilter{
		Type:       "proof",
		Status:     "published",
		Difficulty: "easy",
		Search:     "limit",
		Tags:       []string{"tag-1"},
		Group:      "极限",
	})
	if !strings.Contains(where, "c.owner_teacher_id = $1") || !strings.Contains(where, "c.type = 'PROBLEM'") {
		t.Fatalf("where = %s", where)
	}
	for _, want := range []string{"c.meta->>'type'", "c.status", "c.difficulty", "ILIKE", "json_array_elements_text", "c.title ="} {
		if !strings.Contains(where, want) {
			t.Fatalf("where = %s, missing %s", where, want)
		}
	}
	if len(args) != 8 {
		t.Fatalf("args = %#v", args)
	}
}

func TestQuestionMetaFromInputOmitsEmptyOptions(t *testing.T) {
	options := []string{}
	meta := questionMetaFromInput(questionapp.QuestionInput{
		Type:                 "multiple_choice",
		Answer:               "A",
		AnswerType:           "text",
		Hints:                []string{},
		SolutionSteps:        []string{},
		Options:              &options,
		EstimatedTimeSeconds: 300,
	})
	if _, ok := meta["options"]; ok {
		t.Fatalf("meta = %#v, options should be omitted for create parity", meta)
	}
	if meta["type"] != "multiple_choice" || meta["answer"] != "A" {
		t.Fatalf("meta = %#v", meta)
	}
}

func TestSplitGroupKeywordsFallsBackToWholeName(t *testing.T) {
	keywords := splitGroupKeywords("A")
	if len(keywords) != 1 || keywords[0] != "A" {
		t.Fatalf("keywords = %#v", keywords)
	}
	keywords = splitGroupKeywords("极限与连续")
	if len(keywords) != 2 || keywords[0] != "极限" || keywords[1] != "连续" {
		t.Fatalf("keywords = %#v", keywords)
	}
}

func TestQuestionStatusConversion(t *testing.T) {
	if got := questionStatusFromDB("PUBLISHED"); got != "published" {
		t.Fatalf("questionStatusFromDB() = %q", got)
	}
	if got, ok := questionStatusToDB("archived"); !ok || got != "ARCHIVED" {
		t.Fatalf("questionStatusToDB() = %q %t", got, ok)
	}
	if _, ok := questionStatusToDB("bad"); ok {
		t.Fatal("questionStatusToDB(bad) ok = true, want false")
	}
}
