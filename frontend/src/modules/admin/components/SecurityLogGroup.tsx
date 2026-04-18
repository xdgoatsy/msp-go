/**
 * 日期分组日志组件
 */

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { SecurityLogItem } from './SecurityLogItem';
import type { SecurityLogGroup as SecurityLogGroupType } from '@/modules/admin/types/securityLog';

interface SecurityLogGroupProps {
  group: SecurityLogGroupType;
  isExpanded: boolean;
  selectedIds: string[];
  onToggle: (date: string) => void;
}

export const SecurityLogGroup: React.FC<SecurityLogGroupProps> = ({
  group,
  isExpanded,
  selectedIds,
  onToggle,
}) => {
  return (
    <div className="border border-surface-200 dark:border-surface-700 rounded-lg overflow-hidden">
      {/* 日期组头部 */}
      <button
        onClick={() => onToggle(group.date)}
        className="w-full flex items-center justify-between px-4 py-3 bg-surface-50 dark:bg-surface-800/50 hover:bg-surface-100 dark:hover:bg-surface-700/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-surface-500" />
          ) : (
            <ChevronRight className="w-4 h-4 text-surface-500" />
          )}
          <span className="font-medium text-surface-900 dark:text-surface-100">
            {group.date_display}
          </span>
          <span className="text-sm text-surface-500">
            ({group.count} 条)
          </span>
        </div>
      </button>

      {/* 日志列表 */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: 'auto' }}
            exit={{ height: 0 }}
            className="overflow-hidden"
          >
            <div className="divide-y divide-surface-100 dark:divide-surface-700">
              {group.logs.map((log) => (
                <SecurityLogItem
                  key={log.id}
                  log={log}
                  isSelected={selectedIds.includes(log.id)}
                />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
