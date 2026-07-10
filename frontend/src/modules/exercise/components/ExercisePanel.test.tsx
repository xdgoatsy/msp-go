import type { ComponentProps } from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ExercisePanel } from './ExercisePanel';

const question: NonNullable<ComponentProps<typeof ExercisePanel>['currentQuestion']> = {
  id: 'exercise-1',
  title: '基础练习',
  content: '2 + 2',
  difficulty: 0.2,
  type: 'short_answer',
  knowledgePoints: ['arithmetic'],
  hintsAvailable: false,
  estimatedTimeSeconds: 30,
};

describe('ExercisePanel text answer boundary', () => {
  it('renders no image upload control and submits trimmed text', async () => {
    const loadNextQuestion = vi.fn().mockResolvedValue(undefined);
    const submitAnswer = vi.fn().mockResolvedValue(undefined);

    const { container } = render(
      <ExercisePanel
        currentQuestion={question}
        isLoading={false}
        isSubmitting={false}
        submitResult={null}
        error={null}
        errorType={null}
        loadNextQuestion={loadNextQuestion}
        submitAnswer={submitAnswer}
      />,
    );

    await waitFor(() => expect(loadNextQuestion).toHaveBeenCalledTimes(1));
    expect(container.querySelector('input[type="file"]')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /拍照|上传手写/ })).not.toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText(/输入答案/), {
      target: { value: '  x + 1  ' },
    });
    fireEvent.click(screen.getByRole('button', { name: '提交答案' }));

    await waitFor(() => expect(submitAnswer).toHaveBeenCalledWith('x + 1'));
  });
});
