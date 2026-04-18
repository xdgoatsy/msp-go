/**
 * 安全日志相关类型定义
 */

// =============================================================================
// 事件类型和严重程度
// =============================================================================

export type SecurityEventType =
  | 'login_failed'
  | 'login_anomaly'
  | 'request_error'
  | 'request_blocked'
  | 'service_error'
  | 'service_recovered'
  | 'daily_report'
  | 'config_changed';

export type SecuritySeverity = 'info' | 'warning' | 'error' | 'critical';

// 事件类型显示名称
export const EVENT_TYPE_DISPLAY: Record<SecurityEventType, string> = {
  login_failed: '登录失败',
  login_anomaly: '异常登录',
  request_error: '请求异常',
  request_blocked: '请求拦截',
  service_error: '服务异常',
  service_recovered: '服务恢复',
  daily_report: '每日报告',
  config_changed: '配置变更',
};

// 严重程度显示名称
export const SEVERITY_DISPLAY: Record<SecuritySeverity, string> = {
  info: '信息',
  warning: '警告',
  error: '错误',
  critical: '严重',
};

// 严重程度颜色
export const SEVERITY_COLORS: Record<SecuritySeverity, string> = {
  info: 'text-blue-600 bg-blue-50 border-blue-200',
  warning: 'text-orange-600 bg-orange-50 border-orange-200',
  error: 'text-red-600 bg-red-50 border-red-200',
  critical: 'text-red-800 bg-red-100 border-red-300',
};

// =============================================================================
// 日志数据结构
// =============================================================================

export interface SecurityLogItem {
  id: string;
  event_type: SecurityEventType;
  severity: SecuritySeverity;
  title: string;
  description: string;
  ip_address: string | null;
  user_id: string | null;
  username: string | null;
  extra_data: Record<string, unknown>;
  archived: boolean;
  created_at: string;
}

export interface SecurityLogGroup {
  date: string;
  date_display: string;
  logs: SecurityLogItem[];
  count: number;
}

// =============================================================================
// API 响应类型
// =============================================================================

export interface SecurityLogListResponse {
  groups: SecurityLogGroup[];
  total: number;
  has_more: boolean;
}

export interface SecurityLogStatsResponse {
  total_count: number;
  error_count: number;
  warning_count: number;
  info_count: number;
  last_error_at: string | null;
  last_daily_report_at: string | null;
}

export interface SecurityLogExportResponse {
  filename: string;
  content: string; // Base64 编码
  content_type: string;
  record_count: number;
}

export interface SecurityLogDeleteResponse {
  deleted_count: number;
}

export interface SecurityLogArchiveResponse {
  archived_count: number;
}

// =============================================================================
// 请求参数类型
// =============================================================================

export interface SecurityLogQueryParams {
  event_types?: SecurityEventType[];
  severities?: SecuritySeverity[];
  start_date?: string;
  end_date?: string;
  include_archived?: boolean;
  page?: number;
  page_size?: number;
}

export interface SecurityLogDeleteRequest {
  log_ids?: string[];
  before_date?: string;
  delete_all?: boolean;
}

export interface SecurityLogExportRequest {
  format?: 'json' | 'csv';
  event_types?: SecurityEventType[];
  severities?: SecuritySeverity[];
  start_date?: string;
  end_date?: string;
  include_archived?: boolean;
}

export interface SecurityLogArchiveRequest {
  before_date: string;
}
