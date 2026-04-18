/**
 * 安全日志列表组件
 */

import React from 'react';
import { RefreshCw, CheckCircle } from 'lucide-react';
import { useAppDispatch } from '@/store';
import { toggleSelectAll } from '@/modules/admin/store/securityLogSlice';
import { SecurityLogGroup } from './SecurityLogGroup';
import type { SecurityLogGroup as SecurityLogGroupType } from '@/modules/admin/types/securityLog';

interface SecurityLogListProps {
  groups: SecurityLogGroupType[];
  loading: 'idle' | 'loading' | 'succeeded' | 'failed';
  selectedIds: string[];
  expandedGroups: Set<string>;
  onToggleGroup: (date: string) => void;
}

export const SecurityLogList: React.FC<SecurityLogListProps> = ({
  groups,
  loading,
  selectedIds,
  expandedGroups,
  onToggleGroup,
}) => {
  const dispatch = useAppDispatch();

  if (loading === 'loading' && groups.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 text-surface-400 animate-spin" />
      </div>
    );
  }

  if (groups.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-surface-500">
        <CheckCircle className="w-16 h-16 mb-4 text-emerald-500" />
        <p className="text-lg font-medium">系统安全</p>
        <p className="text-sm">暂无安全日志记录</p>
      </div>
    );
  }

  const totalLogs = groups.reduce((sum, g) => sum + g.logs.length, 0);

  return (
    <div className="space-y-4">
      {/* 全选 */}
      <div className="flex items-center gap-2 pb-2 border-b border-surface-200 dark:border-surface-700">
        <input
          type="checkbox"
          checked={selectedIds.length > 0 && selectedIds.length === totalLogs}
          onChange={() => dispatch(toggleSelectAll())}
          className="w-4 h-4 rounded border-surface-300"
        />
        <span className="text-sm text-surface-600 dark:text-surface-400">
          全选
        </span>
      </div>

      {/* 按日期分组的日志 */}
      {groups.map((group) => (
        <SecurityLogGroup
          key={group.date}
          group={group}
          isExpanded={expandedGroups.has(group.date)}
          selectedIds={selectedIds}
          onToggle={onToggleGroup}
        />
      ))}
    </div>
  );
};
