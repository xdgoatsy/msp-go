import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useExerciseViewModel } from '@/modules/exercise/hooks/exerciseViewModel';

const mocks = vi.hoisted(() => ({
  fetchNextQuestion: vi.fn(),
  submitAnswer: vi.fn(),
}));

vi.mock('@/modules/exercise/services/exerciseService', () => ({
  exerciseService: {
    fetchNextQuestion: mocks.fetchNextQuestion,
    submitAnswer: mocks.submitAnswer,
  },
}));

const question = {
  id: 'exercise-1',
  title: '极限',
  content: 'lim x',
  difficulty: 0.4,
  type: 'short_answer' as const,
  knowledgePoints: ['limit'],
  hintsAvailable: false,
  estimatedTimeSeconds: 60,
};

describe('useExerciseViewModel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.fetchNextQuestion.mockResolvedValue(question);
    mocks.submitAnswer.mockResolvedValue({
      isCorrect: true,
      score: 1,
      studentAnswerLatex: '42',
      correctAnswerLatex: '42',
      diagnosis: null,
      feedback: '正确',
      masteryUpdate: {},
      masteryModel: 'dkt-sakt-lite',
      nextRecommendation: 'advance',
    });
  });

  it('submits text-only answer payloads', async () => {
    const { result } = renderHook(() => useExerciseViewModel());
    await act(async () => {
      await result.current.loadNextQuestion();
    });

    await act(async () => {
      await result.current.submitAnswer('42');
    });

    expect(mocks.submitAnswer).toHaveBeenCalledWith(
      expect.objectContaining({
        exerciseId: 'exercise-1',
        answerText: '42',
      }),
    );
    expect(mocks.submitAnswer.mock.calls[0][0]).not.toHaveProperty('answerImageUrl');
  });

  it('rejects blank text without calling the service', async () => {
    const { result } = renderHook(() => useExerciseViewModel());
    await act(async () => {
      await result.current.loadNextQuestion();
    });

    await act(async () => {
      await result.current.submitAnswer('   ');
    });

    expect(mocks.submitAnswer).not.toHaveBeenCalled();
    expect(result.current.error).toBe('请输入答案');
  });
});
