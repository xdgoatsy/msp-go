/**
 * 班级管理相关类型定义
 */

export interface ClassInfo {
  id: string;
  name: string;
  code: string;
  teacher_id: string;
  description?: string | null;
  created_at: string;
  student_count?: number;
  teacher_name?: string | null;
  teacher_email?: string | null;
  teacher_avatar_url?: string | null;
  joined_at?: string | null;
}

export interface ClassStudent {
  id: string;
  username: string;
  email: string;
  display_name?: string | null;
}

export interface ClassListResponse {
  items: ClassInfo[];
}

export interface ClassDetailResponse {
  class_info: ClassInfo;
  students: ClassStudent[];
}

export interface ClassCreateRequest {
  name: string;
  description?: string;
}

export interface ClassCreateResponse {
  success: boolean;
  message: string;
  class_info: ClassInfo;
}

export interface ClassLookupResponse {
  found: boolean;
  class_info: ClassInfo | null;
  teacher_name?: string | null;
}

export interface JoinClassRequest {
  code: string;
}

export interface JoinClassResponse {
  success: boolean;
  message: string;
  class_info: ClassInfo;
}

export interface LeaveClassResponse {
  success: boolean;
  message: string;
}

export interface StudentClassResponse {
  class_info: ClassInfo | null;
}

export interface RemoveStudentResponse {
  success: boolean;
  message: string;
}

export interface DisbandClassResponse {
  success: boolean;
  message: string;
}
