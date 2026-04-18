/**
 * 学生画像类型定义
 */

export interface StudentPortrait {
  student_id: string;
  portrait_content: string | null;
  portrait_generated_at: string | null;
  portrait_version: number;
  total_exercises: number;
  correct_rate: number;
  total_study_time_minutes: number;
  has_content: boolean;
}

export interface GeneratePortraitResponse {
  portrait_content: string;
  portrait_generated_at: string;
  portrait_version: number;
}

export interface ClearPortraitResponse {
  cleared: boolean;
  message: string;
}
