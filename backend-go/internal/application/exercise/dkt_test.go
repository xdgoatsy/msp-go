package exercise

import (
	"testing"
	"time"
)

func TestDKTUpdateUsesEmbeddedSequenceAttention(t *testing.T) {
	now := time.Date(2026, time.June, 1, 12, 0, 0, 0, time.UTC)
	current := LearningInteraction{
		ExerciseID:  "implicit-derivative",
		ConceptIDs:  []string{"implicit"},
		IsCorrect:   false,
		Difficulty:  0.7,
		SubmittedAt: now,
	}
	sequence := buildDKTSequence([]LearningInteraction{
		{ExerciseID: "chain-rule-yesterday", ConceptIDs: []string{"chain_rule", "implicit"}, IsCorrect: false, Difficulty: 0.6, SubmittedAt: now.Add(-24 * time.Hour)},
		{ExerciseID: "unrelated-old", ConceptIDs: []string{"integral"}, IsCorrect: true, Difficulty: 0.3, SubmittedAt: now.Add(-14 * 24 * time.Hour)},
	}, current)

	result := dktUpdate(0.7, "implicit", current, sequence, StudentProfile{PreferredDifficulty: 0.5, LearningPace: 1}, "conceptual", 2)

	if result.mastery >= 0.7 {
		t.Fatalf("mastery = %.4f, want lower than prior after related mistakes", result.mastery)
	}
	if result.sequenceLength != 3 {
		t.Fatalf("sequence length = %d", result.sequenceLength)
	}
	if result.attentionWeight <= 0 || result.confidence <= 0 {
		t.Fatalf("attention/confidence = %.4f %.4f", result.attentionWeight, result.confidence)
	}
}
