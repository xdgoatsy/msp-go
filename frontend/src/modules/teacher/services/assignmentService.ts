/**
 * 作业管理 API 服务
 *
 * 对接后端 /teacher/assignments API
 */

import { apiClient } from '@/libs/http/apiClient';
import { logger } from '@/libs/utils/logger';

const assignmentLogger = logger.createContextLogger('Assignment');
const BASE_PATH = '/teacher/assignments';

// ========== 类型定义 ==========

export interface Assignment {
  id: string;
  title: string;
  description: string;
  status: 'active' | 'ended' | 'draft';
  dueDate: string | null;
  createdAt: string;
  totalStudents: number;
  submitted: number;
  graded: number;
  questions: number;
  averageScore: number | null;
}

export interface AssignmentListResponse {
  items: Assignment[];
  total: number;
  page: number;
  pageSize: number;
}

export interface AssignmentStats {
  total: number;
  active: number;
  pending: number;
}

// ========== 后端原始响应 ==========

interface AssignmentRaw {
  id: string;
  title: string;
  description: string;
  status: string;
  due_date: string | null;
  created_at: string;
  total_students: number;
  submitted: number;
  graded: number;
  questions: number;
  average_score: number | null;
}

interface AssignmentListResponseRaw {
  items: AssignmentRaw[];
  total: number;
  page: number;
  page_size: number;
}

// ========== 映射函数 ==========

function mapAssignment(raw: AssignmentRaw): Assignment {
  return {
    id: raw.id,
    title: raw.title,
    description: raw.description,
    status: raw.status as Assignment['status'],
    dueDate: raw.due_date,
    createdAt: raw.created_at,
    totalStudents: raw.total_students,
    submitted: raw.submitted,
    graded: raw.graded,
    questions: raw.questions,
    averageScore: raw.average_score,
  };
}

// ========== API 方法 ==========

export const assignmentService = {
  /**
   * 获取作业列表
   */
  async list(params: {
    page?: number;
    pageSize?: number;
    status?: string;
  } = {}): Promise<AssignmentListResponse> {
    try {
      const response = await apiClient.get<AssignmentListResponseRaw>(BASE_PATH, {
        params: {
          page: params.page || 1,
          page_size: params.pageSize || 20,
          status: params.status,
        },
      });
      const raw = response.data;
      return {
        items: raw.items.map(mapAssignment),
        total: raw.total,
        page: raw.page,
        pageSize: raw.page_size,
      };
    } catch (error) {
      assignmentLogger.error('获取作业列表失败', error);
      throw error;
    }
  },

  /**
   * 获取作业统计
   */
  async getStats(): Promise<AssignmentStats> {
    try {
      const response = await apiClient.get<AssignmentStats>(`${BASE_PATH}/stats`);
      return response.data;
    } catch (error) {
      assignmentLogger.error('获取作业统计失败', error);
      throw error;
    }
  },
};
