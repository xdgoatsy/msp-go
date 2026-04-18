/**
 * 课表相关类型定义
 */

/** 课程详情 */
export interface ClassDetail {
  name: string;
  code: string;
  number: string;
}

/** 时间安排 */
export type WeekFlag = number | boolean;

/** 时间安排 */
export interface TimeArrangement {
  source: string;
  index: number;
  start: number;
  stop: number;
  day: number;
  week_list: WeekFlag[];
  teacher: string;
  classroom: string;
}

/** 课表数据 */
export interface ClasstableData {
  semester_code: string;
  term_start_day: string;
  semester_length: number;
  class_detail: ClassDetail[];
  time_arrangement: TimeArrangement[];
  not_arranged: unknown[];
  class_changes: unknown[];
}

/** 课表单元格 */
export interface ClassCell {
  name: string;
  teacher: string;
  classroom: string;
  isMath: boolean;
  startPeriod: number;
  endPeriod: number;
}

/** 高数课时统计 */
export interface MathHoursStats {
  totalWeeks: number;
  remainingWeeks: number;
  totalHours: number;
  remainingHours: number;
  weeklyHours: number;
}
