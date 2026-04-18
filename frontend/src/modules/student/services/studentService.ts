/**
 * 学生服务
 *
 * 提供学生学习进度、统计数据等 API
 */

import { apiClient } from '@/libs/http/apiClient';

// ========== 类型定义 ==========

/** 今日统计数据 */
export interface TodayStats {
  study_time_minutes: number;
  exercises_completed: number;
}

/** 最近学习内容 */
export interface RecentContent {
  last_accessed: string;
}

/** 学习进度概览 */
export interface ProgressOverview {
  total_exercises: number;
  correct_count: number;
  correct_rate: number;
  study_time_minutes: number;
  streak_days: number;
  mastered_concepts: number;
  today_stats: TodayStats;
  recent_content: RecentContent | null;
}

// ========== API 方法 ==========

/**
 * 获取学习进度概览
 *
 * 包含总做题数、正确率、学习时长、连续打卡、掌握概念数、今日统计
 */
export const getProgressOverview = async (): Promise<ProgressOverview> => {
  const response = await apiClient.get<ProgressOverview>('/progress/overview');
  return response.data;
};

/**
 * 学生服务对象（可选的命名空间方式）
 */
export const studentService = {
  getProgressOverview,
};

export default studentService;
