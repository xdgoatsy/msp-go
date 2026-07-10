import { useState, useCallback, useRef } from 'react';
import axios from 'axios';
import {
  exerciseService,
  type Question,
  type SubmitResult,
} from '@/modules/exercise/services/exerciseService';
import { logger } from '@/libs/utils/logger';
import { getApiErrorMessage } from '@/libs/http/apiClient';

const exerciseLogger = logger.createContextLogger('ExerciseViewModel');

/**
 * 练习题错误类型
 */
export type ExerciseErrorType =
  | 'not_enrolled'   // 403: 未加入班级
  | 'no_questions'   // 无可用题目
  | 'network_error'  // 网络错误
  | 'unknown';       // 其他错误

/**
 * 练习题 ViewModel Hook
 *
 * 管理题目加载、文本答案提交和反馈展示
 */
export function useExerciseViewModel() {
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState<SubmitResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorType, setErrorType] = useState<ExerciseErrorType | null>(null);

  // 答题计时
  const startTimeRef = useRef<number>(Date.now());

  const loadNextQuestion = useCallback(
    async (conceptId?: string, difficulty?: number) => {
      setIsLoading(true);
      setError(null);
      setErrorType(null);
      setSubmitResult(null);
      try {
        const question = await exerciseService.fetchNextQuestion(
          conceptId,
          difficulty,
        );
        if (!question) {
          setCurrentQuestion(null);
          setError(null);
          setErrorType('no_questions');
          exerciseLogger.info('No questions available');
          return;
        }
        setCurrentQuestion(question);
        startTimeRef.current = Date.now();
        exerciseLogger.debug('Question loaded', { questionId: question.id });
      } catch (err) {
        const msg = getApiErrorMessage(err, '加载题目失败，请稍后重试');
        setError(msg);

        // 识别错误类型
        if (axios.isAxiosError(err)) {
          const status = err.response?.status;
          if (status === 403) {
            setErrorType('not_enrolled');
          } else if (status === 404) {
            setErrorType('no_questions');
          } else if (!err.response) {
            setErrorType('network_error');
          } else {
            setErrorType('unknown');
          }
        } else {
          setErrorType('unknown');
        }

        exerciseLogger.error('Failed to load question', { error: err });
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  const submitAnswer = useCallback(
    async (answerText: string) => {
      if (!currentQuestion) return;
      if (!answerText.trim()) {
        setError('请输入答案');
        return;
      }

      setIsSubmitting(true);
      setError(null);
      try {
        const timeSpent = Math.round(
          (Date.now() - startTimeRef.current) / 1000,
        );
        const result = await exerciseService.submitAnswer({
          exerciseId: currentQuestion.id,
          answerText,
          timeSpentSeconds: timeSpent,
        });
        setSubmitResult(result);
        exerciseLogger.info('Answer submitted', {
          questionId: currentQuestion.id,
          isCorrect: result.isCorrect,
        });
      } catch (err) {
        const msg = getApiErrorMessage(err, '提交答案失败，请稍后重试');
        setError(msg);
        exerciseLogger.error('Failed to submit answer', {
          questionId: currentQuestion.id,
          error: err,
        });
      } finally {
        setIsSubmitting(false);
      }
    },
    [currentQuestion],
  );

  return {
    currentQuestion,
    isLoading,
    isSubmitting,
    submitResult,
    error,
    errorType,
    loadNextQuestion,
    submitAnswer,
  };
}
