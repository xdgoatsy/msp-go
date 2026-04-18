/**
 * 安全日志筛选面板组件
 */

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/Button';
import {
  EVENT_TYPE_DISPLAY,
  SEVERITY_DISPLAY,
} from '@/modules/admin/types/securityLog';
import type {
  SecurityEventType,
  SecuritySeverity,
  SecurityLogQueryParams,
} from '@/modules/admin/types/securityLog';

interface SecurityLogFiltersProps {
  show: boolean;
  queryParams: SecurityLogQueryParams;
  onEventTypeFilter: (eventType: SecurityEventType) => void;
  onSeverityFilter: (severity: SecuritySeverity) => void;
  onResetFilters: () => void;
}

export const SecurityLogFilters: React.FC<SecurityLogFiltersProps> = ({
  show,
  queryParams,
  onEventTypeFilter,
  onSeverityFilter,
  onResetFilters,
}) => {

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          className="overflow-hidden border-b border-surface-200 dark:border-surface-700"
        >
          <div className="px-6 py-4 bg-surface-50 dark:bg-surface-800/30 space-y-4">
            {/* 事件类型筛选 */}
            <div>
              <label className="text-sm font-medium text-surface-700 dark:text-surface-300 mb-2 block">
                事件类型
              </label>
              <div className="flex flex-wrap gap-2">
                {(Object.keys(EVENT_TYPE_DISPLAY) as SecurityEventType[]).map((type) => (
                  <button
                    key={type}
                    onClick={() => onEventTypeFilter(type)}
                    className={`px-3 py-1.5 text-sm rounded-full border transition-colors ${
                      queryParams.event_types?.includes(type)
                        ? 'bg-primary-100 border-primary-300 text-primary-700 dark:bg-primary-900/30 dark:border-primary-700 dark:text-primary-300'
                        : 'bg-white border-surface-200 text-surface-600 hover:bg-surface-50 dark:bg-surface-700 dark:border-surface-600 dark:text-surface-300'
                    }`}
                  >
                    {EVENT_TYPE_DISPLAY[type]}
                  </button>
                ))}
              </div>
            </div>

            {/* 严重程度筛选 */}
            <div>
              <label className="text-sm font-medium text-surface-700 dark:text-surface-300 mb-2 block">
                严重程度
              </label>
              <div className="flex flex-wrap gap-2">
                {(Object.keys(SEVERITY_DISPLAY) as SecuritySeverity[]).map((severity) => (
                  <button
                    key={severity}
                    onClick={() => onSeverityFilter(severity)}
                    className={`px-3 py-1.5 text-sm rounded-full border transition-colors ${
                      queryParams.severities?.includes(severity)
                        ? 'bg-primary-100 border-primary-300 text-primary-700 dark:bg-primary-900/30 dark:border-primary-700 dark:text-primary-300'
                        : 'bg-white border-surface-200 text-surface-600 hover:bg-surface-50 dark:bg-surface-700 dark:border-surface-600 dark:text-surface-300'
                    }`}
                  >
                    {SEVERITY_DISPLAY[severity]}
                  </button>
                ))}
              </div>
            </div>

            {/* 重置按钮 */}
            <div className="flex justify-end">
              <Button variant="ghost" size="sm" onClick={onResetFilters}>
                重置筛选
              </Button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
