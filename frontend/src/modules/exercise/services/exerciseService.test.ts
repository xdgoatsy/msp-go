import { beforeEach, describe, expect, it, vi } from 'vitest';
import { exerciseService } from './exerciseService';

const apiClientMock = vi.hoisted(() => ({
  post: vi.fn(),
}));

vi.mock('@/libs/http/apiClient', () => ({
  apiClient: apiClientMock,
}));

describe('exerciseService text answer boundary', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('sends no image answer field', async () => {
    apiClientMock.post.mockResolvedValue({
      data: {
        is_correct: true,
        score: 1,
        student_answer_latex: 'x + 1',
        correct_answer_latex: 'x + 1',
        diagnosis: null,
        feedback: '回答正确',
        mastery_update: null,
        mastery_model: 'dkt',
        next_recommendation: 'continue',
      },
    });

    await exerciseService.submitAnswer({
      exerciseId: 'exercise-1',
      answerText: 'x + 1',
      timeSpentSeconds: 12,
    });

    expect(apiClientMock.post).toHaveBeenCalledWith('/exercise/submit', {
      exercise_id: 'exercise-1',
      answer_text: 'x + 1',
      answer_steps: undefined,
      time_spent_seconds: 12,
    });
    expect(apiClientMock.post.mock.calls[0][1]).not.toHaveProperty('answer_image_url');
  });
});
