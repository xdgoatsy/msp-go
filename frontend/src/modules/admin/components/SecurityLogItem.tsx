/**
 * 单条安全日志组件
 */

import React from 'react';
import { AlertCircle, AlertTriangle, Info } from 'lucide-react';
import { useAppDispatch } from '@/store';
import { toggleSelectLog } from '@/modules/admin/store/securityLogSlice';
import {
  SEVERITY_DISPLAY,
  SEVERITY_COLORS,
  EVENT_TYPE_DISPLAY,
} from '@/modules/admin/types/securityLog';
import type { SecurityLogItem as SecurityLogItemType, SecuritySeverity } from '@/modules/admin/types/securityLog';

// 获取严重程度图标
function getSeverityIcon(severity: SecuritySeverity) {
  switch (severity) {
    case 'critical':
      return <AlertCircle className="w-4 h-4" />;
    case 'error':
      return <AlertTriangle className="w-4 h-4" />;
    case 'warning':
      return <AlertTriangle className="w-4 h-4" />;
    case 'info':
    default:
      return <Info className="w-4 h-4" />;
  }
}

// 格式化时间
function formatTime(dateStr: string) {
  const date = new Date(dateStr);
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

interface SecurityLogItemProps {
  log: SecurityLogItemType;
  isSelected: boolean;
}

export const SecurityLogItem: React.FC<SecurityLogItemProps> = ({ log, isSelected }) => {
  const dispatch = useAppDispatch();

  return (
    <div
      className={`flex items-start gap-3 px-4 py-3 hover:bg-surface-50 dark:hover:bg-surface-800/30 transition-colors ${
        isSelected ? 'bg-primary-50 dark:bg-primary-900/10' : ''
      }`}
    >
      <input
        type="checkbox"
        checked={isSelected}
        onChange={() => dispatch(toggleSelectLog(log.id))}
        className="mt-1 w-4 h-4 rounded border-surface-300"
      />

      <div className={`p-1.5 rounded-lg border ${SEVERITY_COLORS[log.severity]}`}>
        {getSeverityIcon(log.severity)}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium text-surface-900 dark:text-surface-100">
            {log.title}
          </span>
          <span className={`px-2 py-0.5 text-xs rounded-full ${SEVERITY_COLORS[log.severity]}`}>
            {SEVERITY_DISPLAY[log.severity]}
          </span>
          <span className="px-2 py-0.5 text-xs rounded-full bg-surface-100 dark:bg-surface-700 text-surface-600 dark:text-surface-400">
            {EVENT_TYPE_DISPLAY[log.event_type]}
          </span>
        </div>
        <p className="text-sm text-surface-600 dark:text-surface-400 mt-1">
          {log.description}
        </p>
        <div className="flex items-center gap-4 mt-2 text-xs text-surface-500">
          <span>{formatTime(log.created_at)}</span>
          {log.ip_address && <span>IP: {log.ip_address}</span>}
          {log.username && <span>用户: {log.username}</span>}
        </div>
      </div>
    </div>
  );
};
