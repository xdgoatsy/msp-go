import { useState, useCallback, useRef } from 'react';
import axios from 'axios';
import {
  exerciseService,
  type Question,
  type SubmitResult,
} from '@/modules/exercise/services/exerciseService';
import { uploadService } from '@/modules/upload/services/uploadService';
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
 * 管理题目加载、答案提交（文本+图片）、反馈展示
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
    async (answerText?: string, answerImageUrl?: string) => {
      if (!currentQuestion) return;
      if (!answerText && !answerImageUrl) {
        setError('请输入答案或上传图片');
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
          answerImageUrl,
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

  const uploadAnswerImage = useCallback(async (file: File): Promise<string | null> => {
    const validation = uploadService.validateImageFile(file);
    if (!validation.valid) {
      setError(validation.error || '图片验证失败');
      return null;
    }

    try {
      const result = await uploadService.uploadImage(file);
      return result.url;
    } catch (err) {
      setError('图片上传失败，请重试');
      exerciseLogger.error('Image upload failed', { error: err });
      return null;
    }
  }, []);

  return {
    currentQuestion,
    isLoading,
    isSubmitting,
    submitResult,
    error,
    errorType,
    loadNextQuestion,
    submitAnswer,
    uploadAnswerImage,
  };
}
