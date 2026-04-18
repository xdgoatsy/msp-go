/**
 * 通用类型定义
 */

// 分页参数
export interface PaginationParams {
  page: number;
  pageSize: number;
}

// 分页响应
export interface PaginationResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// API 响应基础结构
export interface ApiResponse<T = unknown> {
  success: boolean;
  data: T;
  message?: string;
  code?: string;
}

// API 错误响应
export interface ApiError {
  success: false;
  message: string;
  code: string;
  details?: unknown;
}

// 主题类型
export type Theme = 'light' | 'dark';

// 用户角色
export type UserRole = 'student' | 'teacher' | 'admin';

// 难度等级
export type DifficultyLevel = 'easy' | 'medium' | 'hard';

// 加载状态
export type LoadingState = 'idle' | 'loading' | 'success' | 'error';
